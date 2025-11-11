import sys
import os
import requests
import json
import logging
import datetime
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

def get_reflexive_feedback(sheet_url, worksheet_name):
    google_creds_json = os.environ.get("GOOGLE_CLOUD_CREDS_JSON")
    if not google_creds_json:
        logging.error("Missing GOOGLE_CLOUD_CREDS_JSON environment variable.")
        raise RuntimeError("Missing GOOGLE_CLOUD_CREDS_JSON environment variable")
    try:
        creds_dict = json.loads(google_creds_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_url(sheet_url)
        logging.info(f"Connected to Google Sheet: {sheet_url}")
        worksheet = sh.worksheet(worksheet_name)
        logging.info(f"Accessed worksheet: {worksheet_name}")
        feedback = worksheet.get_all_records()
        logging.info(f"Retrieved {len(feedback)} feedback records from Google Sheet.")
        return feedback
    except gspread.exceptions.APIError as e:
        logging.error(f"Google Sheets API error: {e}")
        raise
    except gspread.exceptions.WorksheetNotFound as e:
        logging.error(f"Worksheet not found: {worksheet_name} in {sheet_url}: {e}")
        raise
    except Exception as e:
        logging.error(f"General error accessing Google Sheets: {e}")
        raise

def send_openrouter_request(features_path, session_folder, feedback_json):
    # Ensure session folder exists
    os.makedirs(session_folder, exist_ok=True)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    site_url = "test1"
    site_name = "test1"
    url = "https://openrouter.ai/api/v1/chat/completions"

    # REQUIRED fields (no issue_id, includes biases)
    required_fields = [
        "issue_key",
        "summary",
        "description",
        "value_agreement",
        "dissent",
        "dependencies",
        "biases"
    ]

    with open(features_path, 'r', encoding='utf-8') as file:
        all_features = json.load(file)
    if isinstance(all_features, dict):
        all_features = [all_features]
    filtered_features = [
        {k: feature.get(k, "") for k in required_fields}
        for feature in all_features
    ]

    json_string = json.dumps(filtered_features, indent=2)

    prompt_content = (
        "Analyze the following list of feature metadata (in JSON). For each feature, generate a decision card "
        "including all input fields, a priority score (1-10), and a rationale. Use only the inputs provided in "
        "the JSON file to determine priority, do not invent anything on your own. "
        "Additionally, study the following reflexive feedback from previous issue releases, "
        "the deviations in prioritization, and post-release feedback, and incorporate this analysis into your final priority evaluation. "
        "Try to avoid assigning the same priority to more than one feature. Return the output in JSON array format, "
        "with each 'decision_card' json object containing jira id, summary, value agreement, dissent, dependencies, biases, "
        "a priority_score, and a rationale. "
        "Do not return anything else.\n"
        "Reflexive_Feedback_JSON:\n"
        f"{feedback_json}\n"
        "Features_JSON:\n"
        f"{json_string}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": site_url,
        "X-Title": site_name,
        "Content-Type": "application/json"
    }

    payload = {
        "model": "nvidia/nemotron-nano-12b-v2-vl:free",
        "messages": [
            {
                "role": "user",
                "content": prompt_content
            }
        ]
    }

    logging.info("Request URL: %s", url)
    logging.info("Request Headers: %s", headers)
    logging.info("Request Body: %s", json.dumps(payload, indent=2))

    api_exchange_filename = os.path.join(session_folder, 'api_exchange.json')
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    logging.info("Response Status Code: %s", response.status_code)
    logging.info("Response Headers: %s", dict(response.headers))

    api_exchange_data = {
        "request": {
            "url": url,
            "headers": headers,
            "payload": payload,
        },
        "response": {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
        }
    }

    with open(api_exchange_filename, 'w', encoding='utf-8') as fx:
        json.dump(api_exchange_data, fx, indent=2)

    # handle non‑200 responses
    if response.status_code != 200:
        logging.error("API request failed with status code %s", response.status_code)
        logging.error("Response Body: %s", response.text)
        print(f"API request failed with status code {response.status_code}. Check log for details.")
        return ""

    try:
        resp_data = response.json()
        logging.info("Response Body: %s", json.dumps(resp_data, indent=2))
        assistant_content = resp_data['choices'][0]['message']['content']

        # Extract JSON array from assistant_content
        json_start = assistant_content.find('[')
        json_end = assistant_content.rfind(']') + 1
        cards_json_str = assistant_content[json_start:json_end]
        decision_cards = json.loads(cards_json_str)

        # Merge with original workshop feature set (consolidated reasoning)
        with open(features_path, 'r', encoding='utf-8') as file:
            all_features = json.load(file)
        if isinstance(all_features, dict):
            all_features = [all_features]
        features_lookup = {f["issue_key"]: f for f in all_features if "issue_key" in f}

        merged_cards = []
        for card in decision_cards:
            issue_key = card.get("jira_key") or card.get("issue_key")
            base_feature = features_lookup.get(issue_key, {})
            merged = base_feature.copy()  # Start with all original fields (including biases)
            merged.update(card)           # Add/overwrite with LLM fields (including biases if present in LLM output)
            merged_cards.append(merged)

        # Save the merged output
        result_json_filename = os.path.join(session_folder, "llm_eval_output/star_decision_cards_full.json")
        os.makedirs(os.path.dirname(result_json_filename), exist_ok=True)
        with open(result_json_filename, "w", encoding='utf-8') as f:
            json.dump(merged_cards, f, indent=2)
        print(result_json_filename)

        logging.info("debug 1 ")
        logging.info(f"All keys in first decision_card: {list(merged_cards[0].keys())}")
        # Update Jira with the results, if needed
        # (You can safely comment or keep existing Jira code below if you want, it's bias-agnostic)
        for card in merged_cards:
            issue_id = card.get("jira_id") or card.get("jira_key") or card.get("issue_key")
            logging.info("debug issue_id : %s", issue_id)
            priority = card.get("priority_score")
            logging.info("debug priority : %s", priority)
            rationale = card.get("rationale")
            logging.info("debug rationale : %s", rationale)
            if issue_id and priority and rationale:
                update_jira_issue(issue_id, priority, rationale)
        logging.info("debug:end of openrouter/")
        return result_json_filename

    except Exception as e:
        logging.error("Error processing response: %s", str(e))
        print("Failed to process API response. Check log for details.")
        return ""

def move_data_rows(sheet_url, worksheet_name_source, worksheet_name_target):
    try:
        google_creds_json = os.environ.get("GOOGLE_CLOUD_CREDS_JSON")
        if not google_creds_json:
            logging.error("Missing GOOGLE_CLOUD_CREDS_JSON environment variable.")
            return
        creds_dict = json.loads(google_creds_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_url(sheet_url)
        ws_source = sh.worksheet(worksheet_name_source)
        ws_target = sh.worksheet(worksheet_name_target)

        all_rows = ws_source.get_all_values()
        num_rows = len(all_rows)
        if num_rows > 1:
            header = all_rows[0]
            data_rows = all_rows[1:]
            ws_target.append_rows(data_rows)
            for i in range(num_rows, 1, -1):
                ws_source.delete_rows(i)
            logging.info(f"Moved {num_rows - 1} data rows from {worksheet_name_source} to {worksheet_name_target}, retained headers only in source.")
        else:
            logging.info(f"No data rows to move; {worksheet_name_source} only contains header.")
    except Exception as e:
        logging.error(f"Error moving data rows from Google Sheet: {e}")
        import traceback
        logging.error(traceback.format_exc())

def update_jira_issue(issue_id, priority, rationale):
    jira_url = os.environ["JIRA_URL"]
    jira_user = os.environ["JIRA_USER"]
    jira_token = os.environ["JIRA_TOKEN"]
    priority_field = os.environ.get("JIRA_PRIORITY_FIELD", "priority")
    rationale_field = os.environ["JIRA_RATIONALE_FIELD"]

    api_url = f"{jira_url}/rest/api/3/issue/{issue_id}"
    logging.info(f"Jira url to update : {api_url})")
    auth = (jira_user, jira_token)
    rationale_adf = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": rationale}
                ]
            }
        ]
    }
    payload = {
        "fields": {
            priority_field: priority,
            rationale_field: rationale_adf
        }
    }
    logging.info("Request Body: %s", json.dumps(payload, indent=2))
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    response = requests.put(api_url, auth=auth, headers=headers, data=json.dumps(payload))
    if response.status_code == 204:
        logging.info(f"Jira issue {issue_id} updated: priority={priority}, rationale={rationale}")
    else:
        logging.error(f"Failed to update Jira {issue_id}: {response.status_code} {response.text}")

if __name__ == "__main__":
    sheet_url = "https://docs.google.com/spreadsheets/d/1XMgrnVNwMaQ_o2QSLVyAWC59TKhPvqr2_z9Z75h_1x4"
    worksheet_name = "Sheet1"
    features_path = sys.argv[1] if len(sys.argv) > 1 else "Resources/LLMadapter/features.json"
    session_folder = sys.argv[2] if len(sys.argv) > 2 else "Output/Session9999_default"

    log_filename = os.path.join(session_folder, "debug-prints.log")
    os.makedirs(session_folder, exist_ok=True)
    logging.basicConfig(
        filename=log_filename,
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s'
    )
    logging.info("In Openrouter.py")

    feedback_data = get_reflexive_feedback(sheet_url, worksheet_name)
    feedback_json = json.dumps(feedback_data, indent=2)

    send_openrouter_request(features_path, session_folder, feedback_json)
    move_data_rows(sheet_url, worksheet_name_source="Sheet1", worksheet_name_target="Sheet2")

import sys
import os
import requests
import json
import logging
import datetime
import gspread
from google.oauth2.service_account import Credentials

def get_reflexive_feedback(sheet_url, worksheet_name, creds_path):
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_url(sheet_url)
    worksheet = sh.worksheet(worksheet_name)
    feedback = worksheet.get_all_records()
    return feedback  # List of dictionaries

def send_openrouter_request(features_path, session_folder, feedback_json):
    # Ensure session folder exists
    os.makedirs(session_folder, exist_ok=True)
    api_key = "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"
    site_url = "test1"
    site_name = "test1"
    url = "https://openrouter.ai/api/v1/chat/completions"

    with open(features_path, 'r', encoding='utf-8') as file:
        json_content = json.load(file)
    json_string = json.dumps(json_content, indent=2)

    prompt_content = (
        "Analyze the following list of feature metadata (in JSON). For each feature, generate a decision card "
        "including all input fields, a priority score (1-10), and a rationale. Use only the inputs provided in "
        "the JSON file to determine priority, do not invent anything on your own. "
        "Additionally, study the following reflexive feedback from previous issue releases, "
        "the deviations in prioritization, and post-release feedback, and incorporate this analysis into your final priority evaluation. "
        "Try to avoid assigning the same priority to more than one feature. Return the output in JSON array format, "
        "with each 'decision_card' json object containing all inputs, a priority_score, and a rationale. "
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

    # Save full API exchange (request + response) for session analysis
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

        # Write main result file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        result_json_filename = os.path.join(session_folder, "llm_eval_output/star_decision_cards.json")
        os.makedirs(os.path.dirname(result_json_filename), exist_ok=True)
        logging.info("result_json_filename %s",result_json_filename)
        with open(result_json_filename, "w", encoding='utf-8') as f:
            json.dump(decision_cards, f, indent=2)

        print(result_json_filename)
        logging.info("debug:end of openrouter/")
        return result_json_filename

    except Exception as e:
        logging.error("Error processing response: %s", str(e))
        print("Failed to process API response. Check log for details.")
        return ""

if __name__ == "__main__":
    sheet_url = "https://docs.google.com/spreadsheets/d/1XMgrnVNwMaQ_o2QSLVyAWC59TKhPvqr2_z9Z75h_1x4"
    worksheet_name = "Sheet1"
    creds_path = "test-secrets/jiraintegration-credential.json"
    features_path = sys.argv[1] if len(sys.argv) > 1 else "Resources/LLMadapter/features.json"
    session_folder = sys.argv[2] if len(sys.argv) > 2 else "Output/Session9999_default"

    # Prepare logging to session folder
    log_filename = os.path.join(session_folder, "debug-prints.log")
    logging.basicConfig(
        filename=log_filename,
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s'
    )
    logging.info("In Openrouter.py")

    # 1. Read reflexive feedback data from Google Sheets using secret credentials from env
    feedback_data = get_reflexive_feedback(sheet_url, worksheet_name, creds_path)
    feedback_json = json.dumps(feedback_data, indent=2)

    # 2. Send request with both feature list and feedback
    send_openrouter_request(features_path, session_folder, feedback_json)

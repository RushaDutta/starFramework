import sys
import os
import requests
import json
import logging
import datetime

logging.basicConfig(filename='feature_prioritization.log',
                    level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

def send_openrouter_request(features_path):
    # Use features_path that's passed in
    api_key = api_key
    site_url = "test1"
    site_name = "test1"
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # Read your JSON file using features_path
    with open(features_path, 'r') as file:
        json_content = json.load(file)

    json_string = json.dumps(json_content, indent=2)
    
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
                "content": (
                    "Analyze the following list of feature metadata (in JSON). For each feature, generate a decision card including all input fields,"
                    "a priority score (1-10), and a rationale. Use only the inputs provided in the json file to determine priority, do not invent anything on your own."
                    "Try to avoid assigning same priority to more than one feature. Return the output in JSON array format, with each 'decision_card' json object containing all inputs, "
                    "a priority_score, and a rationale. Do not return anything else.\nJSON:\n"
                    f"{json_string}"
                )
            }
        ]
    }

    logging.info("Request URL: %s", url)
    logging.info("Request Headers: %s", headers)
    logging.info("Request Body: %s", json.dumps(payload, indent=2))

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    logging.info("Response Status Code: %s", response.status_code)
    logging.info("Response Headers: %s", dict(response.headers))

    try:
        resp_data = response.json()
        logging.info("Response Body: %s", json.dumps(resp_data, indent=2))
        assistant_content = resp_data['choices'][0]['message']['content']
        
        # Extract JSON array from assistant_content
        json_start = assistant_content.find('[')
        json_end = assistant_content.rfind(']') + 1
        cards_json_str = assistant_content[json_start:json_end]
        decision_cards = json.loads(cards_json_str)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        result_json_filename = f"Output/ranking_result_{timestamp}.json"

        with open(result_json_filename, "w", encoding='utf-8') as f:
            json.dump(decision_cards, f, indent=2)

        print(f"Ranking result saved to: {result_json_filename}")

        # Return result file path for orchestration if called as subprocess
        return result_json_filename

    except Exception as e:
        logging.error("Error processing response: %s", str(e))
        print("Failed to process API response. Check log for details.")
        return ""

if __name__ == "__main__":
    features_path = sys.argv[1] if len(sys.argv) > 1 else "Resources/LLMadapter/features.json"
    send_openrouter_request(features_path)

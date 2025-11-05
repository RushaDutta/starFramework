import requests
import json
import logging

# --- Logging Setup ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

def send_openrouter_request():
    api_key = api_key
    site_url = "test"
    site_name = "test"
    url = "https://openrouter.ai/api/v1/chat/completions"

    # Read your JSON file
    with open('yourfile.json', 'r') as file:
        json_content = json.load(file)

    # Convert the JSON to a string for the prompt
    json_string = json.dumps(json_content, indent=2)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": site_url,
        "X-Title": site_name,
        "Content-Type": "application/json"
    }

    payload = {
        "model": "openai/gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": f"Analyze the following JSON:\n{json_string}"
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
        logging.info("Response Body: %s", json.dumps(response.json(), indent=2))
    except Exception:
        logging.info("Response Body (raw): %s", response.text)

    return response

if __name__ == "__main__":
    send_openrouter_request()

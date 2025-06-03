import logging
from flask import current_app, jsonify
import json
import requests
import os
from dotenv import load_dotenv

# from app.services.openai_service import generate_response
import re

# Import AI services - Conditionally import or comment out unused ones
# For Gemini-only demo:
from app.services import gemini_service
# try:
#     from app.services import openai_service
#     OPENAI_SERVICE_AVAILABLE = True
# except ImportError:
#     OPENAI_SERVICE_AVAILABLE = False
#     openai_service = None # Define to prevent AttributeError if referenced
#     logging.info("OpenAI service module not available or not used in this demo.")

# try:
#     from app.services import deepseek_service
#     DEEPSEEK_SERVICE_AVAILABLE = True
# except ImportError:
#     DEEPSEEK_SERVICE_AVAILABLE = False
#     deepseek_service = None # Define
#     logging.info("DeepSeek service module not available or not used in this demo.")

load_dotenv()


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def generate_response(message_body: str, wa_id: str, name: str) -> str:
    ai_provider = os.getenv("AI_PROVIDER", "gemini").lower() # Default to gemini for demo
    response_text = f"Sorry, I couldn't process your request using {ai_provider}."

    logging.info(f"Using AI provider: {ai_provider} for user {name} ({wa_id})")

    if ai_provider == "gemini":
        response_text = gemini_service.generate_ai_response(message_body, wa_id, name)
    # elif ai_provider == "openai" and OPENAI_SERVICE_AVAILABLE:
    #     response_text = openai_service.generate_response(message_body, wa_id, name)
    # elif ai_provider == "deepseek" and DEEPSEEK_SERVICE_AVAILABLE:
    #     response_text = deepseek_service.generate_ai_response(message_body, wa_id, name)
    elif ai_provider == "openai" or ai_provider == "deepseek":
        logging.warning(f"AI Provider '{ai_provider}' is configured but its service module might be commented out or unavailable for this demo.")
        response_text = f"AI Provider '{ai_provider}' is not available in this demo configuration."
    else:
        logging.warning(f"Invalid AI_PROVIDER: {ai_provider}. Defaulting to Gemini for this demo or error.")
        # Fallback to Gemini if provider is misconfigured for demo
        response_text = gemini_service.generate_ai_response(message_body, wa_id, name) 
        # response_text = f"AI Provider '{'''{ai_provider}'''}' is not configured. Echo: {message_body}"

    return response_text


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = message["text"]["body"]

    # TODO: implement custom function here
    response = generate_response(message_body, wa_id, name)

    # OpenAI Integration
    # response = generate_response(message_body, wa_id, name)
    response = process_text_for_whatsapp(response)

    #data = get_text_message_input(current_app.config["RECIPIENT_WAID"], response)
    data = get_text_message_input(wa_id, response)
    send_message(data)


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )

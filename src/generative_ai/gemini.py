"""
Implementation with API calls to Gemini for summarizing CCs.

https://ai.google.dev/gemini-api/docs/models
"""
import json
from typing import Optional

import requests


# from src.generative_ai.cc_summary import get_out_file


def generate_gemini_summary_payload(prompt_text: str) -> str:
    """Creates the JSON payload for the Gemini API call."""
    if not prompt_text:
        return None
    
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    return json.dumps(payload)

def call_gemini_api_for_summary(
    video_id: str,
    prompt_text: str, # This is now a required argument
    model_name: str = "gemini-1.5-flash",
    api_key_override: Optional[str] = None,
    output_file: Optional[str] = None
) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key_override
    }
    
    # Generate the JSON payload string
    json_payload = generate_gemini_summary_payload(prompt_text)
    
    try:
        response = requests.post(url, headers=headers, data=json_payload)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        _json = response.json()
        out_file = output_file # or get_out_file(video_id, model=_json["modelVersion"], response_id=_json["responseId"])
        _json["out_file"] = out_file
        json.dump(_json, open(out_file, "w"), indent=2)
        return _json
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
        print(f"Response content: {response.text}")
        return {"error": str(err), "response_content": response.text}
    except requests.exceptions.ConnectionError as err:
        print(f"Connection error occurred: {err}")
        return {"error": str(err)}
    except requests.exceptions.Timeout as err:
        print(f"Timeout error occurred: {err}")
        return {"error": str(err)}
    except requests.exceptions.RequestException as err:
        print(f"An unexpected error occurred: {err}")
        return {"error": str(err)}

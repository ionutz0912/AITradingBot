import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Literal
import requests
from pydantic import BaseModel, Field, ValidationError


URL = "https://api.deepseek.com/beta/chat/completions"
MODEL = "deepseek-chat"

# URL = "https://openrouter.ai/api/v1"
# MODEL = "deepseek/deepseek-chat"

TEMPERATURE = 0.2
#   Lower = less randomness, more consistent formatting (good for structured outputs).
#   Use 0.1–0.3 for trading pipelines. Higher values increase creativity but risk off-schema text.

MAX_TOKENS = 800
#   Upper bound of tokens the model may generate in the *response*.
#   Needs to be high enough so long "reasons" plus JSON do not get cut off mid-output.



class AIResponseError(Exception):
    """Raised when AI response doesn't match expected format."""
    pass


class AIOutlook(BaseModel):
    """Validated structure for AI market outlook."""
    interpretation: Literal["Bullish", "Bearish", "Neutral"]
    reasons: str = Field(min_length=1, description="Non-empty rationale for the outlook")


def send_request(prompt: str, crypto_symbol: str, api_key: str) -> AIOutlook:
    """
    Send request to LLM API and return validated outlook.

    Args:
        prompt: The prompt to send to the AI
        crypto_symbol: Cryptocurrency symbol (e.g., "Bitcoin")
        api_key: API key for the LLM provider

    Returns:
        AIOutlook object with interpretation and reasons

    Raises:
        AIResponseError: If AI response is invalid
        requests.HTTPError: If API request fails
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": MODEL,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
        "tools": _build_tools_schema(crypto_symbol),
        "tool_choice": "auto"
    }

    r = requests.post(URL, headers=headers, data=json.dumps(payload), timeout=30)

    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        logging.error(f"AI API HTTP error {r.status_code}: {r.text}")
        raise

    data = r.json()

    try:
        call = data["choices"][0]["message"]["tool_calls"][0]
    except (KeyError, IndexError) as e:
        logging.error(f"AI API response missing tool_calls: {e}")
        raise AIResponseError(f"Missing tool_calls in API response: {e}")

    expected_function = f"{crypto_symbol.lower()}_outlook"
    if call["function"]["name"] != expected_function:
        logging.error(f"AI called unexpected function: {call['function']['name']}, expected {expected_function}")
        raise AIResponseError(
            f"Unexpected function called: {call['function']['name']}, expected {expected_function}"
        )

    try:
        args = json.loads(call["function"]["arguments"])
    except json.JSONDecodeError as e:
        logging.error(f"AI function arguments are not valid JSON: {e}")
        raise AIResponseError(f"Failed to parse function arguments as JSON: {e}")

    try:
        outlook = AIOutlook(**args)
        return outlook
    except ValidationError as e:
        logging.error(f"AI response failed Pydantic validation: {e}")
        raise AIResponseError(f"Invalid API response structure: {e}")


def _build_tools_schema(crypto_symbol: str) -> list[dict[str, Any]]:
    """
    Build the JSON schema for the LLM tool/function call.
    - enum hard-limits interpretation to 3 choices.
    - reasons is a free string (we cap length via instructions + max_tokens).
    """
    return [{
        "type": "function",
        "strict": True,  # ask server to enforce the schema (provider-dependent)
        "function": {
            "name": f"{crypto_symbol.lower()}_outlook",
            "description": f"Return a structured {crypto_symbol} outlook for the next 24 hours.",
            "parameters": {
                "type": "object",
                "properties": {
                    "interpretation": {
                        "type": "string",
                        "enum": ["Bullish", "Bearish", "Neutral"]
                    },
                    "reasons": {
                        "type": "string",
                        "description": "Concise rationale citing the strongest factors."
                    }
                },
                "required": ["interpretation", "reasons"],
                "additionalProperties": False
            }
        }
    }]


def save_response(outlook: AIOutlook, run_name: str) -> None:
    """
    Save AI response to JSON file organized by run name.

    Args:
        outlook: The AI outlook response to save
        run_name: Name of the run (used as filename)
    """
    try:
        responses_dir = Path("ai_responses")
        responses_dir.mkdir(exist_ok=True)

        file_path = responses_dir / f"{run_name}.json"

        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        data[timestamp] = outlook.model_dump()

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        logging.error(f"Failed to save AI response: {e}")

"""
Multi-provider AI module for trading bot.
Supports: Anthropic (Claude), xAI (Grok), DeepSeek
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Literal
import requests
from pydantic import BaseModel, Field, ValidationError


# ===================== CONFIGURATION =====================

TEMPERATURE = 0.2
#   Lower = less randomness, more consistent formatting (good for structured outputs).
#   Use 0.1–0.3 for trading pipelines. Higher values increase creativity but risk off-schema text.

MAX_TOKENS = 800
#   Upper bound of tokens the model may generate in the *response*.
#   Needs to be high enough so long "reasons" plus JSON do not get cut off mid-output.

TIMEOUT = 30  # seconds


# ===================== EXCEPTIONS =====================

class AIResponseError(Exception):
    """Raised when AI response doesn't match expected format."""
    pass


class AIProviderError(Exception):
    """Raised when AI provider configuration is invalid."""
    pass


# ===================== DATA MODELS =====================

class AIOutlook(BaseModel):
    """Validated structure for AI market outlook."""
    interpretation: Literal["Bullish", "Bearish", "Neutral"]
    reasons: str = Field(min_length=1, description="Non-empty rationale for the outlook")


# ===================== PROVIDER BASE CLASS =====================

class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, api_key: str):
        if not api_key:
            raise AIProviderError(f"{self.__class__.__name__} requires an API key")
        self.api_key = api_key

    @abstractmethod
    def send_request(self, prompt: str, crypto_symbol: str) -> AIOutlook:
        """Send request to AI provider and return validated outlook."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass


# ===================== ANTHROPIC PROVIDER =====================

class AnthropicProvider(AIProvider):
    """Anthropic (Claude) API provider."""

    URL = "https://api.anthropic.com/v1/messages"
    MODEL = "claude-sonnet-4-20250514"  # Latest Claude model
    API_VERSION = "2023-06-01"

    @property
    def name(self) -> str:
        return "Anthropic"

    def send_request(self, prompt: str, crypto_symbol: str) -> AIOutlook:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "Content-Type": "application/json"
        }

        tool_name = f"{crypto_symbol.lower()}_outlook"

        payload = {
            "model": self.MODEL,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "tools": [{
                "name": tool_name,
                "description": f"Return a structured {crypto_symbol} outlook for the next 24 hours.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "interpretation": {
                            "type": "string",
                            "enum": ["Bullish", "Bearish", "Neutral"],
                            "description": "Market outlook direction"
                        },
                        "reasons": {
                            "type": "string",
                            "description": "Concise rationale citing the strongest factors."
                        }
                    },
                    "required": ["interpretation", "reasons"]
                }
            }],
            "tool_choice": {"type": "tool", "name": tool_name},
            "messages": [{"role": "user", "content": prompt}]
        }

        r = requests.post(self.URL, headers=headers, json=payload, timeout=TIMEOUT)

        try:
            r.raise_for_status()
        except requests.HTTPError:
            logging.error(f"Anthropic API HTTP error {r.status_code}: {r.text}")
            raise

        data = r.json()

        # Anthropic returns tool use in content array
        try:
            tool_use = None
            for block in data.get("content", []):
                if block.get("type") == "tool_use":
                    tool_use = block
                    break

            if not tool_use:
                raise AIResponseError("No tool_use block in Anthropic response")

            if tool_use["name"] != tool_name:
                raise AIResponseError(
                    f"Unexpected tool called: {tool_use['name']}, expected {tool_name}"
                )

            args = tool_use["input"]

        except (KeyError, TypeError) as e:
            logging.error(f"Anthropic response parsing error: {e}")
            raise AIResponseError(f"Failed to parse Anthropic response: {e}")

        try:
            return AIOutlook(**args)
        except ValidationError as e:
            logging.error(f"Anthropic response failed validation: {e}")
            raise AIResponseError(f"Invalid response structure: {e}")


# ===================== XAI (GROK) PROVIDER =====================

class XAIProvider(AIProvider):
    """xAI (Grok) API provider - OpenAI-compatible."""

    URL = "https://api.x.ai/v1/chat/completions"
    MODEL = "grok-3-latest"  # Latest Grok model

    @property
    def name(self) -> str:
        return "xAI"

    def send_request(self, prompt: str, crypto_symbol: str) -> AIOutlook:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        tool_name = f"{crypto_symbol.lower()}_outlook"

        payload = {
            "model": self.MODEL,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [{
                "type": "function",
                "function": {
                    "name": tool_name,
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
            }],
            "tool_choice": {"type": "function", "function": {"name": tool_name}}
        }

        r = requests.post(self.URL, headers=headers, json=payload, timeout=TIMEOUT)

        try:
            r.raise_for_status()
        except requests.HTTPError:
            logging.error(f"xAI API HTTP error {r.status_code}: {r.text}")
            raise

        data = r.json()

        try:
            call = data["choices"][0]["message"]["tool_calls"][0]
        except (KeyError, IndexError) as e:
            logging.error(f"xAI response missing tool_calls: {e}")
            raise AIResponseError(f"Missing tool_calls in xAI response: {e}")

        if call["function"]["name"] != tool_name:
            raise AIResponseError(
                f"Unexpected function called: {call['function']['name']}, expected {tool_name}"
            )

        try:
            args = json.loads(call["function"]["arguments"])
        except json.JSONDecodeError as e:
            logging.error(f"xAI function arguments are not valid JSON: {e}")
            raise AIResponseError(f"Failed to parse function arguments: {e}")

        try:
            return AIOutlook(**args)
        except ValidationError as e:
            logging.error(f"xAI response failed validation: {e}")
            raise AIResponseError(f"Invalid response structure: {e}")


# ===================== DEEPSEEK PROVIDER (LEGACY) =====================

class DeepSeekProvider(AIProvider):
    """DeepSeek API provider (legacy/default)."""

    URL = "https://api.deepseek.com/beta/chat/completions"
    MODEL = "deepseek-chat"

    @property
    def name(self) -> str:
        return "DeepSeek"

    def send_request(self, prompt: str, crypto_symbol: str) -> AIOutlook:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        tool_name = f"{crypto_symbol.lower()}_outlook"

        payload = {
            "model": self.MODEL,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [{
                "type": "function",
                "strict": True,
                "function": {
                    "name": tool_name,
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
            }],
            "tool_choice": "auto"
        }

        r = requests.post(self.URL, headers=headers, json=payload, timeout=TIMEOUT)

        try:
            r.raise_for_status()
        except requests.HTTPError:
            logging.error(f"DeepSeek API HTTP error {r.status_code}: {r.text}")
            raise

        data = r.json()

        try:
            call = data["choices"][0]["message"]["tool_calls"][0]
        except (KeyError, IndexError) as e:
            logging.error(f"DeepSeek response missing tool_calls: {e}")
            raise AIResponseError(f"Missing tool_calls in response: {e}")

        if call["function"]["name"] != tool_name:
            raise AIResponseError(
                f"Unexpected function called: {call['function']['name']}, expected {tool_name}"
            )

        try:
            args = json.loads(call["function"]["arguments"])
        except json.JSONDecodeError as e:
            logging.error(f"DeepSeek function arguments are not valid JSON: {e}")
            raise AIResponseError(f"Failed to parse function arguments: {e}")

        try:
            return AIOutlook(**args)
        except ValidationError as e:
            logging.error(f"DeepSeek response failed validation: {e}")
            raise AIResponseError(f"Invalid response structure: {e}")


# ===================== PROVIDER FACTORY =====================

PROVIDERS = {
    "anthropic": AnthropicProvider,
    "xai": XAIProvider,
    "grok": XAIProvider,  # Alias
    "deepseek": DeepSeekProvider,
}


def get_provider(provider_name: str, api_key: str) -> AIProvider:
    """
    Factory function to create AI provider instance.

    Args:
        provider_name: One of "anthropic", "xai", "grok", "deepseek"
        api_key: API key for the provider

    Returns:
        AIProvider instance

    Raises:
        AIProviderError: If provider name is invalid
    """
    provider_name = provider_name.lower().strip()

    if provider_name not in PROVIDERS:
        valid = ", ".join(PROVIDERS.keys())
        raise AIProviderError(f"Unknown provider '{provider_name}'. Valid: {valid}")

    return PROVIDERS[provider_name](api_key)


# ===================== MAIN API (BACKWARD COMPATIBLE) =====================

# Global provider instance (set by init_provider or send_request)
_provider: AIProvider | None = None


def init_provider(provider_name: str, api_key: str) -> AIProvider:
    """
    Initialize the AI provider for the session.

    Args:
        provider_name: One of "anthropic", "xai", "grok", "deepseek"
        api_key: API key for the provider

    Returns:
        Configured AIProvider instance
    """
    global _provider
    _provider = get_provider(provider_name, api_key)
    logging.info(f"AI provider initialized: {_provider.name}")
    return _provider


def send_request(prompt: str, crypto_symbol: str, api_key: str = None,
                 provider_name: str = "deepseek") -> AIOutlook:
    """
    Send request to AI and return validated outlook.

    Backward compatible with original signature. For new code, use init_provider()
    first, then call send_request(prompt, crypto_symbol).

    Args:
        prompt: The prompt to send to the AI
        crypto_symbol: Cryptocurrency symbol (e.g., "Bitcoin")
        api_key: API key (optional if init_provider was called)
        provider_name: Provider to use if api_key is provided (default: deepseek)

    Returns:
        AIOutlook object with interpretation and reasons

    Raises:
        AIResponseError: If AI response is invalid
        AIProviderError: If provider is not configured
        requests.HTTPError: If API request fails
    """
    global _provider

    # If api_key provided, create/update provider (backward compatibility)
    if api_key:
        _provider = get_provider(provider_name, api_key)

    if not _provider:
        raise AIProviderError("No AI provider configured. Call init_provider() first.")

    return _provider.send_request(prompt, crypto_symbol)


# ===================== UTILITY FUNCTIONS =====================

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

        # Include provider info if available
        entry = outlook.model_dump()
        if _provider:
            entry["provider"] = _provider.name

        data[timestamp] = entry

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        logging.error(f"Failed to save AI response: {e}")


def list_providers() -> list[str]:
    """Return list of available provider names."""
    return list(PROVIDERS.keys())

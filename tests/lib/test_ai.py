"""
Tests for lib/ai.py - Multi-provider AI integration module
"""

import pytest
import json
from unittest.mock import Mock, patch
import requests

from lib.ai import (
    AIOutlook,
    AIProvider,
    AnthropicProvider,
    XAIProvider,
    DeepSeekProvider,
    get_provider,
    init_provider,
    send_request,
    save_response,
    list_providers,
    AIResponseError,
    AIProviderError,
)


class TestAIOutlook:
    """Test AIOutlook data model."""

    def test_valid_outlook(self):
        """Test creating a valid AIOutlook."""
        outlook = AIOutlook(
            interpretation="Bullish",
            reasons="Strong upward trend"
        )

        assert outlook.interpretation == "Bullish"
        assert outlook.reasons == "Strong upward trend"

    @pytest.mark.parametrize("interpretation", ["Bullish", "Bearish", "Neutral"])
    def test_valid_interpretations(self, interpretation):
        """Test all valid interpretation values."""
        outlook = AIOutlook(
            interpretation=interpretation,
            reasons="Test reasons"
        )

        assert outlook.interpretation == interpretation

    def test_invalid_interpretation(self):
        """Test invalid interpretation value."""
        with pytest.raises(ValueError):
            AIOutlook(
                interpretation="Invalid",
                reasons="Test"
            )

    def test_empty_reasons(self):
        """Test that empty reasons are invalid."""
        with pytest.raises(ValueError):
            AIOutlook(
                interpretation="Bullish",
                reasons=""
            )


class TestAnthropicProvider:
    """Test Anthropic (Claude) provider."""

    def test_initialization(self):
        """Test Anthropic provider initialization."""
        provider = AnthropicProvider("test_api_key")

        assert provider.api_key == "test_api_key"
        assert provider.name == "Anthropic"

    def test_initialization_no_api_key(self):
        """Test initialization without API key."""
        with pytest.raises(AIProviderError):
            AnthropicProvider("")

    @patch("requests.post")
    def test_send_request_success(self, mock_post, mock_anthropic_response):
        """Test successful Anthropic API request."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_anthropic_response

        provider = AnthropicProvider("test_key")
        result = provider.send_request("Test prompt", "Bitcoin")

        assert isinstance(result, AIOutlook)
        assert result.interpretation == "Bullish"
        assert "momentum" in result.reasons.lower()

    @patch("requests.post")
    def test_send_request_http_error(self, mock_post):
        """Test Anthropic API HTTP error handling."""
        mock_post.return_value.status_code = 401
        mock_post.return_value.raise_for_status.side_effect = requests.HTTPError()

        provider = AnthropicProvider("test_key")

        with pytest.raises(requests.HTTPError):
            provider.send_request("Test prompt", "Bitcoin")

    @patch("requests.post")
    def test_send_request_no_tool_use(self, mock_post):
        """Test response without tool_use block."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "content": [{"type": "text", "text": "No tool use"}]
        }

        provider = AnthropicProvider("test_key")

        with pytest.raises(AIResponseError):
            provider.send_request("Test prompt", "Bitcoin")


class TestXAIProvider:
    """Test xAI (Grok) provider."""

    def test_initialization(self):
        """Test xAI provider initialization."""
        provider = XAIProvider("test_api_key")

        assert provider.api_key == "test_api_key"
        assert provider.name == "xAI"

    @patch("requests.post")
    def test_send_request_success(self, mock_post, mock_xai_response):
        """Test successful xAI API request."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_xai_response

        provider = XAIProvider("test_key")
        result = provider.send_request("Test prompt", "Bitcoin")

        assert isinstance(result, AIOutlook)
        assert result.interpretation == "Bearish"

    @patch("requests.post")
    def test_send_request_invalid_json_args(self, mock_post):
        """Test xAI response with invalid JSON arguments."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "function": {
                            "name": "btcusdt_outlook",
                            "arguments": "invalid json"
                        }
                    }]
                }
            }]
        }

        provider = XAIProvider("test_key")

        with pytest.raises(AIResponseError):
            provider.send_request("Test prompt", "Bitcoin")


class TestDeepSeekProvider:
    """Test DeepSeek provider."""

    def test_initialization(self):
        """Test DeepSeek provider initialization."""
        provider = DeepSeekProvider("test_api_key")

        assert provider.api_key == "test_api_key"
        assert provider.name == "DeepSeek"

    @patch("requests.post")
    def test_send_request_success(self, mock_post):
        """Test successful DeepSeek API request."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "function": {
                            "name": "btcusdt_outlook",
                            "arguments": json.dumps({
                                "interpretation": "Neutral",
                                "reasons": "Mixed signals"
                            })
                        }
                    }]
                }
            }]
        }

        provider = DeepSeekProvider("test_key")
        result = provider.send_request("Test prompt", "Bitcoin")

        assert isinstance(result, AIOutlook)
        assert result.interpretation == "Neutral"


class TestProviderFactory:
    """Test provider factory functions."""

    @pytest.mark.parametrize("provider_name,expected_class", [
        ("anthropic", AnthropicProvider),
        ("xai", XAIProvider),
        ("grok", XAIProvider),  # Alias
        ("deepseek", DeepSeekProvider),
    ])
    def test_get_provider(self, provider_name, expected_class):
        """Test provider factory with all valid providers."""
        provider = get_provider(provider_name, "test_key")

        assert isinstance(provider, expected_class)

    def test_get_provider_invalid(self):
        """Test provider factory with invalid provider name."""
        with pytest.raises(AIProviderError, match="Unknown provider"):
            get_provider("invalid_provider", "test_key")

    def test_get_provider_case_insensitive(self):
        """Test provider factory is case insensitive."""
        provider1 = get_provider("ANTHROPIC", "test_key")
        provider2 = get_provider("anthropic", "test_key")

        assert type(provider1) == type(provider2)

    def test_list_providers(self):
        """Test listing available providers."""
        providers = list_providers()

        assert "anthropic" in providers
        assert "xai" in providers
        assert "deepseek" in providers
        assert len(providers) >= 4  # Including grok alias


class TestGlobalAPI:
    """Test global API functions."""

    def test_init_provider(self):
        """Test initializing global provider."""
        provider = init_provider("anthropic", "test_key")

        assert isinstance(provider, AnthropicProvider)

    @patch("requests.post")
    def test_send_request_with_init(self, mock_post, mock_anthropic_response):
        """Test send_request after init_provider."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_anthropic_response

        init_provider("anthropic", "test_key")
        result = send_request("Test prompt", "Bitcoin")

        assert isinstance(result, AIOutlook)

    @patch("requests.post")
    def test_send_request_with_api_key_param(self, mock_post, mock_anthropic_response):
        """Test send_request with API key parameter (backward compatibility)."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_anthropic_response

        result = send_request(
            "Test prompt",
            "Bitcoin",
            api_key="test_key",
            provider_name="anthropic"
        )

        assert isinstance(result, AIOutlook)

    def test_send_request_no_provider(self):
        """Test send_request without initializing provider."""
        # Reset global provider
        import lib.ai
        lib.ai._provider = None

        with pytest.raises(AIProviderError, match="No AI provider configured"):
            send_request("Test prompt", "Bitcoin")


class TestResponseSaving:
    """Test response saving functionality."""

    @patch("lib.ai._provider")
    def test_save_response(self, mock_provider, tmp_path, monkeypatch):
        """Test saving AI response to file."""
        mock_provider.name = "TestProvider"

        # Use temp directory
        monkeypatch.chdir(tmp_path)

        outlook = AIOutlook(
            interpretation="Bullish",
            reasons="Test reasons"
        )

        save_response(outlook, "test_run")

        # Verify file was created
        response_file = tmp_path / "ai_responses" / "test_run.json"
        assert response_file.exists()

        # Verify content
        with open(response_file) as f:
            data = json.load(f)
            timestamps = list(data.keys())
            assert len(timestamps) > 0

            entry = data[timestamps[0]]
            assert entry["interpretation"] == "Bullish"
            assert entry["provider"] == "TestProvider"

    def test_save_response_append(self, tmp_path, monkeypatch):
        """Test appending multiple responses to same file."""
        monkeypatch.chdir(tmp_path)

        outlook1 = AIOutlook(interpretation="Bullish", reasons="Reason 1")
        outlook2 = AIOutlook(interpretation="Bearish", reasons="Reason 2")

        save_response(outlook1, "test_run")
        save_response(outlook2, "test_run")

        # Verify both responses are in file
        response_file = tmp_path / "ai_responses" / "test_run.json"
        with open(response_file) as f:
            data = json.load(f)
            assert len(data) == 2


class TestRequestPayloads:
    """Test request payload construction."""

    @patch("requests.post")
    def test_anthropic_payload_structure(self, mock_post, mock_anthropic_response):
        """Test Anthropic request payload structure."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_anthropic_response

        provider = AnthropicProvider("test_key")
        provider.send_request("Test prompt", "Bitcoin")

        # Verify payload structure
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]

        assert payload["model"] == "claude-sonnet-4-20250514"
        assert "tools" in payload
        assert payload["tools"][0]["name"] == "bitcoin_outlook"
        assert payload["messages"][0]["content"] == "Test prompt"

    @patch("requests.post")
    def test_xai_payload_structure(self, mock_post, mock_xai_response):
        """Test xAI request payload structure."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_xai_response

        provider = XAIProvider("test_key")
        provider.send_request("Test prompt", "Ethereum")

        # Verify payload structure
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]

        assert payload["model"] == "grok-3-latest"
        assert "tools" in payload
        assert payload["tools"][0]["function"]["name"] == "ethereum_outlook"


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling across providers."""

    @pytest.mark.parametrize("ProviderClass", [
        AnthropicProvider,
        XAIProvider,
        DeepSeekProvider
    ])
    @patch("requests.post")
    def test_timeout_handling(self, mock_post, ProviderClass):
        """Test timeout handling for all providers."""
        mock_post.side_effect = requests.Timeout()

        provider = ProviderClass("test_key")

        with pytest.raises(requests.Timeout):
            provider.send_request("Test", "Bitcoin")

    @pytest.mark.parametrize("ProviderClass", [
        AnthropicProvider,
        XAIProvider,
        DeepSeekProvider
    ])
    @patch("requests.post")
    def test_connection_error(self, mock_post, ProviderClass):
        """Test connection error handling for all providers."""
        mock_post.side_effect = requests.ConnectionError()

        provider = ProviderClass("test_key")

        with pytest.raises(requests.ConnectionError):
            provider.send_request("Test", "Bitcoin")

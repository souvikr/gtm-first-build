"""
tests/test_score.py — tests for score.py

All OpenAI API calls are mocked — no real API key required.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import openai

import score as score_module
from score import _parse_json, call_openai_with_retry, score_signal


# ---------------------------------------------------------------------------
# _parse_json tests
# ---------------------------------------------------------------------------

class TestParseJson:
    def test_plain_json_string(self):
        raw = '{"score": 75, "tier": "warm", "reason": "good fit", "angle": "devtool angle"}'
        result = _parse_json(raw)
        assert result["score"] == 75
        assert result["tier"] == "warm"

    def test_json_wrapped_in_backtick_fence(self):
        raw = '```json\n{"score": 50, "tier": "warm", "reason": "ok", "angle": "a"}\n```'
        result = _parse_json(raw)
        assert result["score"] == 50

    def test_json_wrapped_in_plain_code_fence(self):
        raw = '```\n{"score": 30, "tier": "cold", "reason": "poor fit", "angle": ""}\n```'
        result = _parse_json(raw)
        assert result["score"] == 30

    def test_whitespace_is_stripped(self):
        raw = '   {"score": 10, "tier": "cold", "reason": "r", "angle": ""}   '
        result = _parse_json(raw)
        assert result["score"] == 10

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json("this is not json")

    def test_empty_string_raises(self):
        with pytest.raises((json.JSONDecodeError, ValueError)):
            _parse_json("")


# ---------------------------------------------------------------------------
# call_openai_with_retry tests
# ---------------------------------------------------------------------------

class TestCallOpenAIWithRetry:
    def test_returns_response_on_success(self, mock_openai_response):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response("hello")
        result = call_openai_with_retry(
            mock_client, "gpt-4o-mini",
            [{"role": "user", "content": "hi"}]
        )
        assert result.choices[0].message.content == "hello"

    def test_retries_on_transient_rate_limit(self, mock_openai_response):
        """Should retry up to 4 times on 429, then succeed."""
        mock_client = MagicMock()
        rate_limit_err = openai.RateLimitError(
            "too many requests", response=MagicMock(), body={}
        )
        success_resp = mock_openai_response("ok")
        mock_client.chat.completions.create.side_effect = [
            rate_limit_err, rate_limit_err, success_resp
        ]
        with patch("score.time.sleep"):  # skip actual sleep
            result = call_openai_with_retry(
                mock_client, "gpt-4o-mini",
                [{"role": "user", "content": "hi"}]
            )
        assert result.choices[0].message.content == "ok"

    def test_aborts_immediately_on_quota_error(self):
        """Quota-type 429 should raise immediately without retrying."""
        mock_client = MagicMock()
        quota_err = openai.RateLimitError(
            "You exceeded your current quota", response=MagicMock(), body={}
        )
        mock_client.chat.completions.create.side_effect = quota_err
        with patch("score.time.sleep"):
            with pytest.raises(openai.RateLimitError):
                call_openai_with_retry(
                    mock_client, "gpt-4o-mini",
                    [{"role": "user", "content": "hi"}]
                )
        # Should only be called once (no retries)
        assert mock_client.chat.completions.create.call_count == 1

    def test_raises_after_max_retries_exhausted(self):
        """If all retries fail on transient errors, re-raises the error."""
        mock_client = MagicMock()
        err = openai.RateLimitError("rate limited", response=MagicMock(), body={})
        mock_client.chat.completions.create.side_effect = err
        with patch("score.time.sleep"):
            with pytest.raises(openai.RateLimitError):
                call_openai_with_retry(
                    mock_client, "gpt-4o-mini",
                    [{"role": "user", "content": "hi"}]
                )


# ---------------------------------------------------------------------------
# score_signal tests
# ---------------------------------------------------------------------------

class TestScoreSignal:
    def _make_openai_response(self, content: str):
        msg = MagicMock()
        msg.content = content
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    @patch("score.call_openai_with_retry")
    def test_returns_valid_score_dict(self, mock_retry, sample_signal):
        json_body = json.dumps({
            "score": 75, "tier": "warm",
            "reason": "Good devtool ICP fit", "angle": "Show HN launch angle"
        })
        mock_retry.return_value = self._make_openai_response(json_body)
        result = score_signal(sample_signal)
        assert result["score"] == 75
        assert result["tier"] == "warm"
        assert "reason" in result
        assert "angle" in result

    @patch("score.call_openai_with_retry")
    def test_low_score_for_consumer_app(self, mock_retry, cold_signal):
        json_body = json.dumps({
            "score": 5, "tier": "cold",
            "reason": "Consumer app, not a B2B SaaS/devtool", "angle": ""
        })
        mock_retry.return_value = self._make_openai_response(json_body)
        result = score_signal(cold_signal)
        assert result["score"] < 60

    @patch("score.call_openai_with_retry")
    def test_returns_fallback_on_api_failure(self, mock_retry, sample_signal):
        """If the API call fails, returns fallback cold score."""
        mock_retry.side_effect = Exception("API is down")
        result = score_signal(sample_signal)
        assert result["score"] == 0
        assert result["tier"] == "cold"
        assert "api_failed" in result["reason"]

    @patch("score.call_openai_with_retry")
    def test_returns_fallback_on_bad_json(self, mock_retry, sample_signal):
        """If the model returns non-JSON, returns fallback cold score."""
        mock_retry.return_value = self._make_openai_response("I cannot score this.")
        result = score_signal(sample_signal)
        assert result["score"] == 0

    @patch("score.call_openai_with_retry")
    def test_prompt_includes_signal_fields(self, mock_retry, sample_signal):
        """Ensures the prompt passed to the API contains signal data."""
        json_body = json.dumps({
            "score": 80, "tier": "hot", "reason": "r", "angle": "a"
        })
        mock_retry.return_value = self._make_openai_response(json_body)
        score_signal(sample_signal)
        call_args = mock_retry.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][2]
        prompt = messages[0]["content"]
        assert sample_signal.company in prompt
        assert sample_signal.trigger in prompt

    @patch("score.call_openai_with_retry")
    def test_uses_json_object_response_format(self, mock_retry, sample_signal):
        """Ensures json_object mode is requested from the API."""
        mock_retry.return_value = self._make_openai_response(
            '{"score": 70, "tier": "warm", "reason": "r", "angle": "a"}'
        )
        score_signal(sample_signal)
        call_args = mock_retry.call_args
        rf = call_args[1].get("response_format") or call_args[0][3]
        assert rf == {"type": "json_object"}

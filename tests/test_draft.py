"""
tests/test_draft.py — tests for draft.py

All OpenAI API calls are mocked — no real API key required.
"""
import pytest
from unittest.mock import patch, MagicMock
import openai

from draft import call_openai_with_retry, draft_message


# ---------------------------------------------------------------------------
# call_openai_with_retry tests (draft.py version)
# ---------------------------------------------------------------------------

class TestDraftCallOpenAIWithRetry:
    def test_success_on_first_try(self):
        mock_client = MagicMock()
        msg = MagicMock()
        msg.content = "Great outreach message"
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        mock_client.chat.completions.create.return_value = resp

        result = call_openai_with_retry(mock_client, "gpt-4o", [{"role": "user", "content": "write a message"}])
        assert result.choices[0].message.content == "Great outreach message"

    def test_retries_on_transient_rate_limit(self):
        mock_client = MagicMock()
        rate_limit_err = openai.RateLimitError("rate limited", response=MagicMock(), body={})
        msg = MagicMock()
        msg.content = "message after retry"
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        mock_client.chat.completions.create.side_effect = [rate_limit_err, resp]

        with patch("draft.time.sleep"):
            result = call_openai_with_retry(mock_client, "gpt-4o", [{"role": "user", "content": "write"}])
        assert result.choices[0].message.content == "message after retry"
        assert mock_client.chat.completions.create.call_count == 2

    def test_aborts_on_quota_error(self):
        mock_client = MagicMock()
        quota_err = openai.RateLimitError("You exceeded your current quota", response=MagicMock(), body={})
        mock_client.chat.completions.create.side_effect = quota_err

        with patch("draft.time.sleep"):
            with pytest.raises(openai.RateLimitError):
                call_openai_with_retry(mock_client, "gpt-4o", [{"role": "user", "content": "write"}])
        assert mock_client.chat.completions.create.call_count == 1


# ---------------------------------------------------------------------------
# draft_message tests
# ---------------------------------------------------------------------------

class TestDraftMessage:
    def _make_openai_response(self, content: str):
        msg = MagicMock()
        msg.content = content
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    @patch("draft.call_openai_with_retry")
    def test_returns_draft_string(self, mock_retry, sample_signal, warm_score):
        expected = "Hey, saw your launch on HN — great work on the CLI. Let's talk."
        mock_retry.return_value = self._make_openai_response(expected)
        result = draft_message(sample_signal, warm_score)
        assert result == expected

    @patch("draft.call_openai_with_retry")
    def test_draft_strips_whitespace(self, mock_retry, sample_signal, warm_score):
        mock_retry.return_value = self._make_openai_response("  trimmed message  ")
        result = draft_message(sample_signal, warm_score)
        assert result == "trimmed message"

    @patch("draft.call_openai_with_retry")
    def test_returns_empty_on_api_failure(self, mock_retry, sample_signal, warm_score):
        mock_retry.side_effect = Exception("API is down")
        result = draft_message(sample_signal, warm_score)
        assert result == ""

    @patch("draft.call_openai_with_retry")
    def test_prompt_includes_signal_context(self, mock_retry, sample_signal, warm_score):
        mock_retry.return_value = self._make_openai_response("a draft")
        draft_message(sample_signal, warm_score)
        call_args = mock_retry.call_args
        messages = call_args[1].get("messages") or call_args[0][2]
        prompt = messages[0]["content"]
        assert sample_signal.context in prompt
        assert sample_signal.url in prompt

    @patch("draft.call_openai_with_retry")
    def test_prompt_includes_score_angle(self, mock_retry, sample_signal, warm_score):
        mock_retry.return_value = self._make_openai_response("a draft")
        draft_message(sample_signal, warm_score)
        call_args = mock_retry.call_args
        messages = call_args[1].get("messages") or call_args[0][2]
        prompt = messages[0]["content"]
        assert warm_score["angle"] in prompt

    @patch("draft.call_openai_with_retry")
    def test_score_with_missing_angle_is_handled(self, mock_retry, sample_signal):
        """score dict without 'angle' key should not raise."""
        mock_retry.return_value = self._make_openai_response("a draft")
        score_no_angle = {"score": 70, "tier": "warm", "reason": "good"}
        result = draft_message(sample_signal, score_no_angle)
        assert result == "a draft"

    @patch("draft.call_openai_with_retry")
    def test_uses_gpt4o_model(self, mock_retry, sample_signal, warm_score):
        """Ensures we're using the higher-quality draft model."""
        import draft as draft_module
        mock_retry.return_value = self._make_openai_response("a draft")
        draft_message(sample_signal, warm_score)
        call_args = mock_retry.call_args
        model = call_args[1].get("model") or call_args[0][1]
        assert model == draft_module.DRAFT_MODEL

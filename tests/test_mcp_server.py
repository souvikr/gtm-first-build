"""
tests/test_mcp_server.py — tests for mcp_server.py

All 6 MCP tools are exercised with mocked dependencies.
No real API calls or file system side-effects outside of tmp directories.
"""
import csv
import os
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Import the tool functions directly (bypassing FastMCP registration)
# ---------------------------------------------------------------------------
import mcp_server
from mcp_server import (
    fetch_signals,
    score_icp,
    enrich_contact,
    draft_message,
    queue_for_review,
    log_outcome,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signal_dict(company="Acme Dev Tools"):
    return {
        "source": "hn_show",
        "trigger": "Launched a new product on Show HN",
        "company": company,
        "context": f"{company} — fast cloud CLI for devs",
        "url": "https://news.ycombinator.com/item?id=123",
        "found_at": "2026-07-20T12:00:00",
    }


def _make_score_dict(score=75, tier="warm"):
    return {
        "score": score,
        "tier": tier,
        "reason": "Good ICP fit.",
        "angle": "Position our GTM engineering against their HN launch momentum."
    }


# ===========================================================================
# fetch_signals
# ===========================================================================

class TestFetchSignals:
    @patch("mcp_server.fetch_hiring_gtm")
    @patch("mcp_server.fetch_show_hn")
    def test_hn_show_source_calls_fetch_show_hn(self, mock_show, mock_hiring):
        from gtm_agent.signals import Signal
        mock_show.return_value = [
            Signal(source="hn_show", trigger="t", company="Co", context="c", url="u")
        ]
        mock_hiring.return_value = []
        result = fetch_signals(sources=["hn_show"], since_hours=24)
        mock_show.assert_called_once_with(hours=24)
        mock_hiring.assert_not_called()
        assert len(result) == 1
        assert result[0]["company"] == "Co"

    @patch("mcp_server.fetch_hiring_gtm")
    @patch("mcp_server.fetch_show_hn")
    def test_hn_hiring_source_calls_fetch_hiring_gtm(self, mock_show, mock_hiring):
        from gtm_agent.signals import Signal
        mock_show.return_value = []
        mock_hiring.return_value = [
            Signal(source="hn_hiring", trigger="t", company="X", context="c", url="u")
        ]
        result = fetch_signals(sources=["hn_hiring"], since_hours=72)
        mock_hiring.assert_called_once_with(hours=72)
        mock_show.assert_not_called()
        assert result[0]["source"] == "hn_hiring"

    @patch("mcp_server.fetch_hiring_gtm")
    @patch("mcp_server.fetch_show_hn")
    def test_both_sources_combined(self, mock_show, mock_hiring):
        from gtm_agent.signals import Signal
        mock_show.return_value = [
            Signal(source="hn_show", trigger="t", company="A", context="c", url="u")
        ]
        mock_hiring.return_value = [
            Signal(source="hn_hiring", trigger="t", company="B", context="c", url="u")
        ]
        result = fetch_signals(sources=["hn_show", "hn_hiring"])
        assert len(result) == 2

    @patch("mcp_server.fetch_hiring_gtm")
    @patch("mcp_server.fetch_show_hn")
    def test_unknown_source_is_ignored(self, mock_show, mock_hiring):
        mock_show.return_value = []
        mock_hiring.return_value = []
        result = fetch_signals(sources=["nonexistent_source"])
        assert result == []

    @patch("mcp_server.fetch_hiring_gtm")
    @patch("mcp_server.fetch_show_hn")
    def test_returns_dicts_not_signal_objects(self, mock_show, mock_hiring):
        from gtm_agent.signals import Signal
        mock_show.return_value = [
            Signal(source="hn_show", trigger="t", company="Co", context="c", url="u")
        ]
        mock_hiring.return_value = []
        result = fetch_signals(sources=["hn_show"])
        assert isinstance(result[0], dict)
        assert "company" in result[0]


# ===========================================================================
# score_icp
# ===========================================================================

class TestScoreICP:
    @patch("mcp_server.score_signal")
    def test_returns_score_dict(self, mock_score):
        mock_score.return_value = _make_score_dict()
        signal = _make_signal_dict()
        result = score_icp(signal)
        assert result["score"] == 75
        assert result["tier"] == "warm"

    @patch("mcp_server.score_signal")
    def test_constructs_signal_from_dict(self, mock_score):
        mock_score.return_value = _make_score_dict()
        signal = _make_signal_dict(company="NewCo")
        score_icp(signal)
        called_signal = mock_score.call_args[0][0]
        assert called_signal.company == "NewCo"

    @patch("mcp_server.score_signal")
    def test_missing_found_at_uses_default(self, mock_score):
        mock_score.return_value = _make_score_dict()
        signal = _make_signal_dict()
        del signal["found_at"]
        score_icp(signal)  # Should not raise

    @patch("mcp_server.score_signal")
    def test_score_propagates_api_failure(self, mock_score):
        """If score_signal fails, the exception should propagate."""
        mock_score.side_effect = Exception("API failure")
        with pytest.raises(Exception, match="API failure"):
            score_icp(_make_signal_dict())


# ===========================================================================
# enrich_contact
# ===========================================================================

class TestEnrichContact:
    def test_returns_dict_with_required_fields(self):
        result = enrich_contact("Acme Corp")
        assert "email" in result
        assert "name" in result
        assert "title" in result
        assert "verified" in result

    def test_email_contains_company_name(self):
        result = enrich_contact("Acme")
        assert "acme" in result["email"]

    def test_email_format_is_valid(self):
        result = enrich_contact("MyStartup")
        email = result["email"]
        assert "@" in email
        assert "." in email.split("@")[1]

    def test_special_chars_stripped_from_email(self):
        """Company names with spaces/punctuation → clean email."""
        result = enrich_contact("Acme Dev Tools!")
        email = result["email"]
        # Should not contain spaces, exclamation marks etc.
        assert " " not in email
        assert "!" not in email

    def test_verified_is_true(self):
        result = enrich_contact("AnyCompany")
        assert result["verified"] is True

    def test_empty_company_name_returns_fallback_email(self):
        result = enrich_contact("")
        assert "unknowncompany" in result["email"]

    def test_name_references_company(self):
        result = enrich_contact("Acme")
        assert "Acme" in result["name"]

    def test_title_is_founder(self):
        result = enrich_contact("Acme")
        assert "Founder" in result["title"] or "CEO" in result["title"]


# ===========================================================================
# draft_message
# ===========================================================================

class TestDraftMessage:
    @patch("mcp_server.dm")
    def test_returns_draft_string(self, mock_dm):
        mock_dm.return_value = "Here's your personalized message."
        result = draft_message(_make_signal_dict(), _make_score_dict())
        assert result == "Here's your personalized message."

    @patch("mcp_server.dm")
    def test_constructs_signal_from_dict(self, mock_dm):
        mock_dm.return_value = "a draft"
        signal = _make_signal_dict(company="TestCo")
        draft_message(signal, _make_score_dict())
        called_signal = mock_dm.call_args[0][0]
        assert called_signal.company == "TestCo"

    @patch("mcp_server.dm")
    def test_passes_score_dict_to_dm(self, mock_dm):
        mock_dm.return_value = "a draft"
        score = _make_score_dict(score=90, tier="hot")
        draft_message(_make_signal_dict(), score)
        called_score = mock_dm.call_args[0][1]
        assert called_score["score"] == 90

    @patch("mcp_server.dm")
    def test_api_failure_propagates(self, mock_dm):
        mock_dm.side_effect = Exception("LLM error")
        with pytest.raises(Exception, match="LLM error"):
            draft_message(_make_signal_dict(), _make_score_dict())


# ===========================================================================
# queue_for_review
# ===========================================================================

class TestQueueForReview:
    def test_writes_record_to_csv(self, tmp_path, sample_record, monkeypatch):
        csv_path = tmp_path / "review_queue.csv"
        monkeypatch.chdir(tmp_path)

        result = queue_for_review(sample_record)

        assert result == "ok"
        assert csv_path.exists()
        rows = list(csv.DictReader(csv_path.open()))
        assert len(rows) == 1
        assert rows[0]["company"] == sample_record["company"]

    def test_status_is_always_needs_review(self, tmp_path, sample_record, monkeypatch):
        monkeypatch.chdir(tmp_path)
        queue_for_review(sample_record)
        rows = list(csv.DictReader((tmp_path / "review_queue.csv").open()))
        assert rows[0]["status"] == "NEEDS_REVIEW"

    def test_creates_header_on_first_write(self, tmp_path, sample_record, monkeypatch):
        monkeypatch.chdir(tmp_path)
        queue_for_review(sample_record)
        content = (tmp_path / "review_queue.csv").read_text()
        assert "company" in content.splitlines()[0]

    def test_appends_on_subsequent_writes(self, tmp_path, sample_record, monkeypatch):
        monkeypatch.chdir(tmp_path)
        queue_for_review(sample_record)
        queue_for_review({**sample_record, "company": "Second Co"})
        rows = list(csv.DictReader((tmp_path / "review_queue.csv").open()))
        assert len(rows) == 2

    def test_returns_ok_string(self, tmp_path, sample_record, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = queue_for_review(sample_record)
        assert result == "ok"

    def test_missing_fields_replaced_with_empty_string(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        minimal_record = {"company": "MinimalCo"}
        result = queue_for_review(minimal_record)
        assert result == "ok"
        rows = list(csv.DictReader((tmp_path / "review_queue.csv").open()))
        assert rows[0]["draft"] == ""


# ===========================================================================
# log_outcome
# ===========================================================================

class TestLogOutcome:
    def test_writes_outcome_to_csv(self, tmp_path, sample_record, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = log_outcome(sample_record, "replied")
        assert result == "ok"
        csv_path = tmp_path / "outcome_log.csv"
        assert csv_path.exists()
        rows = list(csv.DictReader(csv_path.open()))
        assert rows[0]["result"] == "replied"
        assert rows[0]["company"] == sample_record["company"]

    def test_timestamp_is_set(self, tmp_path, sample_record, monkeypatch):
        monkeypatch.chdir(tmp_path)
        log_outcome(sample_record, "meeting_booked")
        rows = list(csv.DictReader((tmp_path / "outcome_log.csv").open()))
        assert rows[0]["timestamp"]  # non-empty

    def test_appends_multiple_outcomes(self, tmp_path, sample_record, monkeypatch):
        monkeypatch.chdir(tmp_path)
        log_outcome(sample_record, "replied")
        log_outcome({**sample_record, "company": "Another Co"}, "bounced")
        rows = list(csv.DictReader((tmp_path / "outcome_log.csv").open()))
        assert len(rows) == 2

    def test_all_valid_result_types_accepted(self, tmp_path, sample_record, monkeypatch):
        monkeypatch.chdir(tmp_path)
        for outcome in ["replied", "meeting_booked", "bounced", "ignored"]:
            log_outcome(sample_record, outcome)
        rows = list(csv.DictReader((tmp_path / "outcome_log.csv").open()))
        assert len(rows) == 4

    def test_returns_ok_string(self, tmp_path, sample_record, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = log_outcome(sample_record, "replied")
        assert result == "ok"

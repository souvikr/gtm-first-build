"""
tests/test_run.py — integration tests for the run.py main pipeline.

All external calls (signals, scoring, drafting) are mocked so this
runs without any API key or network access.
"""
import csv
import os
import pytest
from unittest.mock import patch, MagicMock
from dataclasses import asdict
from signals import Signal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signal(company="Acme Dev Tools", score=75):
    return Signal(
        source="hn_show",
        trigger="Launched a new product on Show HN",
        company=company,
        context=f"{company} — fast cloud CLI",
        url="https://news.ycombinator.com/item?id=111",
    ), {"score": score, "tier": "warm", "reason": "good fit", "angle": "launch angle"}


# ---------------------------------------------------------------------------
# Tests for main() pipeline
# ---------------------------------------------------------------------------

class TestRunPipeline:
    @patch("run.draft_message")
    @patch("run.score_signal")
    @patch("run.fetch_all")
    def test_writes_review_queue_csv(self, mock_fetch, mock_score, mock_draft, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sig, sc = _make_signal()
        mock_fetch.return_value = [sig]
        mock_score.return_value = sc
        mock_draft.return_value = "Here's your outreach message."

        from run import main
        main()

        csv_path = tmp_path / "review_queue.csv"
        assert csv_path.exists()
        rows = list(csv.DictReader(csv_path.open()))
        assert len(rows) == 1
        assert rows[0]["company"] == "Acme Dev Tools"
        assert rows[0]["draft"] == "Here's your outreach message."

    @patch("run.draft_message")
    @patch("run.score_signal")
    @patch("run.fetch_all")
    def test_below_threshold_signals_not_drafted(self, mock_fetch, mock_score, mock_draft, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sig, _ = _make_signal(score=30)
        mock_fetch.return_value = [sig]
        mock_score.return_value = {"score": 30, "tier": "cold", "reason": "consumer app", "angle": ""}

        from run import main
        main()

        mock_draft.assert_not_called()
        assert not (tmp_path / "review_queue.csv").exists()

    @patch("run.draft_message")
    @patch("run.score_signal")
    @patch("run.fetch_all")
    def test_rows_sorted_by_score_descending(self, mock_fetch, mock_score, mock_draft, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sig_low, _ = _make_signal("LowCo", score=65)
        sig_high, _ = _make_signal("HighCo", score=90)
        mock_fetch.return_value = [sig_low, sig_high]
        mock_score.side_effect = [
            {"score": 65, "tier": "warm", "reason": "ok", "angle": "a"},
            {"score": 90, "tier": "hot", "reason": "great", "angle": "b"},
        ]
        mock_draft.side_effect = ["draft for low", "draft for high"]

        from run import main
        main()

        rows = list(csv.DictReader((tmp_path / "review_queue.csv").open()))
        assert rows[0]["company"] == "HighCo"
        assert rows[1]["company"] == "LowCo"

    @patch("run.draft_message")
    @patch("run.score_signal")
    @patch("run.fetch_all")
    def test_no_signals_prints_empty_message(self, mock_fetch, mock_score, mock_draft, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        mock_fetch.return_value = []

        from run import main
        main()

        captured = capsys.readouterr()
        assert "No signals" in captured.out
        mock_score.assert_not_called()

    @patch("run.draft_message")
    @patch("run.score_signal")
    @patch("run.fetch_all")
    def test_status_field_is_needs_review(self, mock_fetch, mock_score, mock_draft, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sig, sc = _make_signal()
        mock_fetch.return_value = [sig]
        mock_score.return_value = sc
        mock_draft.return_value = "message"

        from run import main
        main()

        rows = list(csv.DictReader((tmp_path / "review_queue.csv").open()))
        assert rows[0]["status"] == "NEEDS_REVIEW"

    @patch("run.draft_message")
    @patch("run.score_signal")
    @patch("run.fetch_all")
    def test_multiple_passing_signals_all_written(self, mock_fetch, mock_score, mock_draft, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        signals = [_make_signal(f"Co{i}", score=70)[0] for i in range(3)]
        mock_fetch.return_value = signals
        mock_score.side_effect = [
            {"score": 70, "tier": "warm", "reason": "r", "angle": "a"} for _ in range(3)
        ]
        mock_draft.side_effect = [f"draft {i}" for i in range(3)]

        from run import main
        main()

        rows = list(csv.DictReader((tmp_path / "review_queue.csv").open()))
        assert len(rows) == 3

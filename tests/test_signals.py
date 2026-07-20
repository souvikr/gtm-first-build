"""
tests/test_signals.py — tests for signals.py

Tests are fully offline (no real HTTP calls).
The HN Algolia API is mocked via requests.
"""
import pytest
from unittest.mock import patch, MagicMock
from signals import Signal, fetch_show_hn, fetch_hiring_gtm, fetch_all


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _hn_show_response(items=None):
    """Build a fake Algolia API response for Show HN searches."""
    if items is None:
        items = [
            {
                "title": "Show HN: Acme Dev Tools — fast cloud CLI",
                "url": "https://acmedevtools.io",
                "objectID": "111",
            },
            {
                "title": "Show HN: CoolApp — another product",
                "url": None,  # missing URL edge-case
                "objectID": "222",
            },
        ]
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"hits": items}
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def _hn_hiring_response(items=None):
    """Build a fake Algolia API response for hiring comment searches."""
    if items is None:
        items = [
            {
                "comment_text": "We are hiring a RevOps engineer to own our GTM stack.",
                "objectID": "333",
            },
            {
                "comment_text": "",   # empty comment edge-case
                "objectID": "444",
            },
        ]
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"hits": items}
    mock_resp.raise_for_status.return_value = None
    return mock_resp


# ---------------------------------------------------------------------------
# Signal dataclass tests
# ---------------------------------------------------------------------------

class TestSignalDataclass:
    def test_signal_has_required_fields(self):
        sig = Signal(
            source="hn_show",
            trigger="Launched a new product on Show HN",
            company="Acme",
            context="Acme Dev Tools — fast cloud CLI",
            url="https://acmedevtools.io",
        )
        assert sig.source == "hn_show"
        assert sig.trigger == "Launched a new product on Show HN"
        assert sig.company == "Acme"
        assert sig.context == "Acme Dev Tools — fast cloud CLI"
        assert sig.url == "https://acmedevtools.io"

    def test_signal_found_at_auto_populated(self):
        sig = Signal(source="hn_show", trigger="t", company="c", context="ctx", url="u")
        assert sig.found_at  # auto-generated ISO timestamp

    def test_signal_can_override_found_at(self):
        sig = Signal(source="hn_show", trigger="t", company="c", context="ctx",
                     url="u", found_at="2026-01-01T00:00:00")
        assert sig.found_at == "2026-01-01T00:00:00"


# ---------------------------------------------------------------------------
# fetch_show_hn tests
# ---------------------------------------------------------------------------

class TestFetchShowHN:
    @patch("signals.requests.get")
    def test_returns_list_of_signals(self, mock_get):
        mock_get.return_value = _hn_show_response()
        signals = fetch_show_hn(hours=24, max_items=10)
        assert isinstance(signals, list)
        assert len(signals) == 2

    @patch("signals.requests.get")
    def test_signal_has_correct_source(self, mock_get):
        mock_get.return_value = _hn_show_response()
        signals = fetch_show_hn()
        for sig in signals:
            assert sig.source == "hn_show"

    @patch("signals.requests.get")
    def test_signal_trigger_describes_show_hn(self, mock_get):
        mock_get.return_value = _hn_show_response()
        signals = fetch_show_hn()
        assert "Show HN" in signals[0].trigger

    @patch("signals.requests.get")
    def test_missing_url_falls_back_to_hn_item_url(self, mock_get):
        """When a hit has no URL, the fallback is the HN item page."""
        mock_get.return_value = _hn_show_response()
        signals = fetch_show_hn()
        # Second item has url=None → should use HN item URL
        assert "news.ycombinator.com" in signals[1].url

    @patch("signals.requests.get")
    def test_company_name_stripped_of_show_hn_prefix(self, mock_get):
        mock_get.return_value = _hn_show_response()
        signals = fetch_show_hn()
        # "Show HN:" prefix should be stripped
        assert not signals[0].company.startswith("Show HN")

    @patch("signals.requests.get")
    def test_empty_hits_returns_empty_list(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"hits": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        signals = fetch_show_hn()
        assert signals == []

    @patch("signals.requests.get")
    def test_correct_query_params_sent(self, mock_get):
        mock_get.return_value = _hn_show_response()
        fetch_show_hn(hours=48, max_items=5)
        _, kwargs = mock_get.call_args
        params = kwargs.get("params", {})
        assert params.get("tags") == "show_hn"
        assert params.get("hitsPerPage") == 5


# ---------------------------------------------------------------------------
# fetch_hiring_gtm tests
# ---------------------------------------------------------------------------

class TestFetchHiringGTM:
    @patch("signals.requests.get")
    def test_returns_list_of_signals(self, mock_get):
        mock_get.return_value = _hn_hiring_response()
        signals = fetch_hiring_gtm(hours=72)
        assert isinstance(signals, list)
        # The empty-comment item should be filtered out
        assert len(signals) == 1

    @patch("signals.requests.get")
    def test_signal_source_is_hn_hiring(self, mock_get):
        mock_get.return_value = _hn_hiring_response()
        signals = fetch_hiring_gtm()
        assert signals[0].source == "hn_hiring"

    @patch("signals.requests.get")
    def test_empty_comments_are_skipped(self, mock_get):
        mock_get.return_value = _hn_hiring_response()
        signals = fetch_hiring_gtm()
        # Should only have 1 (the non-empty comment)
        assert len(signals) == 1

    @patch("signals.requests.get")
    def test_context_truncated_to_500_chars(self, mock_get):
        long_text = "A" * 1000
        items = [{"comment_text": long_text, "objectID": "1"}]
        mock_get.return_value = _hn_hiring_response(items)
        signals = fetch_hiring_gtm()
        assert len(signals[0].context) <= 500


# ---------------------------------------------------------------------------
# fetch_all tests
# ---------------------------------------------------------------------------

class TestFetchAll:
    @patch("signals.fetch_hiring_gtm")
    @patch("signals.fetch_show_hn")
    def test_combines_both_sources(self, mock_show, mock_hiring):
        mock_show.return_value = [
            Signal(source="hn_show", trigger="t", company="A", context="c", url="u")
        ]
        mock_hiring.return_value = [
            Signal(source="hn_hiring", trigger="t", company="B", context="c", url="u")
        ]
        all_signals = fetch_all(hours=24)
        assert len(all_signals) == 2

    @patch("signals.fetch_hiring_gtm")
    @patch("signals.fetch_show_hn")
    def test_returns_correct_types(self, mock_show, mock_hiring):
        mock_show.return_value = []
        mock_hiring.return_value = []
        all_signals = fetch_all()
        assert isinstance(all_signals, list)

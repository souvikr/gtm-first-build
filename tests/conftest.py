"""
tests/conftest.py — shared fixtures for all GTM pipeline tests.
"""
import pytest
from unittest.mock import MagicMock
from gtm_agent.signals import Signal


@pytest.fixture
def sample_signal():
    """A typical Show HN signal for testing."""
    return Signal(
        source="hn_show",
        trigger="Launched a new product on Show HN",
        company="Acme Dev Tools",
        context="Acme Dev Tools — a blazing-fast CLI for managing cloud infrastructure",
        url="https://news.ycombinator.com/item?id=12345",
    )


@pytest.fixture
def cold_signal():
    """A consumer app signal that should score cold."""
    return Signal(
        source="hn_show",
        trigger="Launched a new product on Show HN",
        company="Fun Cat Game",
        context="Fun Cat Game — play with cats on your phone",
        url="https://news.ycombinator.com/item?id=99999",
    )


@pytest.fixture
def hiring_signal():
    """A typical HN hiring signal."""
    return Signal(
        source="hn_hiring",
        trigger="Hiring for a GTM / RevOps / growth role",
        company="see context",
        context="We are hiring a RevOps Engineer to own our GTM stack end-to-end.",
        url="https://news.ycombinator.com/item?id=77777",
    )


@pytest.fixture
def warm_score():
    """A warm score result for testing draft generation."""
    return {
        "score": 75,
        "tier": "warm",
        "reason": "Technical B2B devtool launch aligns well with ICP.",
        "angle": "Offer to engineer their launch GTM playbook based on the Show HN momentum."
    }


@pytest.fixture
def hot_score():
    """A hot score result."""
    return {
        "score": 90,
        "tier": "hot",
        "reason": "AI-native devtool with active community — exact ICP match.",
        "angle": "Signal-based outbound can convert HN upvotes into pipeline in 48h."
    }


@pytest.fixture
def mock_openai_response():
    """Factory that builds a mock OpenAI chat completion response."""
    def _make(content: str):
        msg = MagicMock()
        msg.content = content
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp
    return _make


@pytest.fixture
def sample_record(sample_signal, warm_score):
    """A full lead record as it would be assembled by the pipeline."""
    return {
        "source": sample_signal.source,
        "trigger": sample_signal.trigger,
        "company": sample_signal.company,
        "context": sample_signal.context,
        "url": sample_signal.url,
        "found_at": sample_signal.found_at,
        **warm_score,
        "email": "founder@acmedevtools.com",
        "name": "Founder of Acme Dev Tools",
        "title": "Founder & CEO",
        "verified": True,
        "draft": "Hey, saw Acme Dev Tools launch on HN — nice work. We help devtools like yours build signal-based outbound. Worth a quick chat?",
        "status": "NEEDS_REVIEW",
    }

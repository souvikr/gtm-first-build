"""
signals.py — pull buying signals from free sources (no API key needed).

Two starter signals, both real intent:
  1. Show HN launches   -> a new product that needs distribution  (Scale Intelligence's ICP)
  2. "Who is hiring" GTM/RevOps roles -> a company with GTM pain AND budget

Swap or add sources here. Everything downstream just consumes Signal objects.
"""

import requests
from dataclasses import dataclass, field
from datetime import datetime, timedelta

HN_SEARCH = "https://hn.algolia.com/api/v1/search_by_date"


@dataclass
class Signal:
    source: str      # where it came from
    trigger: str     # what happened (the buying event)
    company: str     # who it's about
    context: str     # raw text we can personalize from
    url: str
    found_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


def fetch_show_hn(hours: int = 24, max_items: int = 30):
    """New Show HN launches = fresh products that need go-to-market."""
    cutoff = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
    params = {
        "tags": "show_hn",
        "numericFilters": f"created_at_i>{cutoff}",
        "hitsPerPage": max_items,
    }
    r = requests.get(HN_SEARCH, params=params, timeout=20)
    r.raise_for_status()
    out = []
    for hit in r.json().get("hits", []):
        title = (hit.get("title") or "").replace("Show HN:", "").strip()
        company = title.split("–")[0].split("-")[0].strip()[:80]
        out.append(Signal(
            source="hn_show",
            trigger="Launched a new product on Show HN",
            company=company or "unknown",
            context=title,
            url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
        ))
    return out


def fetch_hiring_gtm(hours: int = 72, max_items: int = 30):
    """HN comments mentioning GTM/RevOps/growth hiring = pain + budget."""
    cutoff = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
    params = {
        "query": "GTM RevOps growth engineer",
        "tags": "comment",
        "numericFilters": f"created_at_i>{cutoff}",
        "hitsPerPage": max_items,
    }
    r = requests.get(HN_SEARCH, params=params, timeout=20)
    r.raise_for_status()
    out = []
    for hit in r.json().get("hits", []):
        text = (hit.get("comment_text") or "")[:500]
        if not text:
            continue
        out.append(Signal(
            source="hn_hiring",
            trigger="Hiring for a GTM / RevOps / growth role",
            company="see context",
            context=text,
            url=f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
        ))
    return out


def fetch_all(hours: int = 24):
    return fetch_show_hn(hours=hours) + fetch_hiring_gtm(hours=hours * 3)


if __name__ == "__main__":
    for s in fetch_all()[:5]:
        print(s.trigger, "|", s.company, "|", s.context[:60])

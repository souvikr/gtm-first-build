"""
run.py — v0 pipeline: signal -> score -> draft -> human review queue.

Deliberately does NOT send anything. It writes review_queue.csv.
You (a human) read it, approve the good ones, enrich for a real email, then send.
That gate is the difference between a useful system and a spam cannon.

    export ANTHROPIC_API_KEY=sk-...
    python run.py
"""

import csv
from dataclasses import asdict

from signals import fetch_all
from score import score_signal
from draft import draft_message

MIN_SCORE = 60  # only draft for warm+ signals


def main():
    rows = []
    # Limit to 5 for quick end-to-end testing under free tier rate limits
    signals = fetch_all(hours=24)[:5]
    print(f"Fetched {len(signals)} raw signals for testing")

    for i, sig in enumerate(signals, 1):
        print(f"[{i}/{len(signals)}] Processing company: {sig.company}...")
        s = score_signal(sig)
        print(f"    ICP Fit Score: {s['score']} ({s['tier']}) - Reason: {s['reason']}")
        if s["score"] < MIN_SCORE:
            continue
        print(f"    Fit is above threshold. Drafting personalized outreach...")
        draft = draft_message(sig, s)
        rows.append({
            **asdict(sig),
            "score": s["score"],
            "tier": s["tier"],
            "reason": s["reason"],
            "angle": s["angle"],
            "draft": draft,
            "status": "NEEDS_REVIEW",
        })

    if not rows:
        print("No signals cleared the score threshold today.")
        return

    rows.sort(key=lambda r: r["score"], reverse=True)
    with open("review_queue.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} drafts written to review_queue.csv (highest score first)")


if __name__ == "__main__":
    main()

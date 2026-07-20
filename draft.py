"""
draft.py — generate a personalized outreach draft grounded in the actual signal.

Sonnet for drafting: the quality gap over Haiku shows up in copy.
NOTE: this DRAFTS only. Nothing is sent. A human reviews before anything goes out.
"""

import os
import time
import openai
client = OpenAI()

DRAFT_MODEL = "gpt-4o"

VOICE = """Concise, specific, peer-to-peer. No "I hope this finds you well". No hype.
Open with the specific thing they actually did (cite the signal). One crisp reason we're
relevant. One soft, low-friction CTA. Under 85 words. Sound like a sharp engineer who
noticed something, not a sales rep running a sequence."""


def call_openai_with_retry(client, model, messages, max_tokens=None):
    max_retries = 5
    delay = 10
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens
            )
        except openai.RateLimitError as e:
            if "quota" in str(e).lower():
                print(f"Quota exceeded for model {model}. Aborting retries.")
                raise e
            if attempt < max_retries - 1:
                print(f"Rate limit hit (429) for model {model}. Retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
                delay *= 2
            else:
                raise e


def draft_message(signal, score: dict) -> str:
    prompt = f"""Write one cold outreach message (usable as email or LinkedIn DM).

About us: we build GTM engineering systems (signal-based outbound, content engineering,
GEO/AI-search) for B2B and devtool startups.

Their signal: {signal.trigger} — {signal.context}
Why we're relevant (angle): {score.get('angle', '')}
Reference link: {signal.url}

Voice rules: {VOICE}

Return only the message body, nothing else."""
    try:
        response = call_openai_with_retry(
            client=client,
            model=DRAFT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Failed to draft message for {signal.company}: {e}")
        return ""

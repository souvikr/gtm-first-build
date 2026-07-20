"""
score.py — use Claude to score each signal against your ICP.

Cheap model (Haiku) is fine for high-volume scoring; the reasoning here is simple.
Reads ANTHROPIC_API_KEY from the environment.
"""

import json
import os
import time
import openai
client = OpenAI()

# Edit this to define who you actually sell to.
ICP = """
We build GTM engineering systems (signal-based outbound, content engineering, GEO/AI-search)
for early-stage B2B SaaS and devtool/AI startups (seed to Series B) that have a real product
but weak, manual, or non-existent go-to-market.
Best fit: technical founders, devtools, AI-native products, developer-facing companies.
Poor fit: consumer apps, generic agencies, big enterprises with mature RevOps, non-software.
"""

SCORE_MODEL = "gpt-4o-mini"  # swap to gpt-4o if you want sharper judgment


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def call_openai_with_retry(client, model, messages, response_format=None, max_tokens=None):
    max_retries = 5
    delay = 10
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                response_format=response_format,
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


def score_signal(signal) -> dict:
    prompt = f"""You are a GTM analyst. Score how well this signal fits our ICP.

ICP:
{ICP}

Signal:
- Trigger: {signal.trigger}
- Company: {signal.company}
- Context: {signal.context}
- URL: {signal.url}

Return ONLY JSON, with the following format:
{{"score": <int 0-100>, "tier": "<hot|warm|cold>", "reason": "<one sentence>", "angle": "<a specific outbound angle grounded in THIS signal, not generic>"}}"""
    try:
        response = call_openai_with_retry(
            client=client,
            model=SCORE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=400,
        )
        text = response.choices[0].message.content
        return _parse_json(text)
    except Exception as e:
        print(f"Failed to score signal for {signal.company}: {e}")
        return {"score": 0, "tier": "cold", "reason": "parse_or_api_failed", "angle": ""}

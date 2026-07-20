# Signal → Outbound Agent — Build Guide

*Your first flagship GTM-engineering build. It plays to exactly what you already know (Python, agents, MCP, Claude, orchestration), it demos well, and pointed at the right ICP it finds your own first freelance clients while you build it.*

---

## What you're building

The core loop every serious GTM engine runs — the same **sense → simulate → act → sense** loop Scale Intelligence sells:

```
  SIGNAL            SCORE             ENRICH            DRAFT            REVIEW           SEND + LOG
  a buying   ->   fit vs ICP   ->   find the     ->  personalized  ->  human gate  ->  outbound +
  trigger         (0-100)          real contact      message           (approve)       log outcome
   |                                                                                        |
   +--------------------------  outcome becomes new signal  <--------------------------------+
```

You'll build it in three versions. Ship v0 this weekend; it's already useful.

- **v0 — linear pipeline** (runnable now, in this folder): signal → score → draft → human review queue. No sending. Proves the whole chain with free APIs + Claude.
- **v1 — MCP agent**: expose each step as an MCP tool and let a Claude agent orchestrate. *This is your differentiator* — most Clay operators can't build this.
- **v2 — closed loop**: log sends and replies, feed outcomes back as signal, learn which angles convert.

---

## v0 — run it this weekend

Files in this folder:

| File | Job |
|---|---|
| `signals.py` | Pull signals from free HN APIs (Show HN launches + GTM/RevOps hiring). No key needed. |
| `score.py` | OpenAI (gpt-4o-mini) scores each signal 0–100 against your ICP → JSON. |
| `draft.py` | OpenAI (gpt-4o) writes a personalized draft grounded in the signal. |
| `run.py` | Orchestrates the chain, writes `review_queue.csv`. **Sends nothing.** |

```bash
cd gtm-signal-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python run.py          # -> review_queue.csv, highest-fit first
```

Open `review_queue.csv`, read the drafts, and notice what the scoring gets right and wrong. **Edit the `ICP` string in `score.py` and the `VOICE` in `draft.py`** — tuning those two is 80% of output quality, and doing that tuning *is* the GTM-engineering skill.

**Why these signal sources**: a Show HN launch is a company that just shipped and needs distribution — Scale Intelligence's exact ICP. A "who is hiring a GTM/RevOps person" post is pain *plus* budget. Both are free to pull and genuinely high-intent. Later, swap in job boards (Adzuna has a free API), LinkedIn post monitoring (via Apify/PhantomBuster), GitHub star velocity (`api.github.com`), or Reddit (PRAW).

### The one rule: the human gate is not optional

v0 stops at a review queue on purpose. Auto-sending scraped cold outreach is how you burn a sending domain, annoy your ICP, and cross compliance lines. The gate is a feature: it keeps quality high and keeps you on the right side of CAN-SPAM / GDPR (B2B, relevant, clearly identified, easy opt-out; don't hoard personal data). A GTM engineer who ships deliverable, welcome outbound beats one who ships volume.

---

## The enrichment step (the missing piece between draft and send)

v0 drafts a message but doesn't have a real email yet. That's the **enrichment** slot — and it's where you connect this build to Clay (the tool you need to learn anyway). Two clean options:

- **Clay as an enrichment service**: `POST` the company/person to a Clay table via webhook; Clay runs its waterfall (Apollo → Clearbit → etc.), finds the verified email, and posts the result back to your endpoint. You get Clay's data quality without leaving your agent. This is the "learn Clay" and "build the agent" tracks meeting in one build.
- **Direct API**: call Apollo / a finder API yourself for a verified email. Cheaper to reason about, more plumbing to own.

Slot it in as `enrich_contact(company_or_person) -> {email, name, title, verified}` right before the review queue.

---

## v1 — turn it into an MCP agent (your edge)

Instead of a fixed script, expose each capability as an **MCP tool** and let a Claude agent decide what to do. You've built MCP servers before — this is the same muscle pointed at revenue.

Expose these tools from an MCP server (Python MCP SDK):

```python
fetch_signals(sources: list, since_hours: int) -> list[Signal]
score_icp(signal: Signal)                       -> {score, tier, reason, angle}
enrich_contact(company: str)                     -> {email, name, title, verified}
draft_message(signal, score)                     -> str
queue_for_review(record)                         -> ok        # human gate stays
log_outcome(record, result)                      -> ok        # for v2
```

### Running the MCP Server
Run the server locally with:
```bash
export OPENAI_API_KEY=sk-...
python mcp_server.py
```

### Testing the Tools
We provided a verification script to run all tools end-to-end:
```bash
export OPENAI_API_KEY=sk-...
python test_mcp_tools.py
```

Then the agent loop becomes a prompt, not a hardcoded pipeline:

> *"Pull the last 24h of signals. Score each against our ICP. For anything warm or hot, enrich the contact and draft outreach in our voice. Queue everything scoring 60+ for my review. Summarize what you found and which angle you'd lead with."*

Claude orchestrates: calls `fetch_signals`, loops `score_icp`, decides which clear the bar, calls `enrich_contact` and `draft_message`, and `queue_for_review`. You get an agent that reasons about *which* signals are worth pursuing, not just a filter — and you can run it from Claude Desktop or any MCP client.

**Why this is your moat**: a Clay-only operator builds tables. You build the connector Clay doesn't have, self-host the pipeline, and wrap it as tools an agent can drive. That "data engineer + agents + MCP" shape is exactly Scale Intelligence's forward-deployed engineer — and it's rare.

**Orchestration**: for scheduling, you already know **Airflow** — a daily DAG (`fetch → score → enrich → draft → queue`) is a new fit and a familiar-tech win. If you want a visual/low-code version to show non-technical clients, rebuild the same flow in **n8n** (self-hosted). Doing it in both is itself a great teardown post.

---

## v2 — close the loop

This is what makes it a *learning* engine rather than a scheduled script, and it's the part Scale Intelligence markets hardest.

1. **Log every send** and its outcome (reply / positive / meeting / ignored) via `log_outcome`.
2. **Feed outcomes back as signal**: a reply is a new, hotter signal; a bounce is a data-quality signal; silence after N touches routes to a different sequence.
3. **Weekly learning pass**: have the agent read the outcome log and answer "which angles, sources, and ICP slices actually convert?" Then adjust the `ICP` and `VOICE`, and the source mix. The system sharpens with every cycle — sense → act → sense.

---

## How each version doubles as proof-of-work

Every step here is also a build-in-public post and a portfolio entry — do both jobs at once:

- v0 shipped → *"I built a signal-to-outbound pipeline in a weekend. Here's the architecture."* (screenshot the review queue)
- The MCP version → *"Why I wrapped my GTM pipeline as MCP tools instead of hardcoding it."* (this one will travel with the engineering crowd)
- v2 loop → *"Making outbound learn: feeding outcomes back as signal."*
- A teardown → point the agent at a real company's public footprint and show what a GTM engine *would* catch.

That's four posts, one portfolio project, and a working demo you can screen-share on a call with Scale Intelligence or a prospect — from a single build.

---

## Build order checklist

- [ ] Run v0, read `review_queue.csv`
- [ ] Tune `ICP` (score.py) and `VOICE` (draft.py) until drafts feel sendable
- [ ] Add a 2nd/3rd signal source (job board, GitHub star velocity, Reddit)
- [ ] Wire enrichment via a Clay webhook (learn Clay + finish the chain)
- [ ] Re-architect as an MCP server; drive it with a Claude agent
- [ ] Schedule it (Airflow DAG) and/or mirror it in n8n
- [ ] Add outcome logging + a weekly learning pass
- [ ] Post the build-in-public thread; add it to your portfolio

---

## Model choices (as of mid-2026)

- **Scoring** (high volume, simple judgment): `gpt-4o-mini` — cheap and fast, with native JSON mode.
- **Drafting** (quality matters): `gpt-4o`.
- Move scoring up to `gpt-4o` if your ICP judgments are subtle. Keep everything in one provider first; add fallbacks later.

*Ship v0, tune the two strings, then make it an agent. The moment it's MCP-driven and closing the loop, you've built the thing most people in this field are still hand-waving about — and you did it in the exact style Scale Intelligence hires for.*

# GTM Signal → Outbound Agent

A GTM (Go-To-Market) engineering pipeline for [Scale Intelligence](https://scaleintelligence.dev) that monitors real buying signals, scores them against an Ideal Customer Profile (ICP), drafts personalized outreach, and queues them for human review. Includes a **Model Context Protocol (MCP) server** so any MCP-compatible AI client (Claude Desktop, Cursor, etc.) can orchestrate the entire pipeline as an agent.

---

## What It Does

```
SIGNAL → SCORE → ENRICH → DRAFT → REVIEW QUEUE → (SEND + LOG)
```

1. **Fetches signals** from Hacker News — no API key needed.
2. **Scores each signal** 0–100 against the ICP using OpenAI GPT-4o-mini with native JSON mode.
3. **Enriches contacts** (simulated waterfall — plug in Clay/Apollo for production).
4. **Drafts personalized outreach** using OpenAI GPT-4o in a defined voice.
5. **Queues the best leads** to `review_queue.csv` for human review.
6. **Logs outcomes** to `outcome_log.csv` for closed-loop learning.

**Nothing is ever sent automatically.** A human gates every outbound message.

---

## Signal Sources: Hacker News

The pipeline pulls two live feeds from the [HN Algolia API](https://hn.algolia.com/api) (no API key required):

| Source | What it monitors | Why it's a buying signal |
|---|---|---|
| **Show HN** | New product launches posted by founders | A founder who just launched has a product but no GTM — that's the exact pain Scale Intelligence solves. |
| **Who's Hiring (GTM/RevOps)** | HN monthly job thread comments mentioning GTM, RevOps, growth engineering | A company actively hiring for GTM roles has budget and acknowledged pain — high intent. |

Signals are fetched as a rolling window (default: last 24h for Show HN, last 72h for hiring). The ICP filter then eliminates noise — consumer apps, agencies, non-software companies are scored cold and dropped.

---

## Live Demo Run (Scale Intelligence)

Here's a real pipeline run from July 20, 2026. Five signals were fetched; three cleared the 60-point ICP threshold:

### Fetched 5 signals → 3 cleared threshold

```
[1/5] Crate             → score: 20 (cold)  — consumer mobile app, filtered out
[2/5] Wordpeek          → score: 60 (warm)  — developer traction, needs enrichment
[3/5] Codeground        → score: 85 (hot)   → drafted ✅
[4/5] Logic Puzzles PWA → score: 10 (cold)  — consumer game, filtered out
[5/5] Whetuu            → score: 75 (warm)  → drafted ✅
```

### Lead 1 — Codeground · Score: 85 / 🔴 HOT

**Signal:** Show HN launch — browser-based coding IDE  
**URL:** https://codeground.ai  
**Why it fits:** Developer-facing devtool, early stage, needs distribution after launch.

> Congrats on launching Codeground on Show HN. Your browser-based coding platform is a fantastic tool for developers. Our GTM engineering systems can optimize your outbound strategy, leveraging signals to engage more developers effectively and boost product adoption. Curious if enhancing outreach to target devs fits your growth plans?

---

### Lead 2 — Whetuu · Score: 75 / 🟡 WARM

**Signal:** Show HN launch — zero-config cross-shell prompt in Zig  
**URL:** https://github.com/yamafaktory/whetuu

> Noticed your launch of Whetuu on Show HN — impressive work with a zero-config cross-shell prompt in Zig. Our GTM engineering systems specialize in optimizing outreach to developers actively seeking tools like yours. Curious if you're exploring strategies to expand Whetuu's reach?

---

### Lead 3 — Wordpeek · Score: 60 / 🟡 WARM

**Signal:** Show HN launch — NLP/word tool  
**URL:** https://wordpeek.app

> Noticed Wordpeek's launch on Show HN — impressive work! Our team specializes in GTM systems for devtool startups. We can help refine Wordpeek's developer engagement and boost user acquisition by aligning your product's unique value with precise audience signals.

---

All three drafts land in `review_queue.csv`, sorted by score. A human reviews, enriches with a real email address, edits the copy, and sends.

---

## Project Structure

```
gtm-first-build/
├── gtm_agent/          # Core library (source package)
│   ├── __init__.py
│   ├── signals.py      # HN signal fetching (no API key)
│   ├── score.py        # ICP scoring via GPT-4o-mini
│   └── draft.py        # Outreach drafting via GPT-4o
├── tests/              # pytest suite (80 tests, fully mocked)
│   ├── conftest.py
│   ├── test_signals.py
│   ├── test_score.py
│   ├── test_draft.py
│   ├── test_mcp_server.py
│   └── test_run.py
├── run.py              # v0 entry point: linear pipeline
├── mcp_server.py       # v1 entry point: FastMCP server
├── test_mcp_tools.py   # Manual end-to-end test (requires API key)
├── review_queue.csv    # Output: leads queued for human review
├── outcome_log.csv     # Output: outreach outcome log
├── requirements.txt
└── BUILD-GUIDE.md      # Architecture deep-dive and roadmap
```

---

## Tools & Technologies

| Category | Tool |
|---|---|
| **Language** | Python 3.10+ |
| **AI / LLM** | [OpenAI API](https://platform.openai.com) — GPT-4o-mini (scoring), GPT-4o (drafting) |
| **Agent Protocol** | [Model Context Protocol (MCP)](https://modelcontextprotocol.io) via `mcp` Python SDK (FastMCP) |
| **Signal Sources** | [HN Algolia API](https://hn.algolia.com/api) — Show HN launches, GTM/RevOps hiring comments |
| **HTTP Client** | `requests` |
| **Testing** | `pytest`, `unittest.mock` (80 tests, no API key required) |
| **Version Control** | Git / GitHub |

---

## Prerequisites

- Python 3.10 or newer
- An [OpenAI API key](https://platform.openai.com/api-keys) with credits

---

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/souvikr/gtm-first-build.git
cd gtm-first-build
```

### 2. Create & Activate a Virtual Environment

```bash
# Create
python -m venv .venv

# Activate (macOS / Linux)
source .venv/bin/activate

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Your OpenAI API Key

```bash
# macOS / Linux
export OPENAI_API_KEY="sk-..."

# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."
```

> **Tip:** Store in a `.env` file (already in `.gitignore`) and load with `python-dotenv`.

---

## Running v0 — Linear Pipeline

```bash
python run.py
```

This will:
1. Fetch the last 24h of Show HN launches and 72h of GTM/RevOps hiring signals from HN.
2. Score each against the ICP (defined in `gtm_agent/score.py`).
3. Draft personalized outreach for signals scoring ≥ 60.
4. Write results to `review_queue.csv`, sorted by score descending.

Open `review_queue.csv`, review the drafts, find a real email address, edit, and send.

> **Key levers:** Edit the `ICP` string in [`gtm_agent/score.py`](gtm_agent/score.py) and the `VOICE` string in [`gtm_agent/draft.py`](gtm_agent/draft.py) — those two strings are 80% of output quality.

---

## Running v1 — MCP Server

The MCP server exposes all pipeline steps as tools that an AI agent (Claude, GPT, etc.) can call autonomously.

### Start the Server

```bash
python mcp_server.py
```

The server communicates over `stdio` (compatible with Claude Desktop, Cursor, and other local MCP clients). All logging goes to `stderr` so it never corrupts the JSON-RPC transport.

### Available Tools

| Tool | Description |
|---|---|
| `fetch_signals(sources, since_hours)` | Fetch intent signals from HN. Sources: `hn_show`, `hn_hiring`. |
| `score_icp(signal)` | Score a signal 0–100 against the ICP. Returns `{score, tier, reason, angle}`. |
| `enrich_contact(company)` | Find a decision-maker contact for a company. Returns `{email, name, title, verified}`. |
| `draft_message(signal, score)` | Generate a personalized cold outreach message. |
| `queue_for_review(record)` | Append a full lead record to `review_queue.csv`. |
| `log_outcome(record, result)` | Log an outreach outcome to `outcome_log.csv`. |

### Example Agent Prompt

> *"Pull the last 24h of signals from Show HN and the GTM hiring thread. Score each against our ICP. For anything warm or hot, enrich the contact and draft outreach in our voice. Queue everything scoring 60+ for my review. Summarize what you found."*

### Connect to Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gtm-agent": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/gtm-first-build/mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

---

## Running Tests

All 80 tests run fully offline — no API key or network required:

```bash
pytest tests/ -v
```

### Manual End-to-End Test (Requires API Key)

```bash
python test_mcp_tools.py
```

This exercises all 6 MCP tools against the live OpenAI API and writes sample rows to `review_queue.csv` and `outcome_log.csv`.

---

## Customization

### Change Your ICP
Edit the `ICP` string in [`gtm_agent/score.py`](gtm_agent/score.py). This controls which companies score high or low.

### Change Your Voice
Edit the `VOICE` string in [`gtm_agent/draft.py`](gtm_agent/draft.py). This controls tone and style of outreach drafts.

### Add More Signal Sources
Add new fetch functions to [`gtm_agent/signals.py`](gtm_agent/signals.py) following the `Signal` dataclass pattern. Ideas:
- Job board APIs (Adzuna, Greenhouse)
- GitHub star velocity (`api.github.com`)
- Reddit posts (PRAW)
- LinkedIn post monitoring (Apify / PhantomBuster)

---

## Roadmap

| Version | Status | Description |
|---|---|---|
| **v0** | ✅ Done | Linear pipeline: signal → score → draft → human review queue |
| **v1** | ✅ Done | MCP server: expose each step as an AI-callable tool |
| **v2** | 🔜 Planned | Closed loop: log outcomes, feed back as signal, weekly learning pass |

---

## Contributing

1. Fork the repo and create a feature branch.
2. Run `pytest tests/ -v` — all 80 tests must pass.
3. Never commit API keys — use environment variables.

---

## License

MIT

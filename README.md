# GTM Signal → Outbound Agent

A GTM (Go-To-Market) engineering pipeline that monitors buying signals, scores them against your Ideal Customer Profile (ICP), drafts personalized outreach, and queues them for human review. Includes a **Model Context Protocol (MCP) server** so any MCP-compatible client (Claude Desktop, Cursor, etc.) can orchestrate the entire pipeline as an agent.

---

## What It Does

```
SIGNAL → SCORE → ENRICH → DRAFT → REVIEW QUEUE → (SEND + LOG)
```

1. **Fetches signals** from free sources (Hacker News Show HN launches, GTM/RevOps hiring posts).
2. **Scores each signal** 0–100 against your ICP using OpenAI GPT-4o-mini with native JSON mode.
3. **Enriches contacts** (simulated waterfall — plug in Clay/Apollo for production).
4. **Drafts personalized outreach** using OpenAI GPT-4o in your defined voice.
5. **Queues the best leads** to `review_queue.csv` for human review.
6. **Logs outcomes** to `outcome_log.csv` for closed-loop learning.

**Nothing is ever sent automatically.** A human gates every outbound message.

---

## Project Structure

| File | Purpose |
|---|---|
| `signals.py` | Fetches buying intent signals from free APIs (no key required). |
| `score.py` | Scores each signal 0–100 against your ICP using OpenAI GPT-4o-mini (JSON mode). |
| `draft.py` | Writes a personalized cold outreach copy using OpenAI GPT-4o. |
| `run.py` | v0 linear pipeline: fetch → score → draft → write to `review_queue.csv`. |
| `mcp_server.py` | v1 FastMCP server exposing all pipeline steps as AI-callable tools. |
| `test_mcp_tools.py` | Manual end-to-end test exercising all 6 MCP server tools. |
| `tests/` | pytest test suite covering all modules and MCP tools. |
| `requirements.txt` | Python dependencies. |
| `BUILD-GUIDE.md` | Architecture deep-dive, design decisions, and v0→v2 roadmap. |

---

## Tools & Technologies

| Category | Tool |
|---|---|
| **Language** | Python 3.10+ |
| **AI / LLM** | [OpenAI API](https://platform.openai.com) (GPT-4o-mini for scoring, GPT-4o for drafting) |
| **Agent Protocol** | [Model Context Protocol (MCP)](https://modelcontextprotocol.io) via `mcp` Python SDK (FastMCP) |
| **Signal Sources** | [HN Algolia API](https://hn.algolia.com/api) — Show HN launches, GTM/RevOps hiring posts |
| **HTTP Client** | `requests` |
| **Testing** | `pytest`, `unittest.mock` |
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

# Activate (macOS/Linux)
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
$env:OPENAI_API_KEY="sk-..."
```

> **Tip:** Store it in a `.env` file (already `.gitignore`d) and load it with `python-dotenv`.

---

## Running v0 — Linear Pipeline

```bash
python run.py
```

This will:
1. Fetch the last 24 hours of Show HN launches and GTM/RevOps hiring signals.
2. Score each against your ICP.
3. Draft personalized outreach for signals scoring ≥ 60.
4. Write results to `review_queue.csv`.

Open `review_queue.csv`, read the drafts, approve the good ones, enrich for a real email, and then send.

> **Key levers:** Edit the `ICP` string in `score.py` and the `VOICE` string in `draft.py` — those two strings are 80% of output quality.

---

## Running v1 — MCP Server

The MCP server exposes all pipeline steps as tools that an AI agent (Claude, GPT, etc.) can call autonomously.

### Start the Server

```bash
python mcp_server.py
```

The server communicates over `stdio` (suitable for Claude Desktop, Cursor, and other local MCP clients).

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

> *"Pull the last 24h of signals. Score each against our ICP. For anything warm or hot, enrich the contact and draft outreach in our voice. Queue everything scoring 60+ for my review. Summarize what you found."*

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

```bash
pytest tests/ -v
```

The test suite uses mocks to avoid hitting real APIs (no key required to run tests):

```bash
pytest tests/ -v --tb=short
```

### Manual End-to-End Test (Requires API Key)

```bash
python test_mcp_tools.py
```

This exercises all 6 MCP tools against the live OpenAI API.

---

## Customization

### Change Your ICP
Edit the `ICP` string in [`score.py`](score.py). This controls which companies score high or low.

### Change Your Voice
Edit the `VOICE` string in [`draft.py`](draft.py). This controls the tone and style of outreach drafts.

### Add More Signal Sources
Add new fetch functions to [`signals.py`](signals.py) following the `Signal` dataclass pattern. Ideas:
- Job board APIs (Adzuna)
- GitHub star velocity (`api.github.com`)
- Reddit posts (PRAW)
- LinkedIn post monitoring (Apify/PhantomBuster)

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
2. Run `pytest tests/ -v` before submitting a PR.
3. Don't commit API keys — use environment variables.

---

## License

MIT

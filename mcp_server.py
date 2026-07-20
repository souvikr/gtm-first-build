import sys
import logging
import csv
import os
import re
from datetime import datetime
from dataclasses import asdict
from mcp.server.fastmcp import FastMCP
from gtm_agent.signals import Signal, fetch_show_hn, fetch_hiring_gtm
from gtm_agent.score import score_signal
from gtm_agent.draft import draft_message as dm

# Configure logging to stderr so it doesn't interfere with the stdio transport
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("gtm_mcp_server")

# Initialize FastMCP Server
mcp = FastMCP("GTM Outbound Agent Server")


@mcp.tool()
def fetch_signals(sources: list[str], since_hours: int = 24) -> list[dict]:
    """
    Fetch raw buying signals from free sources (e.g. ['hn_show', 'hn_hiring']).
    
    Args:
        sources: List of sources to fetch from. Supported: 'hn_show', 'hn_hiring'.
        since_hours: How far back (in hours) to fetch signals. Default is 24.
    """
    logger.info(f"fetch_signals called with sources={sources}, since_hours={since_hours}")
    results = []
    if "hn_show" in sources:
        logger.info("Fetching Show HN signals...")
        results.extend(fetch_show_hn(hours=since_hours))
    if "hn_hiring" in sources:
        logger.info("Fetching HN hiring signals...")
        results.extend(fetch_hiring_gtm(hours=since_hours))
        
    logger.info(f"Fetched {len(results)} total raw signals")
    return [asdict(sig) for sig in results]


@mcp.tool()
def score_icp(signal: dict) -> dict:
    """
    Score a raw signal against our ICP (Ideal Customer Profile) using OpenAI.
    
    Args:
        signal: A signal dictionary containing 'source', 'trigger', 'company', 'context', and 'url'.
    """
    logger.info(f"score_icp called for company: {signal.get('company')}")
    sig = Signal(
        source=signal.get("source", ""),
        trigger=signal.get("trigger", ""),
        company=signal.get("company", ""),
        context=signal.get("context", ""),
        url=signal.get("url", ""),
        found_at=signal.get("found_at", datetime.utcnow().isoformat())
    )
    score_result = score_signal(sig)
    logger.info(f"Scoring result for {sig.company}: {score_result}")
    return score_result


@mcp.tool()
def enrich_contact(company: str) -> dict:
    """
    Enrich a company to find a verified decision-maker contact (e.g. Founder/CEO).
    
    Args:
        company: The name of the company to enrich.
    """
    logger.info(f"enrich_contact called for company: {company}")
    # Simulated enrichment waterfall (mocking Clay or Apollo pipeline)
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', company).lower()
    email = f"founder@{clean_name}.com" if clean_name else "founder@unknowncompany.com"
    
    contact = {
        "email": email,
        "name": f"Founder of {company}",
        "title": "Founder & CEO",
        "verified": True
    }
    logger.info(f"Enrichment result for {company}: {contact}")
    return contact


@mcp.tool()
def draft_message(signal: dict, score: dict) -> str:
    """
    Draft a personalized cold outreach message based on a signal and its fit score.
    
    Args:
        signal: A signal dictionary containing 'trigger', 'context', 'url', etc.
        score: The score dict returned by score_icp, containing 'angle', 'score', etc.
    """
    logger.info(f"draft_message called for company: {signal.get('company')}")
    sig = Signal(
        source=signal.get("source", ""),
        trigger=signal.get("trigger", ""),
        company=signal.get("company", ""),
        context=signal.get("context", ""),
        url=signal.get("url", ""),
        found_at=signal.get("found_at", datetime.utcnow().isoformat())
    )
    draft_content = dm(sig, score)
    logger.info(f"Generated draft for {sig.company}")
    return draft_content


@mcp.tool()
def queue_for_review(record: dict) -> str:
    """
    Push a completed lead record (scored, enriched, and drafted) to the human review queue.
    
    Args:
        record: A full lead record dictionary including all fields from signal, score, contact, and draft.
    """
    logger.info(f"queue_for_review called for company: {record.get('company')}")
    file_exists = os.path.exists("review_queue.csv")
    
    fieldnames = [
        "source", "trigger", "company", "context", "url", "found_at",
        "score", "tier", "reason", "angle", "email", "name", "title",
        "verified", "draft", "status"
    ]
    
    # Extract only valid fieldnames
    row = {k: record.get(k, "") for k in fieldnames}
    row["status"] = "NEEDS_REVIEW"
    
    try:
        with open("review_queue.csv", "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                w.writeheader()
            w.writerow(row)
        logger.info(f"Successfully queued {record.get('company')} in review_queue.csv")
        return "ok"
    except Exception as e:
        logger.error(f"Failed to write to review_queue.csv: {e}")
        return f"error: {str(e)}"


@mcp.tool()
def log_outcome(record: dict, result: str) -> str:
    """
    Log send outcomes (e.g. replies, meetings, bounces, ignores) for closed-loop learning.
    
    Args:
        record: The lead record containing company details, email, and draft copy.
        result: The outreach outcome (e.g. 'replied', 'meeting_booked', 'bounced', 'ignored').
    """
    logger.info(f"log_outcome called for company: {record.get('company')} with result: {result}")
    file_exists = os.path.exists("outcome_log.csv")
    
    fieldnames = [
        "timestamp", "company", "email", "draft", "result"
    ]
    
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "company": record.get("company", ""),
        "email": record.get("email", ""),
        "draft": record.get("draft", ""),
        "result": result
    }
    
    try:
        with open("outcome_log.csv", "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                w.writeheader()
            w.writerow(row)
        logger.info(f"Successfully logged outcome for {record.get('company')}")
        return "ok"
    except Exception as e:
        logger.error(f"Failed to write to outcome_log.csv: {e}")
        return f"error: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")

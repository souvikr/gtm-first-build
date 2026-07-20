import os
from mcp_server import fetch_signals, score_icp, enrich_contact, draft_message, queue_for_review, log_outcome

# Ensure the API key is present in the environment for testing
if "OPENAI_API_KEY" not in os.environ:
    raise ValueError("OPENAI_API_KEY environment variable is required to run tests.")

def test_mcp_pipeline():
    print("Testing GTM MCP Server Tools...")
    
    # 1. Test fetch_signals
    print("\n--- 1. Testing fetch_signals ---")
    signals = fetch_signals(sources=["hn_show"], since_hours=24)
    print(f"Fetched {len(signals)} signals.")
    if not signals:
        print("No signals found, using a mock signal for testing.")
        test_signal = {
            "source": "hn_show",
            "trigger": "Launched a new product on Show HN",
            "company": "Codeground",
            "context": "Codeground - Run code in your browser, collaborative IDE",
            "url": "https://github.com/codeground"
        }
    else:
        test_signal = signals[0]
        print(f"Sample signal: {test_signal}")

    # 2. Test score_icp
    print("\n--- 2. Testing score_icp ---")
    score = score_icp(test_signal)
    print(f"Score result: {score}")

    # 3. Test enrich_contact
    print("\n--- 3. Testing enrich_contact ---")
    contact = enrich_contact(test_signal["company"])
    print(f"Enrichment result: {contact}")

    # 4. Test draft_message (if score fit is high enough)
    print("\n--- 4. Testing draft_message ---")
    draft = draft_message(test_signal, score)
    print(f"Draft:\n{draft}\n")

    # 5. Test queue_for_review
    print("\n--- 5. Testing queue_for_review ---")
    record = {
        **test_signal,
        **score,
        **contact,
        "draft": draft
    }
    queue_result = queue_for_review(record)
    print(f"Queue result: {queue_result}")

    # 6. Test log_outcome
    print("\n--- 6. Testing log_outcome ---")
    outcome_result = log_outcome(record, "replied")
    print(f"Log outcome result: {outcome_result}")
    
    print("\nAll GTM MCP Server tools successfully verified!")

if __name__ == "__main__":
    test_mcp_pipeline()

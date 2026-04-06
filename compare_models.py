import json
from datetime import datetime
import time

from baseline.baseline_chatbot import chatbot_baseline

# TODO: import agent thật
def react_agent(question: str) -> str:
    return "[AGENT OUTPUT HERE]"

from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


def load_test_cases():
    with open("test_cases.json", "r", encoding="utf-8") as f:
        return json.load(f)

def run_comparison():
    test_cases = load_test_cases()
    results = []

    logger.info("=== START COMPARISON RUN ===")

    for case in test_cases:
        q = case["question"]

        print(f"\n--- Test case {case['id']} ---")
        print(f"Q: {q}")

        logger.log_event("TEST_CASE_START", {
            "id": case["id"],
            "question": q
        })

        # =========================
        # BASELINE
        # =========================
        start_time = time.time()
        baseline = chatbot_baseline(q)
        latency_baseline = int((time.time() - start_time) * 1000)

        logger.log_event("BASELINE_RESPONSE", {
            "question": q,
            "response": baseline[:200],
            "latency_ms": latency_baseline
        })

        # fake usage (vì baseline có thể không trả usage)
        tracker.track_request(
            provider="baseline",
            model="claude",
            usage={"total_tokens": len(baseline.split())},
            latency_ms=latency_baseline
        )

        # =========================
        # AGENT
        # =========================
        start_time = time.time()
        agent = react_agent(q)
        latency_agent = int((time.time() - start_time) * 1000)

        logger.log_event("AGENT_RESPONSE", {
            "question": q,
            "response": agent[:200],
            "latency_ms": latency_agent
        })

        tracker.track_request(
            provider="react_agent",
            model="custom-agent",
            usage={"total_tokens": len(agent.split())},
            latency_ms=latency_agent
        )

        print(f"\nBaseline:\n{baseline}")
        print(f"\nAgent:\n{agent}")

        results.append({
            "id": case["id"],
            "question": q,
            "baseline": baseline,
            "agent": agent,
            "latency_baseline_ms": latency_baseline,
            "latency_agent_ms": latency_agent
        })

    filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved results to {filename}")
    logger.info("=== END COMPARISON RUN ===")


if __name__ == "__main__":
    run_comparison()
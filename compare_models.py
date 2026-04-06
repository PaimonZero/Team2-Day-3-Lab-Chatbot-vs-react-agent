import json
import time
from datetime import datetime

from baseline.baseline_chatbot import chatbot_baseline
from agent_v1.agent import run_agent as run_agent_v1
from agent_v2.agent import run_agent as run_agent_v2

from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


def load_test_cases():
    with open("baseline/test_cases.json", "r", encoding="utf-8") as f:
        return json.load(f)


def run_comparison():
    test_cases = load_test_cases()
    results = []

    logger.info("=== START COMPARISON (Baseline vs V1 vs V2) ===")

    for case in test_cases:
        q = case["question"]

        print(f"\n{'='*60}")
        print(f"Test case {case['id']}: {q}")
        print(f"{'='*60}")

        logger.log_event("TEST_CASE_START", {
            "id": case["id"],
            "question": q
        })

        # =========================
        # BASELINE
        # =========================
        start = time.time()
        baseline = chatbot_baseline(q)
        latency_baseline = int((time.time() - start) * 1000)

        logger.log_event("BASELINE_RESPONSE", {
            "response": baseline[:200],
            "latency_ms": latency_baseline
        })

        tracker.track_request(
            provider="baseline",
            model="claude",
            usage={"total_tokens": len(baseline.split())},
            latency_ms=latency_baseline
        )

        # =========================
        # AGENT V1
        # =========================
        start = time.time()
        v1 = run_agent_v1(q)
        latency_v1 = int((time.time() - start) * 1000)

        logger.log_event("AGENT_V1_RESPONSE", {
            "response": v1[:200],
            "latency_ms": latency_v1
        })

        tracker.track_request(
            provider="agent_v1",
            model="react-v1",
            usage={"total_tokens": len(v1.split())},
            latency_ms=latency_v1
        )

        # =========================
        # AGENT V2
        # =========================
        start = time.time()
        v2 = run_agent_v2(q)
        latency_v2 = int((time.time() - start) * 1000)

        logger.log_event("AGENT_V2_RESPONSE", {
            "response": v2[:200],
            "latency_ms": latency_v2
        })

        tracker.track_request(
            provider="agent_v2",
            model="react-v2",
            usage={"total_tokens": len(v2.split())},
            latency_ms=latency_v2
        )

        # =========================
        # PRINT OUTPUT
        # =========================
        print("\n--- Baseline ---")
        print(baseline)

        print("\n--- Agent V1 ---")
        print(v1)

        print("\n--- Agent V2 ---")
        print(v2)

        # =========================
        # SAVE RESULT
        # =========================
        results.append({
            "id": case["id"],
            "question": q,

            "baseline": baseline,
            "agent_v1": v1,
            "agent_v2": v2,

            "latency_baseline_ms": latency_baseline,
            "latency_v1_ms": latency_v1,
            "latency_v2_ms": latency_v2
        })

    # save file
    filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved results to {filename}")

    # =========================
    # SUMMARY (rất nên có)
    # =========================
    avg_baseline = sum(r["latency_baseline_ms"] for r in results) / len(results)
    avg_v1 = sum(r["latency_v1_ms"] for r in results) / len(results)
    avg_v2 = sum(r["latency_v2_ms"] for r in results) / len(results)

    print("\n===== SUMMARY =====")
    print(f"Baseline latency avg: {avg_baseline:.2f} ms")
    print(f"Agent V1 latency avg: {avg_v1:.2f} ms")
    print(f"Agent V2 latency avg: {avg_v2:.2f} ms")

    logger.info("=== END COMPARISON ===")


if __name__ == "__main__":
    run_comparison()
"""
compare_models.py  ← upload lên GitHub tại ROOT (không phải trong baseline/)
─────────────────────────────────────────────────────────────
Script so sánh Chatbot Baseline vs Agent V1 vs Agent V2
Author  : Nguyễn Đức Hoàng Phúc
Project : Team 2 – Day 3 Lab: Chatbot vs ReAct Agent

Cách chạy (từ root folder):
    python compare_models.py

Output:
    - In kết quả từng test case ra terminal
    - Lưu kết quả vào results_YYYYMMDD_HHMMSS.json
─────────────────────────────────────────────────────────────
"""

import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from baseline.baseline_chatbot import chatbot_baseline
from agent_v1.agent import run_agent as run_agent_v1
from agent_v2.agent import run_agent as run_agent_v2

from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

TEST_CASES_PATH = "baseline/test_cases.json"


def load_test_cases() -> list:
    """Load test cases từ baseline/test_cases.json."""
    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_one(label: str, fn, question: str) -> tuple[str, int]:
    """
    Chạy một model và đo latency.

    Returns:
        (response_text, latency_ms)
    """
    start = time.time()
    try:
        result = fn(question)
    except Exception as e:
        result = f"[ERROR] {str(e)}"
    latency_ms = int((time.time() - start) * 1000)
    return result, latency_ms


def run_comparison():
    test_cases = load_test_cases()
    results    = []

    logger.log_event("COMPARISON_START", {
        "total_cases": len(test_cases),
        "models": ["baseline", "agent_v1", "agent_v2"],
    })

    for case in test_cases:
        q = case["question"]

        print(f"\n{'='*60}")
        print(f"Test #{case['id']}: {q}")
        print(f"{'='*60}")

        logger.log_event("TEST_CASE_START", {"id": case["id"], "question": q})

        # ── Baseline ────────────────────────────────────────
        baseline_ans, latency_baseline = run_one("Baseline", chatbot_baseline, q)

        logger.log_event("BASELINE_RESPONSE", {
            "id":         case["id"],
            "response":   baseline_ans[:200],
            "latency_ms": latency_baseline,
        })
        tracker.track_request(
            provider="baseline",
            model="claude-sonnet-4-5",
            usage={"total_tokens": len(baseline_ans.split())},
            latency_ms=latency_baseline,
        )

        # ── Agent V1 ─────────────────────────────────────────
        v1_ans, latency_v1 = run_one("Agent V1", run_agent_v1, q)

        logger.log_event("AGENT_V1_RESPONSE", {
            "id":         case["id"],
            "response":   v1_ans[:200],
            "latency_ms": latency_v1,
        })
        tracker.track_request(
            provider="agent_v1",
            model="react-v1",
            usage={"total_tokens": len(v1_ans.split())},
            latency_ms=latency_v1,
        )

        # ── Agent V2 ─────────────────────────────────────────
        v2_ans, latency_v2 = run_one("Agent V2", run_agent_v2, q)

        logger.log_event("AGENT_V2_RESPONSE", {
            "id":         case["id"],
            "response":   v2_ans[:200],
            "latency_ms": latency_v2,
        })
        tracker.track_request(
            provider="agent_v2",
            model="react-v2",
            usage={"total_tokens": len(v2_ans.split())},
            latency_ms=latency_v2,
        )

        # ── Print ─────────────────────────────────────────────
        print("\n[Baseline]")
        print(baseline_ans)
        print("\n[Agent V1]")
        print(v1_ans)
        print("\n[Agent V2]")
        print(v2_ans)

        results.append({
            "id":       case["id"],
            "question": q,

            "baseline":  baseline_ans,
            "agent_v1":  v1_ans,
            "agent_v2":  v2_ans,

            "latency_baseline_ms": latency_baseline,
            "latency_v1_ms":       latency_v1,
            "latency_v2_ms":       latency_v2,
        })

    # ── Save results ──────────────────────────────────────────
    filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved results → {filename}")

    # ── Summary ───────────────────────────────────────────────
    n = len(results)
    avg_baseline = sum(r["latency_baseline_ms"] for r in results) / n
    avg_v1       = sum(r["latency_v1_ms"]       for r in results) / n
    avg_v2       = sum(r["latency_v2_ms"]       for r in results) / n

    print(f"\n{'='*60}")
    print(f"  SUMMARY ({n} test cases)")
    print(f"{'='*60}")
    print(f"  Chatbot Baseline  avg latency: {avg_baseline:>8.0f} ms")
    print(f"  Agent V1          avg latency: {avg_v1:>8.0f} ms")
    print(f"  Agent V2          avg latency: {avg_v2:>8.0f} ms")
    print(f"{'='*60}")

    logger.log_event("COMPARISON_DONE", {
        "total_cases":     n,
        "avg_baseline_ms": round(avg_baseline),
        "avg_v1_ms":       round(avg_v1),
        "avg_v2_ms":       round(avg_v2),
        "results_file":    filename,
    })


if __name__ == "__main__":
    run_comparison()
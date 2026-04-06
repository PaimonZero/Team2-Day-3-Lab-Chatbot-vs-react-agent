import json
from datetime import datetime
from baseline.baseline_chatbot import chatbot_baseline

# TODO: import agent thật của nhóm bạn
def react_agent(question: str) -> str:
    return "[AGENT OUTPUT HERE]"


def load_test_cases():
    with open("test_cases.json", "r", encoding="utf-8") as f:
        return json.load(f)


def run_comparison():
    test_cases = load_test_cases()
    results = []

    for case in test_cases:
        q = case["question"]
        print(f"\n--- Test case {case['id']} ---")
        print(f"Q: {q}")

        baseline = chatbot_baseline(q)
        agent = react_agent(q)

        print(f"\nBaseline:\n{baseline}")
        print(f"\nAgent:\n{agent}")

        results.append({
            "id": case["id"],
            "question": q,
            "baseline": baseline,
            "agent": agent
        })

    filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to {filename}")


if __name__ == "__main__":
    run_comparison()
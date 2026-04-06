"""
AGENT V1 — ReAct Agent (Basic)
================================
NGƯỜI LÀM: Ta (nhóm trưởng)

Implement ReAct loop cơ bản:
  Thought → Action → Observation → ... → Final Answer

Đặc điểm V1 (intentional limitations để tạo failure traces):
- Prompt đơn giản, không có few-shot examples
- Parse Action bằng string.split() → dễ fail nếu LLM format sai
- Không có retry khi tool lỗi
- Không validate tool input trước khi gọi
- Không có fallback khi city không tồn tại

Cách chạy:
    python agent_v1/agent.py
"""

import os
import sys
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from src.core.anthropic_provider import AnthropicProvider
from src.telemetry.logger import logger
from agent_v1.tools.weather_tools import get_coordinates, get_weather
from agent_v1.tools.risk_tools import analyze_risk, escalate_to_human

load_dotenv()

# ─────────────────────────────────────────────
# SYSTEM PROMPT — V1: Đơn giản, không few-shot
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are a Smart Weather Planner agent. Your job is to help users plan travel based on real-time weather.

You have access to these tools:
- get_coordinates(city) → returns lat, lon of a city
- get_weather(lat, lon) → returns current temperature, wind speed, weather code
- analyze_risk(temperature_c, wind_speed_kmh, weather_code) → returns risk level and recommendation
- escalate_to_human(reason, city) → notifies a travel agent for extreme cases

Follow this ReAct format strictly — each step on its own line:
Thought: <your reasoning>
Action: <tool_name>(<arg1>, <arg2>, ...)
Observation: <result of the tool>
... (repeat Thought/Action/Observation as needed)
Final Answer: <your final travel recommendation>

Rules:
- Always call get_coordinates first to get lat/lon.
- Then call get_weather with those coordinates.
- Then call analyze_risk with the weather data.
- If risk is HIGH, call escalate_to_human.
- End with Final Answer.
"""

MAX_STEPS = 8  # V1: không có retry, chỉ giới hạn số bước


# ─────────────────────────────────────────────
# Tool Registry — map tên tool → function
# ─────────────────────────────────────────────
TOOL_REGISTRY = {
    "get_coordinates": get_coordinates,
    "get_weather": get_weather,
    "analyze_risk": analyze_risk,
    "escalate_to_human": escalate_to_human,
}


def parse_action(action_line: str):
    """
    Parse dòng Action thành (tool_name, args).

    V1: Dùng regex đơn giản — dễ fail nếu LLM không format đúng.
    Ví dụ: "get_coordinates(Hanoi)" → ("get_coordinates", ["Hanoi"])
            "get_weather(21.03, 105.85)" → ("get_weather", [21.03, 105.85])
    """
    match = re.match(r"(\w+)\((.*)?\)", action_line.strip())
    if not match:
        raise ValueError(f"Cannot parse action: '{action_line}'")

    tool_name = match.group(1)
    raw_args  = match.group(2).strip()

    if not raw_args:
        return tool_name, []

    # V1: Split bằng dấu phẩy, không handle quoted strings
    args = [a.strip().strip('"').strip("'") for a in raw_args.split(",")]

    # Cố convert sang số nếu có thể
    parsed_args = []
    for a in args:
        try:
            parsed_args.append(float(a) if "." in a else int(a))
        except ValueError:
            parsed_args.append(a)

    return tool_name, parsed_args


def run_tool(tool_name: str, args: list):
    """Gọi tool từ registry. V1: Không validate args trước khi gọi."""
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: '{tool_name}'"}

    tool_fn = TOOL_REGISTRY[tool_name]
    return tool_fn(*args)


def run_agent(user_query: str) -> str:
    """
    Chạy ReAct loop cho một câu hỏi của người dùng.

    Returns:
        Final answer string
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model   = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-5")
    llm     = AnthropicProvider(model_name=model, api_key=api_key)

    logger.start_trace(agent_version="v1", query=user_query)
    logger.log_event("AGENT_V1_START", {"query": user_query})
    print(f"\n{'='*60}")
    print(f"  ReAct Agent V1")
    print(f"  Query: {user_query}")
    print(f"{'='*60}")

    # Khởi tạo conversation
    conversation = f"User: {user_query}\n"
    step = 0

    while step < MAX_STEPS:
        step += 1
        print(f"\n--- Step {step} ---")

        # ── Gọi LLM ──
        response = llm.generate(conversation, system_prompt=SYSTEM_PROMPT)
        llm_output = response["content"].strip()

        logger.log_event("AGENT_V1_LLM_OUTPUT", {
            "step": step,
            "output_preview": llm_output[:300],
            "tokens": response["usage"],
            "latency_ms": response["latency_ms"],
        })

        print(llm_output)

        # ── Kiểm tra Final Answer ──
        if "Final Answer:" in llm_output:
            final_answer = llm_output.split("Final Answer:")[-1].strip()
            logger.log_event("AGENT_V1_DONE", {
                "steps": step,
                "final_answer_preview": final_answer[:200],
            })
            logger.save_trace(outcome="success")
            print(f"\n{'='*60}")
            print(f"  ✅ FINAL ANSWER")
            print(f"{'='*60}")
            print(final_answer)
            return final_answer

        # ── Parse Action ──
        action_line = None
        for line in llm_output.splitlines():
            if line.strip().startswith("Action:"):
                action_line = line.replace("Action:", "").strip()
                break

        if not action_line:
            logger.log_event("AGENT_V1_ERROR", {
                "step": step,
                "error": "No Action found in LLM output — V1 parse failure"
            })
            observation = "ERROR: Could not find Action in your response. Please follow the format."
        else:
            # ── Execute Tool ──
            try:
                tool_name, args = parse_action(action_line)
                logger.log_event("AGENT_V1_TOOL_CALL", {
                    "step": step,
                    "tool": tool_name,
                    "args": args,
                })
                result = run_tool(tool_name, args)
                observation = str(result)
                logger.log_event("AGENT_V1_TOOL_RESULT", {
                    "step": step,
                    "tool": tool_name,
                    "result_preview": observation[:200],
                })
            except Exception as e:
                observation = f"ERROR: {str(e)}"
                logger.log_event("AGENT_V1_TOOL_ERROR", {
                    "step": step,
                    "action_line": action_line,
                    "error": str(e),
                })

        # ── Append Observation vào conversation ──
        conversation += f"\n{llm_output}\nObservation: {observation}\n"

    # Vượt quá MAX_STEPS
    logger.log_event("AGENT_V1_MAX_STEPS", {"steps": step})
    logger.save_trace(outcome="failure")
    return f"Agent stopped after {MAX_STEPS} steps without a Final Answer."


if __name__ == "__main__":
    print("Smart Weather Planner — Agent V1 (ReAct Basic)")
    print("Type 'quit' to exit\n")

    while True:
        query = input("You: ").strip()
        if query.lower() in ["quit", "exit", "q"]:
            break
        if not query:
            continue
        run_agent(query)

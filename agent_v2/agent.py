"""
AGENT V2 — ReAct Agent (Improved)
====================================
NGƯỜI LÀM: Mai Tấn Thành - 2A202600127 (nhóm trưởng)

Cải tiến so với V1 — dựa trên failure traces đã ghi lại:

  V1 FAILURE                  →   V2 FIX
  ─────────────────────────────────────────────────────
  Prompt đơn giản, dễ sai format  →  Few-shot examples trong prompt
  Parse bằng regex, dễ crash      →  LLM trả JSON → parse an toàn
  Không retry khi lỗi             →  Retry tối đa 2 lần / bước
  Không validate input tools      →  Validate trước khi gọi tool
  Không fallback city sai         →  Xử lý gracefully khi city not found
  Không save trace                →  Tự động save trace success/failure

Cách chạy:
    python agent_v2/agent.py
"""

import os
import sys
import json
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from src.core.anthropic_provider import AnthropicProvider
from src.telemetry.logger import logger

# Import tools v2 (Thành viên A & B implement)
# Fallback sang v1 nếu v2 chưa có
try:
    from agent_v2.tools.weather_tools import get_coordinates, get_weather
    from agent_v2.tools.risk_tools import analyze_risk, escalate_to_human
except (ImportError, AttributeError):
    from agent_v1.tools.weather_tools import get_coordinates, get_weather
    from agent_v1.tools.risk_tools import analyze_risk, escalate_to_human

load_dotenv()

# ─────────────────────────────────────────────────────
# SYSTEM PROMPT — V2: Có few-shot + JSON Action format
# ─────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a Smart Weather Planner agent. Help users plan travel based on real-time weather.

## Available Tools

| Tool | Args | Returns |
|------|------|---------|
| get_coordinates | city (str) | lat, lon, name, country |
| get_weather | lat (float), lon (float) | temperature_c, wind_speed_kmh, weather_code, weather_desc |
| analyze_risk | temperature_c (float), wind_speed_kmh (float), weather_code (int) | risk_level, reasons, recommendation |
| escalate_to_human | reason (str), city (str) | status, message, ticket_id |

## Output Format (STRICT JSON for Action)

Each step must follow this EXACT format:

Thought: <your reasoning here>
Action: {"tool": "<tool_name>", "args": {"<arg_name>": <value>, ...}}

When you have enough information to answer:
Thought: I now have all the information needed.
Final Answer: <your complete travel recommendation>

## Workflow

1. get_coordinates(city) → get lat/lon
2. get_weather(lat, lon) → get current conditions
3. analyze_risk(temperature_c, wind_speed_kmh, weather_code) → assess safety
4. If risk_level is HIGH → escalate_to_human(reason, city)
5. Final Answer → summarize everything for the user

## Few-Shot Example

User: Should I visit Bangkok this weekend?

Thought: I need to get the coordinates of Bangkok first.
Action: {"tool": "get_coordinates", "args": {"city": "Bangkok"}}
Observation: {"lat": 13.75, "lon": 100.52, "name": "Bangkok", "country": "Thailand"}

Thought: I have the coordinates. Now I'll get the current weather.
Action: {"tool": "get_weather", "args": {"lat": 13.75, "lon": 100.52}}
Observation: {"temperature_c": 34, "wind_speed_kmh": 18, "weather_code": 80, "weather_desc": "Slight showers"}

Thought: Weather data retrieved. Now analyzing the travel risk.
Action: {"tool": "analyze_risk", "args": {"temperature_c": 34, "wind_speed_kmh": 18, "weather_code": 80}}
Observation: {"risk_level": "MEDIUM", "reasons": ["Very hot (34°C)"], "recommendation": "⚠️ Travel with caution."}

Thought: Risk is MEDIUM, no need to escalate. I can give a final answer.
Final Answer: Bangkok is experiencing hot weather (34°C) with light showers. The risk level is MEDIUM. I recommend packing light clothes and a rain jacket. Stay hydrated and avoid midday outdoor activities.
"""

MAX_STEPS   = 10   # V2: tăng từ 8 → 10
MAX_RETRIES = 2    # V2: thêm retry


# ─────────────────────────────────────────────
# Tool Registry
# ─────────────────────────────────────────────
TOOL_REGISTRY = {
    "get_coordinates": get_coordinates,
    "get_weather":     get_weather,
    "analyze_risk":    analyze_risk,
    "escalate_to_human": escalate_to_human,
}

# Schema validation đơn giản cho mỗi tool
TOOL_SCHEMA = {
    "get_coordinates":   {"required": ["city"],             "types": {"city": str}},
    "get_weather":       {"required": ["lat", "lon"],        "types": {"lat": float, "lon": float}},
    "analyze_risk":      {"required": ["temperature_c", "wind_speed_kmh", "weather_code"],
                          "types": {"temperature_c": (int, float), "wind_speed_kmh": (int, float), "weather_code": int}},
    "escalate_to_human": {"required": ["reason", "city"],   "types": {"reason": str, "city": str}},
}


# ─────────────────────────────────────────────
# Parse Action — V2: JSON format
# ─────────────────────────────────────────────
def parse_action(action_text: str) -> dict:
    """
    Parse Action từ JSON string.
    V2: Robust hơn V1 — thử nhiều cách extract JSON.

    Returns:
        dict với 'tool' và 'args'
    Raises:
        ValueError nếu không parse được
    """
    action_text = action_text.strip()

    # Thử parse trực tiếp
    try:
        return json.loads(action_text)
    except json.JSONDecodeError:
        pass

    # Thử extract JSON từ trong text (LLM đôi khi thêm text xung quanh)
    match = re.search(r'\{.*\}', action_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Cannot parse action as JSON: '{action_text[:100]}'")


# ─────────────────────────────────────────────
# Validate args — V2: kiểm tra trước khi gọi
# ─────────────────────────────────────────────
def validate_args(tool_name: str, args: dict) -> str | None:
    """
    Validate args trước khi gọi tool.
    Returns: error message nếu không hợp lệ, None nếu OK.
    """
    if tool_name not in TOOL_SCHEMA:
        return f"Unknown tool: '{tool_name}'"

    schema = TOOL_SCHEMA[tool_name]

    for field in schema["required"]:
        if field not in args:
            return f"Missing required arg '{field}' for tool '{tool_name}'"

    for field, expected_type in schema["types"].items():
        if field in args and not isinstance(args[field], expected_type):
            try:
                # Thử convert
                if expected_type in (float, (int, float)):
                    args[field] = float(args[field])
                elif expected_type is int:
                    args[field] = int(args[field])
            except (ValueError, TypeError):
                return f"Arg '{field}' should be {expected_type}, got {type(args[field])}"

    return None  # OK


# ─────────────────────────────────────────────
# Run Tool
# ─────────────────────────────────────────────
def run_tool(tool_name: str, args: dict):
    """Validate rồi gọi tool. V2: validate trước."""
    error = validate_args(tool_name, args)
    if error:
        return {"error": error}

    tool_fn = TOOL_REGISTRY[tool_name]
    return tool_fn(**args)


# ─────────────────────────────────────────────
# Main Agent Loop
# ─────────────────────────────────────────────
def run_agent(user_query: str) -> str:
    """
    Chạy ReAct loop V2 với retry và fallback.

    Returns:
        Final answer string
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model   = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-5")
    llm     = AnthropicProvider(model_name=model, api_key=api_key)

    logger.start_trace(agent_version="v2", query=user_query)
    logger.log_event("AGENT_V2_START", {"query": user_query})

    print(f"\n{'='*60}")
    print(f"  ReAct Agent V2 (Improved)")
    print(f"  Query: {user_query}")
    print(f"{'='*60}")

    conversation = f"User: {user_query}\n"
    step = 0

    while step < MAX_STEPS:
        step += 1
        print(f"\n--- Step {step} ---")

        # ── Gọi LLM (có retry) ──
        llm_output = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response  = llm.generate(conversation, system_prompt=SYSTEM_PROMPT)
                llm_output = response["content"].strip()
                logger.log_event("AGENT_V2_LLM_OUTPUT", {
                    "step": step,
                    "attempt": attempt + 1,
                    "output_preview": llm_output[:300],
                    "tokens": response["usage"],
                    "latency_ms": response["latency_ms"],
                })
                break
            except Exception as e:
                logger.log_event("AGENT_V2_LLM_ERROR", {
                    "step": step,
                    "attempt": attempt + 1,
                    "error": str(e),
                })
                if attempt == MAX_RETRIES:
                    logger.save_trace(outcome="failure")
                    return f"LLM failed after {MAX_RETRIES + 1} attempts: {e}"

        print(llm_output)

        # ── Kiểm tra Final Answer ──
        if "Final Answer:" in llm_output:
            final_answer = llm_output.split("Final Answer:")[-1].strip()
            logger.log_event("AGENT_V2_DONE", {
                "steps": step,
                "final_answer_preview": final_answer[:200],
            })
            logger.save_trace(outcome="success")
            print(f"\n{'='*60}")
            print(f"  ✅ FINAL ANSWER")
            print(f"{'='*60}")
            print(final_answer)
            return final_answer

        # ── Parse Action (có retry) ──
        action_line = None
        for line in llm_output.splitlines():
            if line.strip().startswith("Action:"):
                action_line = line.replace("Action:", "").strip()
                break

        if not action_line:
            logger.log_event("AGENT_V2_NO_ACTION", {"step": step})
            observation = "ERROR: No Action found. Please use the format: Action: {\"tool\": \"...\", \"args\": {...}}"
            conversation += f"\n{llm_output}\nObservation: {observation}\n"
            continue

        # ── Execute Tool (với retry + validation) ──
        observation = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                action = parse_action(action_line)
                tool_name = action.get("tool")
                args      = action.get("args", {})

                if not tool_name:
                    raise ValueError("Action JSON missing 'tool' key")

                logger.log_event("AGENT_V2_TOOL_CALL", {
                    "step": step,
                    "attempt": attempt + 1,
                    "tool": tool_name,
                    "args": args,
                })

                result = run_tool(tool_name, args)
                observation = json.dumps(result, ensure_ascii=False)

                logger.log_event("AGENT_V2_TOOL_RESULT", {
                    "step": step,
                    "tool": tool_name,
                    "result_preview": observation[:300],
                })

                # V2: Nếu tool trả về error, thông báo cho LLM biết
                if isinstance(result, dict) and "error" in result:
                    logger.log_event("AGENT_V2_TOOL_SOFT_ERROR", {
                        "step": step,
                        "tool": tool_name,
                        "error": result["error"],
                    })

                break  # Success

            except Exception as e:
                logger.log_event("AGENT_V2_TOOL_EXCEPTION", {
                    "step": step,
                    "attempt": attempt + 1,
                    "error": str(e),
                })
                if attempt == MAX_RETRIES:
                    observation = f"ERROR after {MAX_RETRIES + 1} attempts: {str(e)}"
                else:
                    observation = f"Attempt {attempt+1} failed: {str(e)}. Retrying..."

        # ── Append Observation ──
        conversation += f"\n{llm_output}\nObservation: {observation}\n"

    # Quá MAX_STEPS
    logger.log_event("AGENT_V2_MAX_STEPS", {"steps": step})
    logger.save_trace(outcome="failure")
    return f"Agent stopped after {MAX_STEPS} steps without a Final Answer."


if __name__ == "__main__":
    print("Smart Weather Planner — Agent V2 (Improved ReAct)")
    print("Type 'quit' to exit\n")

    while True:
        query = input("You: ").strip()
        if query.lower() in ["quit", "exit", "q"]:
            break
        if not query:
            continue
        run_agent(query)

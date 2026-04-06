"""
agent_v2/agent.py — ReAct Agent (Improved)
============================================
NGƯỜI LÀM: Mai Tấn Thành - 2A202600127 (nhóm trưởng)

Cải tiến so với V1 — dựa trên failure traces đã ghi lại:

  V1 FAILURE                       →   V2 FIX
  ────────────────────────────────────────────────────────────
  Prompt đơn giản, dễ sai format   →  Few-shot examples trong prompt
  Parse bằng regex, dễ crash        →  LLM trả JSON → parse an toàn
  Không retry khi lỗi              →  Retry tối đa 2 lần / bước
  Không validate input tools       →  Validate + coerce type trước khi gọi
  Không fallback city sai          →  Forward error JSON cho LLM tự sửa
  Không save trace                 →  Tự động save trace success/failure

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

# Import tools — fallback sang agent_v1 nếu chưa có
try:
    from agent_v2.tools.weather_tools import get_coordinates, get_weather
    from agent_v2.tools.risk_tools import analyze_risk, escalate_to_human
except (ImportError, AttributeError):
    from agent_v1.tools.weather_tools import get_coordinates, get_weather
    from agent_v1.tools.risk_tools import analyze_risk, escalate_to_human

load_dotenv()

# ──────────────────────────────────────────────────────────────
# SYSTEM PROMPT — Few-shot + JSON Action format
# ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a Smart Weather Planner agent. Help users plan travel based on real-time weather.

## Available Tools

| Tool              | Args                                                          | Returns                                                      |
|-------------------|---------------------------------------------------------------|--------------------------------------------------------------|
| get_coordinates   | city_name (str)                                               | status, city, country, latitude, longitude                   |
| get_weather       | latitude (float), longitude (float)                          | status, weather_description, weather_code, temperature_c,    |
|                   |                                                               | feels_like_c, humidity_percent, precipitation_mm, rain_mm,   |
|                   |                                                               | wind_speed_kmh, wind_gusts_kmh, visibility_m                 |
| analyze_risk      | temperature_c (float), wind_speed_kmh (float), weather_code (int) | risk_level, comfort_index, reasons, recommendation      |
| escalate_to_human | reason (str), city (str)                                     | status, message, incident_id                                 |

## Output Format (STRICT JSON for Action)

Each step must follow this EXACT format:

Thought: <your reasoning here>
Action: {"tool": "<tool_name>", "args": {"<arg_name>": <value>, ...}}

When you have enough information to answer:
Thought: I now have all the information needed.
Final Answer: <your complete travel recommendation>

## Workflow

1. get_coordinates(city_name) → lấy latitude / longitude
2. get_weather(latitude, longitude) → lấy thời tiết thực tế
3. analyze_risk(temperature_c, wind_speed_kmh, weather_code) → đánh giá rủi ro
4. Nếu risk_level là HIGH hoặc CRITICAL → escalate_to_human(reason, city)
5. Final Answer → tổng hợp kết quả cho người dùng

## Few-Shot Example

User: Should I visit Bangkok this weekend?

Thought: I need to get the coordinates of Bangkok first.
Action: {"tool": "get_coordinates", "args": {"city_name": "Bangkok"}}
Observation: {"status": "success", "city": "Bangkok", "country": "Thailand", "latitude": 13.75, "longitude": 100.52}

Thought: I have the coordinates. Now I'll get the current weather.
Action: {"tool": "get_weather", "args": {"latitude": 13.75, "longitude": 100.52}}
Observation: {"status": "success", "weather_description": "Mưa rào nhẹ 🌦️", "weather_code": 80, "temperature_c": 34, "feels_like_c": 38, "humidity_percent": 82, "precipitation_mm": 1.2, "rain_mm": 1.2, "wind_speed_kmh": 18, "wind_gusts_kmh": 28, "visibility_m": 9000}

Thought: Weather data retrieved. Now analyzing the travel risk.
Action: {"tool": "analyze_risk", "args": {"temperature_c": 34, "wind_speed_kmh": 18, "weather_code": 80}}
Observation: {"risk_level": "MEDIUM", "comfort_index": "NÓNG", "reasons": ["Nhiệt độ cao (34°C)", "Có mưa (weather_code: 80)"], "recommendation": "Trời khá nóng, bạn nên chú ý uống nhiều nước. Có mưa. Lời khuyên: Mang theo dù (ô) hoặc áo mưa.", "status": "PROCESSED_V2"}

Thought: Risk is MEDIUM, no need to escalate. I can give a final answer.
Final Answer: Bangkok is experiencing hot weather (34°C, feels like 38°C) with light rain showers. Risk level: MEDIUM. Recommendations: pack light clothes, bring a rain jacket or umbrella, stay hydrated, and avoid midday outdoor activities.
"""

MAX_STEPS   = 10
MAX_RETRIES = 2


# ──────────────────────────────────────────────────────────────
# Tool Registry
# ──────────────────────────────────────────────────────────────
TOOL_REGISTRY = {
    "get_coordinates":   get_coordinates,
    "get_weather":       get_weather,
    "analyze_risk":      analyze_risk,
    "escalate_to_human": escalate_to_human,
}

# Schema validation — required args + expected types cho mỗi tool
TOOL_SCHEMA = {
    "get_coordinates": {
        "required": ["city_name"],
        "types":    {"city_name": str},
    },
    "get_weather": {
        "required": ["latitude", "longitude"],
        "types":    {"latitude": float, "longitude": float},
    },
    "analyze_risk": {
        "required": ["temperature_c", "wind_speed_kmh", "weather_code"],
        "types":    {
            "temperature_c":   (int, float),
            "wind_speed_kmh":  (int, float),
            "weather_code":    int,
        },
    },
    "escalate_to_human": {
        "required": ["reason", "city"],
        "types":    {"reason": str, "city": str},
    },
}

# Alias map — tự động đổi tên arg sai → đúng khi LLM sinh không chuẩn
# vd: LLM trả "city" → tự map thành "city_name"
ARG_ALIASES = {
    "get_coordinates": {"city": "city_name", "name": "city_name"},
    "get_weather":     {"lat": "latitude", "lon": "longitude"},
}


# ──────────────────────────────────────────────────────────────
# Parse Action — JSON format (robust hơn regex của V1)
# ──────────────────────────────────────────────────────────────
def parse_action(action_text: str) -> dict:
    """
    Parse Action line từ JSON string.
    Thử 2 cách: parse trực tiếp → extract JSON từ trong text.

    Returns:
        dict với 'tool' và 'args'
    Raises:
        ValueError nếu không parse được
    """
    action_text = action_text.strip()

    # Cách 1: parse trực tiếp
    try:
        return json.loads(action_text)
    except json.JSONDecodeError:
        pass

    # Cách 2: extract JSON từ trong text (LLM đôi khi thêm text xung quanh)
    match = re.search(r'\{.*\}', action_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Cannot parse action as JSON: '{action_text[:100]}'")


# ──────────────────────────────────────────────────────────────
# Normalize Args — alias fallback
# ──────────────────────────────────────────────────────────────
def normalize_args(tool_name: str, args: dict) -> dict:
    """
    Tự động đổi tên arg sai → đúng theo ARG_ALIASES.
    Không ảnh hưởng nếu LLM đã dùng đúng tên.
    """
    aliases = ARG_ALIASES.get(tool_name, {})
    for wrong_key, correct_key in aliases.items():
        if wrong_key in args and correct_key not in args:
            logger.log_event("AGENT_ARG_ALIAS_APPLIED", {
                "tool":  tool_name,
                "from":  wrong_key,
                "to":    correct_key,
            })
            args[correct_key] = args.pop(wrong_key)
    return args


# ──────────────────────────────────────────────────────────────
# Validate Args — kiểm tra + coerce type trước khi gọi tool
# ──────────────────────────────────────────────────────────────
def validate_args(tool_name: str, args: dict) -> str | None:
    """
    Validate args trước khi gọi tool.

    Returns:
        error message (str) nếu không hợp lệ, None nếu OK.
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
                if expected_type in (float, (int, float)):
                    args[field] = float(args[field])
                elif expected_type is int:
                    args[field] = int(args[field])
            except (ValueError, TypeError):
                return f"Arg '{field}' should be {expected_type}, got {type(args[field])}"

    return None  # OK


# ──────────────────────────────────────────────────────────────
# Run Tool — Normalize → Validate → Execute
# ──────────────────────────────────────────────────────────────
def run_tool(tool_name: str, args: dict):
    """Normalize alias → validate schema → gọi tool function."""
    args  = normalize_args(tool_name, args)
    error = validate_args(tool_name, args)
    if error:
        return {"error": error}

    tool_fn = TOOL_REGISTRY[tool_name]
    return tool_fn(**args)


# ──────────────────────────────────────────────────────────────
# Main Agent Loop
# ──────────────────────────────────────────────────────────────
def run_agent(user_query: str) -> str:
    """
    Chạy ReAct loop với retry và graceful error handling.

    Returns:
        Final answer string
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model   = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-5")
    llm     = AnthropicProvider(model_name=model, api_key=api_key)

    logger.start_trace(agent_version="v2", query=user_query)
    logger.log_event("AGENT_START", {"query": user_query, "model": model})

    print(f"\n{'='*60}")
    print(f"  Smart Weather Planner — ReAct Agent")
    print(f"  Query: {user_query}")
    print(f"{'='*60}")

    conversation = f"User: {user_query}\n"
    step = 0

    while step < MAX_STEPS:
        step += 1
        print(f"\n--- Step {step} ---")

        # ── Gọi LLM (có retry) ──────────────────────────────
        llm_output = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response   = llm.generate(conversation, system_prompt=SYSTEM_PROMPT)
                llm_output = response["content"].strip()
                logger.log_event("LLM_OUTPUT", {
                    "step":           step,
                    "attempt":        attempt + 1,
                    "output_preview": llm_output[:300],
                    "tokens":         response["usage"],
                    "latency_ms":     response["latency_ms"],
                })
                break
            except Exception as e:
                logger.log_event("LLM_ERROR", {
                    "step":    step,
                    "attempt": attempt + 1,
                    "error":   str(e),
                })
                if attempt == MAX_RETRIES:
                    logger.save_trace(outcome="failure")
                    return f"LLM failed after {MAX_RETRIES + 1} attempts: {e}"

        print(llm_output)

        # ── Kiểm tra Final Answer ────────────────────────────
        if "Final Answer:" in llm_output:
            final_answer = llm_output.split("Final Answer:")[-1].strip()
            logger.log_event("AGENT_DONE", {
                "steps":                step,
                "final_answer_preview": final_answer[:200],
            })
            logger.save_trace(outcome="success")
            print(f"\n{'='*60}")
            print(f"  ✅ FINAL ANSWER")
            print(f"{'='*60}")
            print(final_answer)
            return final_answer

        # ── Parse Action line ────────────────────────────────
        action_line = None
        for line in llm_output.splitlines():
            if line.strip().startswith("Action:"):
                action_line = line.replace("Action:", "").strip()
                break

        if not action_line:
            logger.log_event("NO_ACTION", {"step": step})
            observation = (
                'ERROR: No Action found. Please follow the format: '
                'Action: {"tool": "...", "args": {...}}'
            )
            conversation += f"\n{llm_output}\nObservation: {observation}\n"
            continue

        # ── Execute Tool (với retry) ─────────────────────────
        observation = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                action    = parse_action(action_line)
                tool_name = action.get("tool")
                args      = action.get("args", {})

                if not tool_name:
                    raise ValueError("Action JSON missing 'tool' key")

                logger.log_event("TOOL_CALL", {
                    "step":    step,
                    "attempt": attempt + 1,
                    "tool":    tool_name,
                    "args":    args,
                })

                result      = run_tool(tool_name, args)
                observation = json.dumps(result, ensure_ascii=False)

                logger.log_event("TOOL_RESULT", {
                    "step":           step,
                    "tool":           tool_name,
                    "result_preview": observation[:300],
                })

                # Nếu tool trả về error / error_code → log để trace
                if isinstance(result, dict) and (
                    "error" in result or result.get("status") == "error"
                ):
                    logger.log_event("TOOL_SOFT_ERROR", {
                        "step":       step,
                        "tool":       tool_name,
                        "error_code": result.get("error_code"),
                        "message":    result.get("message") or result.get("error"),
                    })

                break  # thành công → thoát retry loop

            except Exception as e:
                logger.log_event("TOOL_EXCEPTION", {
                    "step":    step,
                    "attempt": attempt + 1,
                    "error":   str(e),
                })
                if attempt == MAX_RETRIES:
                    observation = f"ERROR after {MAX_RETRIES + 1} attempts: {str(e)}"
                else:
                    observation = f"Attempt {attempt + 1} failed: {str(e)}. Retrying..."

        # ── Append Observation vào conversation ──────────────
        conversation += f"\n{llm_output}\nObservation: {observation}\n"

    # Quá MAX_STEPS
    logger.log_event("AGENT_MAX_STEPS", {"steps": step})
    logger.save_trace(outcome="failure")
    return f"Agent stopped after {MAX_STEPS} steps without a Final Answer."


if __name__ == "__main__":
    print("Smart Weather Planner — ReAct Agent")
    print("Type 'quit' to exit\n")

    while True:
        query = input("You: ").strip()
        if query.lower() in ["quit", "exit", "q"]:
            break
        if not query:
            continue
        run_agent(query)

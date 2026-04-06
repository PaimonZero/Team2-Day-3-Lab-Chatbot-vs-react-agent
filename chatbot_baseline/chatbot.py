"""
CHATBOT BASELINE — Smart Weather Planner
=========================================
NGƯỜI LÀM: [Thành viên C]

Mục tiêu: Viết một chatbot đơn giản dùng Claude để tư vấn thời tiết.
Chatbot này KHÔNG có tools, chỉ dùng kiến thức LLM sẵn có.
=> Đây là baseline để so sánh với ReAct Agent sau này.

Cách chạy:
    python chatbot_baseline/chatbot.py

Lưu ý:
- Chatbot sẽ trả lời sai / không biết thời tiết real-time
- Đây là intentional failure để highlight điểm yếu của chatbot
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from src.core.anthropic_provider import AnthropicProvider
from src.telemetry.logger import logger

load_dotenv()

SYSTEM_PROMPT = """You are a travel assistant that helps users with weather-related travel advice.
Answer based on your general knowledge about weather patterns and seasons.
Be helpful but honest if you don't have real-time data."""


def run_chatbot():
    """Run the weather chatbot in interactive mode."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-5")
    llm = AnthropicProvider(model_name=model, api_key=api_key)

    print("=" * 50)
    print("  Weather Chatbot Baseline (No Tools)")
    print("  Type 'quit' to exit")
    print("=" * 50)

    conversation_history = []

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ["quit", "exit", "q"]:
            break
        if not user_input:
            continue

        # Build conversation context
        history_text = "\n".join([
            f"User: {h['user']}\nAssistant: {h['assistant']}"
            for h in conversation_history
        ])
        prompt = f"{history_text}\nUser: {user_input}" if history_text else user_input

        logger.log_event("CHATBOT_REQUEST", {"input": user_input})

        result = llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        response = result["content"]

        logger.log_event("CHATBOT_RESPONSE", {
            "response": response[:200],
            "latency_ms": result["latency_ms"],
            "tokens": result["usage"]
        })

        conversation_history.append({
            "user": user_input,
            "assistant": response
        })

        print(f"\nChatbot: {response}")


if __name__ == "__main__":
    run_chatbot()

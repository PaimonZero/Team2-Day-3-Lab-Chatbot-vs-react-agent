"""
baseline/baseline_chatbot.py
─────────────────────────────────────────────────────────────
Chatbot Baseline — Smart Weather Planner
Author  : Nguyễn Đức Hoàng Phúc
Project : Team 2 – Day 3 Lab: Chatbot vs ReAct Agent

Mục đích:
  Làm baseline để so sánh với Agent V1 và V2.
  Chatbot KHÔNG có tools → chỉ trả lời dựa trên kiến thức LLM.
  → Dễ bị sai với dữ liệu thời tiết thực tế (hallucination).

Upload lên GitHub tại: baseline/baseline_chatbot.py

Cách chạy (từ root folder):
    python baseline/baseline_chatbot.py
─────────────────────────────────────────────────────────────
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from src.core.anthropic_provider import AnthropicProvider

load_dotenv()

SYSTEM_PROMPT = """You are a weather assistant chatbot. Answer in Vietnamese.

Rules:
- You DO NOT have access to real-time weather data or any tools.
- You MUST NOT pretend to know exact current weather conditions.
- Answer based on general weather patterns, seasons, and your knowledge — with uncertainty.
- Always clarify that you cannot check live weather.
- Still provide helpful, practical suggestions.

Style:
- Natural, helpful, concise
- Vietnamese language
"""


def chatbot_baseline(question: str) -> str:
    """
    Chatbot baseline — trả lời câu hỏi thời tiết không dùng tools.

    Args:
        question (str): Câu hỏi của người dùng.

    Returns:
        str: Câu trả lời dạng text.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model   = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-5")
    llm     = AnthropicProvider(model_name=model, api_key=api_key)

    response = llm.generate(question, system_prompt=SYSTEM_PROMPT)
    return response["content"]


if __name__ == "__main__":
    print("Chatbot Baseline (no tools)")
    print("Type 'quit' to exit\n")

    while True:
        q = input("You: ").strip()
        if q.lower() in ["quit", "exit", "q"]:
            break
        if not q:
            continue
        answer = chatbot_baseline(q)
        print(f"Bot: {answer}\n")
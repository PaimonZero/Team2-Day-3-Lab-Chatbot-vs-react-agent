from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://models.inference.ai.azure.com/",
    api_key=os.getenv("OPENAI_API_KEY")
)

SYSTEM_PROMPT = """
You are a weather assistant chatbot.

Rules:
- You DO NOT have access to real-time weather data.
- You MUST NOT pretend to know exact current conditions.
- Answer based on general weather patterns and uncertainty.
- If needed, say you are not sure about real-time conditions.
- Still provide helpful suggestions.

Style:
- Natural, helpful, short
- Vietnamese language
"""

def chatbot_baseline(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # hoặc model bạn đang dùng
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content
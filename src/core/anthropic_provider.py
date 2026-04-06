import time
from typing import Dict, Any, Optional, Generator
import anthropic
from src.core.llm_provider import LLMProvider


class AnthropicProvider(LLMProvider):
    """
    LLM Provider for Anthropic Claude models.
    Supports: claude-sonnet-4-5, claude-3-5-haiku-20241022, etc.
    """

    def __init__(self, model_name: str = "claude-sonnet-4-5", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()

        kwargs = {
            "model": self.model_name,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)
        latency_ms = int((time.time() - start_time) * 1000)

        content = response.content[0].text
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "anthropic",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        kwargs = {
            "model": self.model_name,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

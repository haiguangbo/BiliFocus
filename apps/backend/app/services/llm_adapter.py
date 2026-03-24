import json
from abc import ABC, abstractmethod

import httpx

from app.core.config import Settings


class BaseLLMAdapter(ABC):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def available(self) -> bool:
        return self.settings.llm_adapter_configured

    @abstractmethod
    def generate_json(
        self,
        *,
        schema_name: str,
        schema: dict,
        system_prompt: str,
        user_payload: dict,
        max_output_tokens: int,
    ) -> dict:
        raise NotImplementedError


class DisabledLLMAdapter(BaseLLMAdapter):
    @property
    def available(self) -> bool:
        return False

    def generate_json(
        self,
        *,
        schema_name: str,
        schema: dict,
        system_prompt: str,
        user_payload: dict,
        max_output_tokens: int,
    ) -> dict:
        del schema_name, schema, system_prompt, user_payload, max_output_tokens
        raise ValueError("llm adapter is not configured")


class ResponsesCompatibleLLMAdapter(BaseLLMAdapter):
    def __init__(self, settings: Settings, *, base_url: str) -> None:
        super().__init__(settings)
        self.base_url = base_url.rstrip("/")

    def generate_json(
        self,
        *,
        schema_name: str,
        schema: dict,
        system_prompt: str,
        user_payload: dict,
        max_output_tokens: int,
    ) -> dict:
        if not self.available:
            raise ValueError("llm adapter is not configured")

        payload = {
            "model": self.settings.effective_llm_model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": system_prompt,
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(user_payload, ensure_ascii=False),
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
            "max_output_tokens": max_output_tokens,
        }

        if self.settings.effective_llm_reasoning_effort:
            payload["reasoning"] = {"effort": self.settings.effective_llm_reasoning_effort}

        with httpx.Client(timeout=self.settings.llm_refinement_timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/responses",
                headers={
                    "Authorization": f"Bearer {self.settings.effective_llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        return json.loads(self._extract_output_text(body))

    def _extract_output_text(self, body: dict) -> str:
        if isinstance(body.get("output_text"), str) and body["output_text"]:
            return body["output_text"]

        for item in body.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    return content["text"]

        raise ValueError("responses api did not return output_text")


class ChatCompletionsCompatibleLLMAdapter(BaseLLMAdapter):
    def __init__(self, settings: Settings, *, base_url: str) -> None:
        super().__init__(settings)
        self.base_url = base_url.rstrip("/")

    def generate_json(
        self,
        *,
        schema_name: str,
        schema: dict,
        system_prompt: str,
        user_payload: dict,
        max_output_tokens: int,
    ) -> dict:
        if not self.available:
            raise ValueError("llm adapter is not configured")

        schema_hint = json.dumps(schema, ensure_ascii=False)
        payload = {
            "model": self.settings.effective_llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{system_prompt} "
                        "Return valid JSON only, with no markdown fences or extra prose. "
                        f"The JSON must conform to this schema: {schema_hint}"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                },
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": max_output_tokens,
        }

        with httpx.Client(timeout=self.settings.llm_refinement_timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.effective_llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        return json.loads(self._extract_message_content(body))

    def _extract_message_content(self, body: dict) -> str:
        choices = body.get("choices", [])
        if not choices:
            raise ValueError("chat completions api returned no choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
        raise ValueError("chat completions api returned empty content")


def build_llm_adapter(settings: Settings) -> BaseLLMAdapter:
    provider = settings.effective_llm_provider
    if not settings.llm_adapter_configured:
        return DisabledLLMAdapter(settings)
    if provider == "volcengine":
        return ChatCompletionsCompatibleLLMAdapter(settings, base_url=settings.effective_llm_base_url)
    if provider in {"openai", "responses_compatible"}:
        return ResponsesCompatibleLLMAdapter(settings, base_url=settings.effective_llm_base_url)
    if provider == "chat_completions":
        return ChatCompletionsCompatibleLLMAdapter(settings, base_url=settings.effective_llm_base_url)
    return DisabledLLMAdapter(settings)

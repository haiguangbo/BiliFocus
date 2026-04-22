from app.core.config import Settings
from app.services.llm_adapter import (
    ChatCompletionsCompatibleLLMAdapter,
    DisabledLLMAdapter,
    ResponsesCompatibleLLMAdapter,
    build_llm_adapter,
)


def test_build_llm_adapter_uses_volcengine_chat_completions() -> None:
    settings = Settings(
        llm_provider="volcengine",
        llm_base_url="https://ark.cn-beijing.volces.com/api/v3",
        llm_api_key="test-key",
        llm_model="ep-test",
    )

    adapter = build_llm_adapter(settings)

    assert isinstance(adapter, ChatCompletionsCompatibleLLMAdapter)
    assert adapter.available is True


def test_build_llm_adapter_uses_openai_responses() -> None:
    settings = Settings(
        llm_provider="openai",
        llm_base_url="https://api.openai.com/v1",
        llm_api_key="test-key",
        llm_model="gpt-test",
    )

    adapter = build_llm_adapter(settings)

    assert isinstance(adapter, ResponsesCompatibleLLMAdapter)
    assert adapter.available is True


def test_build_llm_adapter_falls_back_to_disabled_without_key_or_model() -> None:
    settings = Settings(
        llm_provider="volcengine",
        llm_base_url="https://ark.cn-beijing.volces.com/api/v3",
        llm_api_key="",
        llm_model="",
    )

    adapter = build_llm_adapter(settings)

    assert isinstance(adapter, DisabledLLMAdapter)
    assert adapter.available is False

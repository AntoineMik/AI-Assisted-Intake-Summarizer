import json
from intake_summarizer.schema import IntakeSummary
from intake_summarizer.llm_client import LLMClient, MockLLMClient, OpenAILLMClient
from intake_summarizer.settings import get_settings
from pydantic import ValidationError

# class RetryableLLMError(RuntimeError):
#     pass

class RetryableLLMError(RuntimeError):
    def __init__(self, message: str, *, raw: str | None = None):
        super().__init__(message)
        self.raw = raw

class NonRetryableLLMError(ValueError):
    def __init__(self, message: str, *, raw: str | None = None):
        super().__init__(message)
        self.raw = raw

def summarize_intake(text: str) -> IntakeSummary:
    client = get_llm_client()
    raw = client.summarize(text)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RetryableLLMError(f"LLM output was not valid JSON: {e}", raw=raw) from e

    try:
        return IntakeSummary.model_validate(payload)
    except ValidationError as e:
        raise NonRetryableLLMError(f"LLM output failed schema validation: {e}", raw=raw) from e

def get_llm_client() -> LLMClient:
    # Expand later: OpenAI, Bedrock, Vertex, etc.
    s = get_settings()
    if s.llm_provider == "mock":
        return MockLLMClient()
    if s.llm_provider == "openai":
        return OpenAILLMClient()
    raise ValueError(f"Unsupported LLM_PROVIDER: {s.llm_provider}")

# def summarize_intake(text: str) -> IntakeSummary:
#     client = get_llm_client()
#     raw = client.summarize(text)

#     try:
#         payload = json.loads(raw)
#     except json.JSONDecodeError as e:
#         raise ValueError(f"LLM output was not valid JSON: {e}") from e

#     # Strict schema validation
#     return IntakeSummary.model_validate(payload)

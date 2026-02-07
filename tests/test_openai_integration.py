import os
import pytest
from intake_summarizer.summarize import summarize_intake
from intake_summarizer.validate import enforce_business_rules

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_OPENAI_TESTS") != "1",
    reason="Set RUN_OPENAI_TESTS=1 to run OpenAI integration tests."
)

def test_openai_returns_valid_schema_and_emergency_triage():
    text = "Patient reports chest pain and shortness of breath since yesterday."
    summary = summarize_intake(text)
    summary = enforce_business_rules(summary, text)

    # hard requirements (schema already enforced, but these are behavior checks)
    assert summary.urgency == "emergency"
    assert summary.triage_category == "in_person"

# When ready to test OpenAI integration, set your API key in the environment and run:
# RUN_OPENAI_TESTS=1 LLM_PROVIDER=openai LLM_MODEL=gpt-5 python -m pytest -q
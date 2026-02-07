import pytest
from intake_summarizer.schema import IntakeSummary

def test_schema_rejects_long_chief_complaint():
    payload = {
        "chief_complaint": "x" * 200,
        "symptoms": [],
        "duration": "unknown",
        "urgency": "unknown",
        "triage_category": "unknown", # ✅ NEW
        "red_flags": [],
        "recommended_next_step": "test",
        "confidence": 0.5,
        "notes": "ok",
    }
    with pytest.raises(Exception):
        IntakeSummary.model_validate(payload)
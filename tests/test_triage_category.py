from intake_summarizer.summarize import summarize_intake
from intake_summarizer.validate import enforce_business_rules

def test_emergency_forces_in_person_triage():
    text = "Patient reports chest pain and shortness of breath since yesterday."
    summary = summarize_intake(text)
    summary = enforce_business_rules(summary, text)
    assert summary.urgency == "emergency"
    assert summary.triage_category == "in_person"

def test_telehealth_keyword_sets_telehealth_when_not_emergency():
    text = "Patient requests a virtual video visit for mild sore throat."
    summary = summarize_intake(text)
    summary = enforce_business_rules(summary, text)
    assert summary.urgency in ["urgent", "routine", "unknown"]  # mock may vary
    assert summary.triage_category == "telehealth"

def test_emergency_adds_standard_emergency_flag():
    text = "Patient reports chest pain and shortness of breath since yesterday."
    summary = summarize_intake(text)
    summary = enforce_business_rules(summary, text)
    assert "Emergency indicators present in intake text." in summary.red_flags
from intake_summarizer.summarize import summarize_intake

def test_mock_is_deterministic():
    text = "Patient reports chest pain and shortness of breath since yesterday."
    s1 = summarize_intake(text).model_dump()
    s2 = summarize_intake(text).model_dump()
    assert s1 == s2
    assert s1["urgency"] in ["emergency", "urgent", "routine", "unknown"]
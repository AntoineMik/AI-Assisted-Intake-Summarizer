from intake_summarizer.schema import IntakeSummary

IN_PERSON_KEYWORDS = {"walk in", "walk-in", "need to be seen", "clinic", "exam", "appointment today"}
TELEHEALTH_KEYWORDS = {"telehealth", "virtual", "video visit", "video call"}
SELF_CARE_KEYWORDS = {"mild", "runny nose", "sore throat", "seasonal allergies", "congestion"}
BREATH_TERMS = {"shortness of breath", "trouble breathing", "can't breathe", "cannot breathe", "short of breath", "sob"}

def contains_any(text: str, phrases: set[str]) -> bool:
    return any(p in text for p in phrases)

def enforce_business_rules(summary: IntakeSummary, original_text: str) -> IntakeSummary:
    lowered = original_text.lower()

    # Emergency indicators (existing rule)
    has_emergency_indicator = (
        "chest pain" in lowered
        and any (t in lowered for t in BREATH_TERMS)
    )

    STANDARD_EMERGENCY_FLAG = "Emergency indicators present in intake text."

    if has_emergency_indicator:
        summary.urgency = "emergency"
        if STANDARD_EMERGENCY_FLAG not in summary.red_flags:
            summary.red_flags.append(STANDARD_EMERGENCY_FLAG)

    # ✅ NEW: triage_category deterministic rules
    # Precedence: in_person > telehealth > self_care > unknown
    if summary.urgency == "emergency":
        summary.triage_category = "in_person"
    else:
        # keyword-based classification
        if contains_any(lowered, IN_PERSON_KEYWORDS):
            summary.triage_category = "in_person"
        elif contains_any(lowered, TELEHEALTH_KEYWORDS):
            summary.triage_category = "telehealth"
        elif contains_any(lowered, SELF_CARE_KEYWORDS):
            summary.triage_category = "self_care"
        else:
            summary.triage_category = "unknown"

    # Confidence guardrail example (existing behavior)
    if summary.duration == "unknown" and summary.confidence > 0.9:
        summary.confidence = 0.75

    if summary.urgency == "emergency":
        summary.recommended_next_step = "Seek emergency care immediately or call emergency services."

    return summary
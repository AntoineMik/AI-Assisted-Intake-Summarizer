# Intake Summarizer Spec (v0.1)

## Goal
Convert raw intake text into a structured, conservative summary.

## Output Contract (required fields)
- chief_complaint: short string (<= 120 chars)
- symptoms: list of strings (0..10 items, each <= 80 chars)
- duration: string (<= 60 chars) - e.g., "2 days", "since yesterday", "unknown"
- urgency: one of ["emergency", "urgent", "routine", "unknown"]
- red_flags: list of strings (0..10 items)
- recommended_next_step: short string (<= 140 chars)
- confidence: float (0.0..1.0)
- notes: short string (<= 200 chars)

## New Field: triage_category (required)

Allowed values:
- telehealth
- in_person
- self_care
- unknown
# Precedence: in_person > telehealth > self_care > unknown

Rules (deterministic):
- If urgency == "emergency" → triage_category must be "in_person"
- If intake text contains any in-person keywords (e.g., "need to be seen", "walk in", "clinic", "exam") → "in_person"
- If intake text contains telehealth keywords (e.g., "video visit", "telehealth", "virtual") and no emergency indicators → "telehealth"
- If intake text indicates mild/common issues and self-care keywords (e.g., "mild", "sore throat", "runny nose") and no emergency indicators → "self_care"
- Otherwise → "unknown"

## Safety rules
- Do NOT invent diagnoses, medications, vitals, or history not present.
- If information is missing, use "unknown" or an empty list.
- If the text contains emergency indicators (e.g., chest pain + shortness of breath, stroke symptoms), urgency must be "emergency".

## Determinism
- For identical inputs, output should be stable given same model/settings.
from pydantic import BaseModel, Field, field_validator, conlist
from typing import Literal, List, Annotated

Urgency = Literal["emergency", "urgent", "routine", "unknown"]
TriageCategory = Literal["telehealth", "in_person", "self_care", "unknown"]

class IntakeSummary(BaseModel):
    chief_complaint: str = Field(..., max_length=120)
    symptoms: conlist(str, max_length=10) = []
    duration: str = Field(..., max_length=60)
    urgency: Urgency
    triage_category: TriageCategory  # ✅ NEW
    red_flags: conlist(str, max_length=10) = []
    recommended_next_step: str = Field(..., max_length=140)
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: str = Field(..., max_length=200)

    @field_validator("symptoms", "red_flags")
    @classmethod
    def validate_list_items(cls, v):
        if len(v) > 10:
            raise ValueError("List too long (max 10).")
        for item in v:
            if not isinstance(item, str):
                raise ValueError("List items must be strings.")
            if len(item) > 80:
                raise ValueError("List item too long (max 80 chars).")
        return v
    

from pydantic import BaseModel
from typing import Literal, Optional

class IntakeResult(BaseModel):
    status: Literal["ok", "failed"]
    out_path: Optional[str] = None

    # failure fields
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    failure_artifact: Optional[str] = None
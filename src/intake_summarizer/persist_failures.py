import json
import os, hashlib
from datetime import datetime, timezone
from pathlib import Path

FAIL_DIR = Path("out") / "fail"
FAIL_DIR.mkdir(parents=True, exist_ok=True)

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def persist_failure(
    *,
    text: str,
    provider: str,
    model: str,
    error_type: str,
    error_message: str,
    raw_output: str | None = None,
    
    
) -> Path:
    """
    Writes a structured failure artifact for debugging.
    - Uses deterministic key based on input text (idempotent)
    - Truncates raw output to limit sensitive exposure
    """
    key = _sha256_hex(text)[:16]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = FAIL_DIR / f"intake_failure_{key}_{ts}.json"
    keep_raw = os.getenv("KEEP_RAW_LLM_OUTPUT", "0") == "1"
    raw = raw_output or ""
    raw_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest() if raw else None

    payload = {
        "key": key,
        "timestamp_utc": ts,
        "provider": provider,
        "model": model,
        "error_type": error_type,
        "error_message": error_message,
        "raw_output_preview": raw[:200] if keep_raw else "",  # cap
    }

    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
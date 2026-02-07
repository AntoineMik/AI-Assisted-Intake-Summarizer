# import json
# from datetime import datetime, timezone
# from pathlib import Path
# from intake_summarizer.schema import IntakeSummary

# OUT_DIR = Path("out")
# OUT_DIR.mkdir(exist_ok=True)

# def persist_summary(summary: IntakeSummary) -> Path:
#     ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
#     path = OUT_DIR / f"intake_summary_{ts}.json"
#     path.write_text(json.dumps(summary.model_dump(), indent=2), encoding="utf-8")
#     return path

import json
import hashlib
from pathlib import Path
from intake_summarizer.schema import IntakeSummary

OUT_DIR = Path("out")
OUT_DIR.mkdir(exist_ok=True)

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def persist_summary(summary: IntakeSummary, *, text: str) -> Path:
    """
    Idempotent persistence:
    - Same intake text -> same output path
    - Prevents duplicates across retries / reruns
    - Uses atomic write via temp file + replace
    """
    # comparing providers/models
    # key_material = f"{settings.llm_provider}|{settings.llm_model}|{text}"
    # key = _sha256_hex(key_material)[:16]

    key = _sha256_hex(text)[:16]  # short stable identifier
    path = OUT_DIR / f"intake_summary_{key}.json"

    payload = summary.model_dump()
    data = json.dumps(payload, indent=2, ensure_ascii=False)

    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(data, encoding="utf-8")
    tmp_path.replace(path)  # atomic on same filesystem

    return path
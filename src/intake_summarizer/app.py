from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
import logging

from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from intake_summarizer.schema import IntakeSummary
from intake_summarizer.summarize import summarize_intake, RetryableLLMError
from intake_summarizer.validate import enforce_business_rules
from intake_summarizer.persist import persist_summary
from intake_summarizer.llm_client import LLMClient, MockLLMClient
from intake_summarizer.settings import get_settings

logger = logging.getLogger(__name__)

GENERIC_USER_ERROR = (
    "We couldn’t generate a structured summary. "
    "Please retry or contact support."
)

app = FastAPI(title="Clinician Intake Summarizer", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

MAX_UPLOAD_BYTES = 200_000


def _decode_upload(upload: UploadFile, raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


def _run_pipeline(
    text: str,
    persist: bool,
    client_override: Optional[LLMClient] = None,
) -> tuple[IntakeSummary, Optional[str]]:
    summary = summarize_intake(text, client=client_override)
    summary = enforce_business_rules(summary, text)
    out_path = str(persist_summary(summary, text=text)) if persist else None    
    return summary, out_path


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_persist": True,
            "samples": _load_samples_index(),
            "raw_input": "",
        },
    )

@app.post("/summarize", response_class=HTMLResponse)
async def summarize_route(
    request: Request,
    intake_text: str = Form(default=""),
    persist: bool = Form(default=True),
    file: UploadFile | None = File(default=None),
    chaos_enabled: bool = Form(default=False),
    chaos_rate: float = Form(default=0.0),
    chaos_seed: str = Form(default=""),
) -> HTMLResponse:
    text = (intake_text or "").strip()

    # file overrides paste
    if file is not None and file.filename:
        raw = await file.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "default_persist": persist,
                    "samples": _load_samples_index(),
                    "error_message": "Uploaded file is too large. Please upload a smaller .txt file.",
                    "raw_input": text,
                },
                status_code=200,
            )
        file_text = _decode_upload(file, raw).strip()
        if file_text:
            text = file_text

    if not text:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "default_persist": persist,
                "samples": _load_samples_index(),
                "error_message": "Please paste intake text or upload a .txt file.",
            },
            status_code=200,
        )

    s = get_settings()
    client_override: Optional[LLMClient] = None
    if s.llm_provider == "mock":
        seed_val = int(chaos_seed) if chaos_seed.strip().isdigit() else None
        client_override = MockLLMClient(
            chaos_enabled=chaos_enabled,
            chaos_rate=chaos_rate,
            chaos_seed=seed_val,
        )

    try:
        summary, out_path = _run_pipeline(text, persist=persist, client_override=client_override)
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "summary": summary.model_dump(),
                "out_path": out_path,
                "original_text": text,
                "persisted": bool(out_path),
                "chaos_enabled": chaos_enabled,
                "chaos_rate": chaos_rate,
                "chaos_seed": chaos_seed,
            },
        )
    except Exception:
        logger.exception("Summarization request failed")
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "default_persist": persist,
                "error_message": GENERIC_USER_ERROR,
                "raw_input": text,
            },
            status_code=200,
        )


@app.post("/api/summarize")
async def api_summarize(
    intake_text: str = Form(default=""),
    persist: bool = Form(default=True),
    file: UploadFile | None = File(default=None),
    chaos_enabled: bool = Form(default=False),
    chaos_rate: float = Form(default=0.0),
    chaos_seed: str = Form(default=""),
) -> JSONResponse:
    text = (intake_text or "").strip()

    # file overrides paste
    if file is not None and file.filename:
        raw = await file.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": f"File too large (max {MAX_UPLOAD_BYTES} bytes)."},
            )
        file_text = _decode_upload(file, raw).strip()
        if file_text:
            text = file_text

    if not text:
        return JSONResponse(status_code=400, content={"status": "error", "error": "No intake text provided."})

    s = get_settings()
    client_override: Optional[LLMClient] = None
    if s.llm_provider == "mock":
        seed_val = int(chaos_seed) if chaos_seed.strip().isdigit() else None
        client_override = MockLLMClient(
            chaos_enabled=chaos_enabled,
            chaos_rate=chaos_rate,
            chaos_seed=seed_val,
        )

    try:
        summary, out_path = _run_pipeline(text, persist=persist, client_override=client_override)
        return JSONResponse(content={"status": "ok", "summary": summary.model_dump(), "out_path": out_path})
    except RetryableLLMError as e:
        return JSONResponse(status_code=503, content={"status": "error", "error": str(e)})
    except ValueError as e:
        return JSONResponse(status_code=422, content={"status": "error", "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error": f"Unexpected error: {e}"})


@app.get("/download")
def download_example() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=302)

from fastapi import HTTPException
from fastapi.responses import PlainTextResponse

SAMPLES_DIR = BASE_DIR / "samples"
SAMPLES_INDEX = SAMPLES_DIR / "index.json"

SAMPLES = {
    "emergency": ("Emergency: Chest pain + SOB", "emergency_chest_pain.txt"),
    "telehealth": ("Telehealth: URI symptoms", "telehealth_upper_respiratory.txt"),
    "routine": ("Routine: Refill request", "routine_med_refill.txt"),
}

@app.get("/api/samples")
def api_samples() -> dict:
    return {"samples": _load_samples_index()}

@app.get("/api/samples/{sample_id}")
def api_sample_text(sample_id: str) -> dict:
    return {"id": sample_id, "text": _read_sample_text(sample_id)}


def get_sample(sample_id: str):
    if sample_id not in SAMPLES:
        raise HTTPException(status_code=404, detail="Sample not found")
    _, filename = SAMPLES[sample_id]
    path = SAMPLES_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Sample file missing")
    return path.read_text(encoding="utf-8")


def _load_samples_index() -> list[dict]:
    if not SAMPLES_INDEX.exists():
        return []
    data = json.loads(SAMPLES_INDEX.read_text(encoding="utf-8"))
    samples = data.get("samples", [])
    # Only include entries whose files exist
    out = []
    for s in samples:
        fn = s.get("filename")
        if not fn:
            continue
        if (SAMPLES_DIR / fn).exists():
            out.append(s)
    return out


def _read_sample_text(sample_id: str) -> str:
    samples = _load_samples_index()
    match = next((s for s in samples if s.get("id") == sample_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Sample not found")
    path = SAMPLES_DIR / match["filename"]
    return path.read_text(encoding="utf-8")
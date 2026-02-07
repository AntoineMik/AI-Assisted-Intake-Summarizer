from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from intake_summarizer.schema import IntakeSummary
from intake_summarizer.summarize import summarize_intake, RetryableLLMError
from intake_summarizer.validate import enforce_business_rules
from intake_summarizer.persist import persist_summary


app = FastAPI(
    title="AI-Assisted Intake Summarizer",
    version="0.1.0",
    description="Clinician-facing API for intake summarization + deterministic rules.",
)


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10_000)
    persist: bool = Field(default=True, description="If true, writes output JSON to out/")
    include_original_text: bool = Field(
        default=False,
        description="If true, returns the original intake text in the response payload.",
    )


class SummarizeResponse(BaseModel):
    status: str = "ok"
    summary: IntakeSummary
    out_path: str | None = None
    original_text: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    # Minimal clinician UI (no build tooling)
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Intake Summarizer</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }
    textarea { width: 100%; min-height: 160px; padding: 12px; font-size: 14px; }
    button { padding: 10px 14px; font-size: 14px; cursor: pointer; }
    .row { display: flex; gap: 16px; align-items: center; margin: 12px 0; }
    .card { border: 1px solid #ddd; border-radius: 10px; padding: 14px; }
    pre { white-space: pre-wrap; word-break: break-word; }
    label { display: inline-flex; gap: 8px; align-items: center; }
  </style>
</head>
<body>
  <h1>AI-Assisted Intake Summarizer</h1>
  <p>Paste intake text below. The system will generate a structured summary and apply deterministic safety rules.</p>

  <div class="card">
    <textarea id="text" placeholder="Example: Patient reports chest pain and shortness of breath since yesterday."></textarea>

    <div class="row">
      <label><input type="checkbox" id="persist" checked /> Persist to <code>out/</code></label>
      <label><input type="checkbox" id="include_original" /> Include original text in response</label>
      <button onclick="run()">Summarize</button>
    </div>

    <h3>Output</h3>
    <pre id="out">(waiting...)</pre>
  </div>

<script>
async function run() {
  const text = document.getElementById("text").value;
  const persist = document.getElementById("persist").checked;
  const include_original_text = document.getElementById("include_original").checked;

  document.getElementById("out").textContent = "Running...";
  try {
    const resp = await fetch("/api/summarize", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({text, persist, include_original_text})
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data?.detail || "Request failed");
    document.getElementById("out").textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    document.getElementById("out").textContent = "ERROR: " + e.message;
  }
}
</script>

</body>
</html>"""


@app.post("/api/summarize", response_model=SummarizeResponse)
def api_summarize(req: SummarizeRequest) -> SummarizeResponse:
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    try:
        # 1) LLM summary (mock/openai)
        summary = summarize_intake(text)

        # 2) deterministic overrides (safety/business rules)
        summary = enforce_business_rules(summary, text)

        # 3) persist if requested
        out_path = str(persist_summary(summary, text=text)) if req.persist else None

        return SummarizeResponse(
            summary=summary,
            out_path=out_path,
            original_text=text if req.include_original_text else None,
        )

    except RetryableLLMError as e:
        # Transient / formatting failures
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        # Schema mismatches or non-retryable failures
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}") from e
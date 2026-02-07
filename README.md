# AI-Assisted Intake Summarizer

## Overview

The **AI-Assisted Intake Summarizer** is a safety-first clinical intake processing system that converts unstructured patient text into a structured, auditable summary for clinician review.

> ⚠️ **This system does NOT provide diagnoses or medical advice.**  
> It is an **intake triage and summarization assistant**, not a clinical decision engine.

The system is designed so that **LLMs assist — but never decide**.  
All critical decisions (urgency, routing, escalation) are enforced deterministically in code.

---

## Primary Goals

- Convert free-text intake messages into structured summaries
- Identify urgency signals reliably and conservatively
- Route intakes to appropriate care paths (telehealth / in-person / self-care)
- Ensure every output is **auditable, reproducible, and explainable**
- Handle failures safely without blocking the rest of the workload

---

## Installation

### Prerequisites

- Python **3.11+**
- `pip` or `uv`
- (Optional) OpenAI API key for real LLM usage

### Clone the Repository

```bash
git clone https://github.com/your-org/ai-assisted-intake-summarizer.git
cd ai-assisted-intake-summarizer
```

### Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate    # Windows
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Quickstart

### 1. Run with Mock LLM (Recommended First)

The mock provider is deterministic and requires no API keys.

```bash
export LLM_PROVIDER=mock
python -m intake_summarizer.flow
```

### 2. Run Batch Intake from a File

Create an input file (`inputs.txt`), one intake per line:

```text
mild sore throat wants video visit
chest pain and shortness of breath since yesterday
```

Run the batch flow:

```bash
python -m intake_summarizer.cli inputs.txt
```

Outputs:
- Successful summaries → `out/`
- Failure artifacts → `out/fail/`

### 3. Enable Chaos Testing (Optional)

Simulate LLM instability:

```bash
export MOCK_CHAOS=1
export MOCK_CHAOS_RATE=0.6
python -m intake_summarizer.cli inputs.txt
```

---

## High-Level Architecture

```
Raw Intake Text
      │
      ▼
LLM Client (Mock / OpenAI)
      │
      ▼
JSON Parsing
      │
      ▼
Schema Validation (Pydantic)
      │
      ▼
Deterministic Business Rules
      │
      ▼
Persistence (success or failure)
      │
      ▼
Structured Output for Clinician Review
```

---

## Project Structure

```
src/intake_summarizer/
├── cli.py                 # CLI entrypoint (batch from file)
├── flow.py                # Prefect flows (single + batch)
├── llm_client.py          # LLM abstraction (mock / OpenAI)
├── persist.py             # Successful output persistence
├── persist_failures.py    # Failure artifact persistence
├── schema.py              # Pydantic data contract
├── settings.py            # Environment-driven configuration
├── summarize.py           # LLM call + validation boundary
├── validate.py            # Deterministic business rules
└── __init__.py
```

---

## Data Contract

### IntakeSummary Schema
This is the single source of truth for what the system produces.

```python
class IntakeSummary(BaseModel):
    chief_complaint: str
    symptoms: List[str]
    duration: str
    urgency: Literal["emergency", "urgent", "routine", "unknown"]
    triage_category: Literal["telehealth", "in_person", "self_care", "unknown"]
    red_flags: List[str]
    recommended_next_step: str
    confidence: float
    notes: str
```
Why this exists
	•	Prevents silent schema drift
	•	Forces explicit handling of uncertainty
	•	Ensures downstream systems receive predictable data
	•	Makes outputs reviewable by clinicians and auditors

---

## Configuration

```bash
LLM_PROVIDER=mock | openai
LLM_MODEL=gpt-4.1
OPENAI_API_KEY=sk-...
MOCK_CHAOS=1
MOCK_CHAOS_RATE=0.6
MOCK_CHAOS_SEED=1
```

---

MockLLMClient
	•	Deterministic
	•	No external dependencies
	•	Optional chaos injection for failure testing

Why:
You can validate the entire system (flows, retries, persistence, batch behavior) without paying for LLM calls.

⸻

OpenAILLMClient
	•	Uses structured JSON schema output
	•	temperature = 0
	•	No storage of sensitive data

Why:
Guarantees machine-parseable output and reduces hallucination risk.

### Summarization Boundary (summarize.py)

summarize_intake(text)

Responsibilities:
	1.	Call the LLM
	2.	Parse JSON
	3.	Validate against IntakeSummary
	4.	Classify errors as retryable vs non-retryable

```python
try:
    payload = json.loads(raw)
except JSONDecodeError:
    raise RetryableLLMError
```
Why this boundary matters
	•	LLM output is untrusted input
	•	JSON parsing failures are transient → retry
	•	Schema violations are structural → fail fast

⸻

### Deterministic Rules (validate.py)

enforce_business_rules(summary, original_text)

This function overrides the LLM when safety or policy requires it.

Examples:
	•	Emergency urgency → force triage_category = "in_person"
	•	Add standardized red flags
	•	Cap confidence when information is missing

Why this exists
	•	Clinicians and regulators will not accept “the model decided”
	•	This is where medical policy lives
	•	Fully testable and explainable

### Persistence

#### Successful Outputs (persist.py)

Saved to:
```text
out/intake_summary_<timestamp>.json
```
Failures (persist_failures.py)

Saved to:
```text
out/fail/intake_failure_<hash>_<timestamp>.json
```
Each failure artifact includes:
	•	original input
	•	provider and model
	•	error type
	•	error message
	•	raw model output (if available)

Why
	•	No silent failures
	•	Enables incident review
	•	Supports compliance and debugging

⸻

### Orchestration (flow.py)

Single Intake Flow

Used for:
	•	Interactive runs
	•	Clinician UI
	•	API requests

Retry behavior:
	•	Retries occur at the task level
	•	The flow itself does not retry

### Batch Flow (Best-Effort)

Processes many intakes concurrently:
	•	One failure does not stop the batch
	•	Each item returns a structured result

```python
IntakeResult(
  status="ok" | "failed",
  out_path=...,
  error_type=...,
  error_message=...,
)
```
## Final Note

This project prioritizes **safety, determinism, and auditability** over raw automation.

from prefect import flow, task, get_run_logger
from intake_summarizer.summarize import summarize_intake, RetryableLLMError, NonRetryableLLMError
from intake_summarizer.validate import enforce_business_rules
from intake_summarizer.persist import persist_summary
from intake_summarizer.schema import IntakeSummary
from intake_summarizer.settings import get_settings
from intake_summarizer.persist_failures import persist_failure
from intake_summarizer.results import IntakeResult
import time

def _unwrap_exc(e: Exception) -> Exception:
    cur = e
    while True:
        nxt = getattr(cur, "__cause__", None) or getattr(cur, "__context__", None)
        if not nxt:
            return cur
        cur = nxt

@task(retries=0)  # IMPORTANT: disable Prefect retries; we do selective retry ourselves
def t_summarize(text: str, max_attempts: int = 3, delay_seconds: float = 2.0) -> IntakeSummary:
    logger = get_run_logger()
    attempt = 0

    while True:
        attempt += 1
        try:
            logger.info(f"Calling summarizer (LLM). attempt={attempt}/{max_attempts}")
            return summarize_intake(text)

        except RetryableLLMError as e:
            logger.warning(f"Retryable LLM failure: {e}")
            if attempt >= max_attempts:
                raise
            time.sleep(delay_seconds)

        except NonRetryableLLMError:
            # Contract mismatch: do NOT retry
            raise

@task
def t_validate(summary: IntakeSummary, text: str) -> IntakeSummary:
    return enforce_business_rules(summary, text)

@task
def t_persist(summary: IntakeSummary, text: str) -> str:
    path = persist_summary(summary, text=text)
    return str(path)

@flow(name="intake-summarizer", retries=0)
def intake_flow(text: str) -> str:
    logger = get_run_logger()
    logger.info("Starting intake summarization flow.")
    s = get_settings()

    try:
        summary = t_summarize(text)  # selective retries happen inside task
        summary = t_validate(summary, text)
        out_path = t_persist(summary, text)

    except Exception as e:
        root = _unwrap_exc(e)

        if isinstance(root, (RetryableLLMError, NonRetryableLLMError)):
            fail_path = persist_failure(
                text=text,
                provider=s.llm_provider,
                model=s.llm_model,
                error_type=type(root).__name__,
                error_message=str(root),
                raw_output=getattr(root, "raw", None),
            )
            logger.error(f"Persisted failure artifact to: {fail_path}")

        raise

    logger.info(f"Persisted summary to: {out_path}")
    return out_path

# @task
# def t_persist(summary: IntakeSummary) -> str:
#     path = persist_summary(summary)
#     return str(path)

# @flow(name="intake-summarizer", retries=1, retry_delay_seconds=10)
# def intake_flow(text: str) -> str:
#     logger = get_run_logger()
#     logger.info("Starting intake summarization flow.")
#     summary = t_summarize(text)
#     summary = t_validate(summary, text)
#     out_path = t_persist(summary, text)
#     logger.info(f"Persisted summary to: {out_path}")
#     return out_path

@flow(name="intake-summarizer-batch")
def intake_batch_flow(texts: list[str]) -> list[IntakeResult]:
    logger = get_run_logger()
    logger.info(f"Starting batch intake flow. count={len(texts)}")

    futures = t_process_one.map(texts)
    # Resolve to actual values (not State objects)
    results: list[IntakeResult] = [f.result(raise_on_failure=False) for f in futures]

    ok = sum(1 for r in results if r.status == "ok")
    failed = len(results) - ok
    logger.info(f"Batch complete. ok={ok} failed={failed}")

    
    return results

@task(retries=0)
def t_process_one(text: str) -> IntakeResult:
    """
    Best-effort wrapper:
    - summarize has internal retries already (via t_summarize) OR you can inline summarize here.
    - this task never raises for expected LLM failures; it returns a failed result instead.
    """
    logger = get_run_logger()
    s = get_settings()

    try:
        summary = summarize_intake(text)  # NOTE: this will raise RetryableLLMError/NonRetryableLLMError
        summary = enforce_business_rules(summary, text)
        out_path = persist_summary(summary, text=text)
        return IntakeResult(status="ok", out_path=str(out_path))

    except (RetryableLLMError, NonRetryableLLMError) as e:
        fail_path = persist_failure(
            text=text,
            provider=s.llm_provider,
            model=s.llm_model,
            error_type=type(e).__name__,
            error_message=str(e),
            raw_output=getattr(e, "raw", None),
        )
        logger.error(f"Intake failed; wrote failure artifact: {fail_path}")
        return IntakeResult(
            status="failed",
            error_type=type(e).__name__,
            error_message=str(e),
            failure_artifact=str(fail_path),
        )
    


if __name__ == "__main__":
    sample = "Patient reports chest pain and shortness of breath since yesterday."
    print(intake_flow(sample))
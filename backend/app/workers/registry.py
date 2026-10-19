"""Registered job task handlers and failure classification."""

import asyncio
import time
from typing import Any, Callable, Coroutine, Dict
from pydantic import BaseModel


class TransientExecutionError(Exception):
    """Temporary failure eligible for retry (e.g. network timeout, rate limit)."""
    pass


class PermanentExecutionError(Exception):
    """Fatal failure that will not succeed upon retry (e.g. poison pill, invalid payload)."""
    pass


class ExecutionContext(BaseModel):
    """Contextual metadata passed to a running task handler."""
    job_id: str
    attempt_number: int
    worker_id: str


# Type alias for task handler coroutine
TaskHandler = Callable[[Dict[str, Any], ExecutionContext], Coroutine[Any, Any, Dict[str, Any]]]

_HANDLER_REGISTRY: Dict[str, TaskHandler] = {}


def register_handler(job_type: str) -> Callable[[TaskHandler], TaskHandler]:
    """Decorator for registering an approved job handler."""
    def decorator(fn: TaskHandler) -> TaskHandler:
        _HANDLER_REGISTRY[job_type] = fn
        return fn
    return decorator


def get_handler(job_type: str) -> TaskHandler:
    """Retrieves registered task handler or raises PermanentExecutionError."""
    if job_type not in _HANDLER_REGISTRY:
        raise PermanentExecutionError(f"Unknown or unapproved job handler for type '{job_type}'.")
    return _HANDLER_REGISTRY[job_type]


# ==============================================================================
# Standard Business Handlers
# ==============================================================================

@register_handler("report_generation")
async def handle_report_generation(payload: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
    """Generates analytical report with simulated processing duration."""
    report_format = payload.get("format", "pdf")
    row_count = payload.get("rows", 250)

    # Simulated non-blocking computation
    await asyncio.sleep(0.05)

    return {
        "status": "generated",
        "format": report_format,
        "rows_processed": row_count,
        "generated_by": context.worker_id,
        "output_url": f"https://storage.taskforge.dev/reports/{context.job_id}.{report_format}"
    }


@register_handler("dataset_processing")
async def handle_dataset_processing(payload: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
    """Processes batch records and calculates summary statistics."""
    batch_size = payload.get("batch_size", 100)
    await asyncio.sleep(0.05)
    return {
        "batch_size": batch_size,
        "records_ingested": batch_size,
        "checksum": f"sha256:{hash(context.job_id)}",
        "processed_at": time.time()
    }


@register_handler("notification_dispatch")
async def handle_notification_dispatch(payload: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
    """Simulates multi-channel notification dispatch."""
    recipient = payload.get("recipient", "ops@taskforge.dev")
    channel = payload.get("channel", "email")
    await asyncio.sleep(0.02)
    return {
        "channel": channel,
        "recipient": recipient,
        "delivered": True,
        "delivery_id": f"del-{context.job_id[:8]}"
    }


@register_handler("data_pipeline")
async def handle_data_pipeline(payload: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
    """Multi-step ETL pipeline handler."""
    steps = payload.get("steps", ["extract", "transform", "load"])
    await asyncio.sleep(0.05)
    return {
        "steps_completed": steps,
        "pipeline_id": payload.get("pipeline_id", context.job_id)
    }


# ==============================================================================
# Deterministic Chaos & Testing Handlers
# ==============================================================================

@register_handler("chaos_flaky_task")
async def handle_chaos_flaky_task(payload: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
    """
    Fails with TransientExecutionError for the first N attempts, then succeeds.
    Used for verifying bounded retries and exponential backoff with jitter.
    """
    fail_until_attempt = payload.get("fail_until_attempt", 2)
    if context.attempt_number <= fail_until_attempt:
        raise TransientExecutionError(
            f"Simulated transient upstream timeout on attempt {context.attempt_number} (will succeed after attempt {fail_until_attempt})."
        )
    return {
        "status": "recovered",
        "succeeded_on_attempt": context.attempt_number,
        "message": "Flaky task successfully recovered after backoff retry."
    }


@register_handler("chaos_poison_pill")
async def handle_chaos_poison_pill(payload: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
    """
    Always raises PermanentExecutionError.
    Used for verifying non-retryable failure classification and dead-letter routing.
    """
    error_msg = payload.get("error_message", "Fatal schema violation: Poison pill payload cannot be processed.")
    raise PermanentExecutionError(error_msg)


@register_handler("chaos_slow_worker")
async def handle_chaos_slow_worker(payload: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
    """
    Sleeps for longer than timeout or lease.
    Used for verifying timeout cancellation and abandoned lease recovery.
    """
    sleep_seconds = payload.get("sleep_seconds", 10.0)
    await asyncio.sleep(sleep_seconds)
    return {"slept_seconds": sleep_seconds}

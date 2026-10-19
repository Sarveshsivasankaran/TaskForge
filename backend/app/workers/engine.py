"""Core asynchronous Worker Engine for TaskForge."""

import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.enums import AttemptStatus, JobStatus
from app.queue.base import BaseQueueClient, QueueMessage
from app.queue.factory import get_queue_client
from app.services.job_repository import JobRepository
from app.workers.backoff import calculate_backoff_delay
from app.workers.registry import (
    ExecutionContext,
    get_handler,
    PermanentExecutionError,
    TransientExecutionError,
)


class WorkerEngine:
    """
    Asynchronous background worker engine.
    Fetches job messages, acquires optimistic concurrency leases, executes registered handlers,
    enforces deadlines, records execution attempts, and routes failures to backoff retries or DLQ.
    """

    def __init__(
        self,
        worker_id: Optional[str] = None,
        concurrency: int = settings.worker_concurrency,
        queue_client: Optional[BaseQueueClient] = None,
        queue_name: str = settings.queue_name,
        session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
        lease_duration_seconds: int = 60
    ):
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.concurrency = concurrency
        self.queue_client = queue_client or get_queue_client()
        self.queue_name = queue_name
        self.session_factory = session_factory
        self.lease_duration_seconds = lease_duration_seconds
        self.semaphore = asyncio.Semaphore(concurrency)
        self._running = False

    async def process_message(self, message: QueueMessage) -> bool:
        """
        Executes a single job message with lease fencing, timeout enforcement,
        and atomic status updates.
        """
        job_id_raw = message.payload.get("job_id")
        if not job_id_raw:
            logger.error(f"Malformed queue message without job_id: {message.payload}")
            await self.queue_client.ack(self.queue_name, message.msg_id)
            return False

        try:
            job_id = uuid.UUID(str(job_id_raw))
        except ValueError:
            logger.error(f"Invalid UUID in queue message: {job_id_raw}")
            await self.queue_client.ack(self.queue_name, message.msg_id)
            return False

        # 1. Acquire execution lease in database
        async with self.session_factory() as session:
            claim_result = await JobRepository.claim_job_lease(
                session=session,
                job_id=job_id,
                worker_id=self.worker_id,
                lease_duration_seconds=self.lease_duration_seconds
            )
            await session.commit()

        if not claim_result:
            # Lease not acquired: another worker claimed the job or state is no longer queued/retry_wait
            logger.info(f"Skipping job {job_id}: lease claim unfulfilled (concurrency fence)")
            # Ack message to avoid queue congestion from redundant deliveries
            await self.queue_client.ack(self.queue_name, message.msg_id)
            return False

        job, lease_token = claim_result
        attempt_number = job.attempt_count
        start_time = time.time()
        start_dt = datetime.now(timezone.utc)

        # 2. Record attempt start
        attempt_id = uuid.uuid4()
        async with self.session_factory() as session:
            attempt = await JobRepository.record_attempt(
                session=session,
                job_id=job_id,
                attempt_number=attempt_number,
                worker_id=self.worker_id,
                lease_token=lease_token,
                status=AttemptStatus.RUNNING,
                started_at=start_dt
            )
            attempt_id = attempt.id
            await session.commit()

        logger.info(
            f"Worker {self.worker_id} started execution for job {job_id} (type: {job.job_type}, attempt {attempt_number}/{job.max_attempts})",
            extra={"job_id": str(job_id), "attempt_id": str(attempt_id), "worker_id": self.worker_id}
        )

        context = ExecutionContext(
            job_id=str(job_id),
            attempt_number=attempt_number,
            worker_id=self.worker_id
        )

        # 3. Execute registered handler under timeout deadline
        success = False
        result_payload = None
        error_info = None

        try:
            handler = get_handler(job.job_type)
            result_payload = await asyncio.wait_for(
                handler(job.payload, context),
                timeout=float(job.timeout_seconds)
            )
            success = True
        except asyncio.TimeoutError:
            error_info = {
                "error_type": "TimeoutError",
                "message": f"Execution deadline exceeded ({job.timeout_seconds} seconds).",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            logger.warning(f"Job {job_id} timed out after {job.timeout_seconds}s")
        except TransientExecutionError as exc:
            error_info = {
                "error_type": "TransientExecutionError",
                "message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            logger.warning(f"Job {job_id} transient error: {exc}")
        except PermanentExecutionError as exc:
            error_info = {
                "error_type": "PermanentExecutionError",
                "message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            logger.error(f"Job {job_id} permanent error: {exc}")
        except Exception as exc:
            error_info = {
                "error_type": exc.__class__.__name__,
                "message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            logger.error(f"Job {job_id} unexpected failure: {exc}", exc_info=True)

        duration_ms = int((time.time() - start_time) * 1000)
        end_dt = datetime.now(timezone.utc)

        # 4. Finalize state
        async with self.session_factory() as session:
            if success:
                # Update attempt
                await JobRepository.update_attempt(
                    session=session,
                    attempt_id=attempt_id,
                    status=AttemptStatus.SUCCEEDED,
                    finished_at=end_dt,
                    duration_ms=duration_ms,
                    result=result_payload
                )
                await JobRepository.complete_job(
                    session=session,
                    job_id=job_id,
                    lease_token=lease_token,
                    result_data=result_payload or {}
                )
                await session.commit()

                # Ack queue message
                await self.queue_client.ack(self.queue_name, message.msg_id)
                logger.info(
                    f"Job {job_id} succeeded in {duration_ms}ms",
                    extra={"job_id": str(job_id), "duration_ms": duration_ms, "worker_id": self.worker_id}
                )
                return True
            else:
                is_transient = error_info["error_type"] in ("TransientExecutionError", "TimeoutError")
                has_attempts_remaining = attempt_number < job.max_attempts
                should_retry = is_transient and has_attempts_remaining

                next_run_at = None
                if should_retry:
                    backoff_delay = calculate_backoff_delay(attempt_number)
                    next_run_at = end_dt + timedelta(seconds=backoff_delay)
                    logger.info(f"Job {job_id} scheduled for retry #{attempt_number + 1} in {backoff_delay}s")

                await JobRepository.update_attempt(
                    session=session,
                    attempt_id=attempt_id,
                    status=AttemptStatus.FAILED,
                    finished_at=end_dt,
                    duration_ms=duration_ms,
                    error_type=error_info["error_type"],
                    error_message=error_info["message"]
                )

                await JobRepository.fail_job_attempt(
                    session=session,
                    job_id=job_id,
                    lease_token=lease_token,
                    error_info=error_info,
                    next_run_at=next_run_at,
                    is_dead_letter=not should_retry
                )
                await session.commit()

                # Acknowledge broker message; if retrying, the scheduler/outbox redelivers at next_run_at
                await self.queue_client.ack(self.queue_name, message.msg_id)
                return False

    async def run_worker_loop(self, poll_interval_seconds: float = 1.0) -> None:
        """Runs the worker continuous message polling loop with concurrency control."""
        self._running = True
        logger.info(f"Worker engine '{self.worker_id}' started with concurrency={self.concurrency}.")

        while self._running:
            try:
                # Read messages up to concurrency limit
                messages = await self.queue_client.read(
                    queue_name=self.queue_name,
                    visibility_timeout_seconds=self.lease_duration_seconds,
                    limit=self.concurrency
                )

                if not messages:
                    await asyncio.sleep(poll_interval_seconds)
                    continue

                tasks = []
                for msg in messages:
                    # Execute each message concurrently up to semaphore limit
                    task = asyncio.create_task(self._process_with_semaphore(msg))
                    tasks.append(task)

                await asyncio.gather(*tasks, return_exceptions=True)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(poll_interval_seconds)

        logger.info(f"Worker engine '{self.worker_id}' stopped gracefully.")

    async def _process_with_semaphore(self, message: QueueMessage) -> None:
        async with self.semaphore:
            await self.process_message(message)

    def stop(self) -> None:
        """Signals worker engine to terminate after active jobs complete."""
        self._running = False

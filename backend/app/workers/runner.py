"""Worker process runner with graceful shutdown and signal handling."""

import asyncio
import signal
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.workers.engine import WorkerEngine
from app.workers.recovery import AbandonedJobRecoveryService
from app.services.outbox_dispatcher import OutboxDispatcher


async def main():
    setup_logging(level="DEBUG" if settings.debug else "INFO")
    logger.info(f"Initializing TaskForge worker process ({settings.worker_id})...")

    worker_engine = WorkerEngine(worker_id=settings.worker_id)
    outbox_dispatcher = OutboxDispatcher()
    recovery_service = AbandonedJobRecoveryService()

    loop = asyncio.get_running_loop()

    def handle_signal():
        logger.info("Termination signal received. Initiating graceful shutdown...")
        worker_engine.stop()
        outbox_dispatcher.stop()
        recovery_service.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            # Signal handlers not implemented on Windows event loop
            pass

    # Run tasks concurrently
    try:
        await asyncio.gather(
            worker_engine.run_worker_loop(poll_interval_seconds=settings.queue_poll_interval_seconds),
            outbox_dispatcher.run_loop(poll_interval_seconds=1.0),
            recovery_service.run_recovery_loop(scan_interval_seconds=5.0)
        )
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("TaskForge worker process successfully terminated.")


if __name__ == "__main__":
    asyncio.run(main())

"""Queue client factory."""

from app.core.config import settings
from app.queue.base import BaseQueueClient
from app.queue.table_queue import TableQueueClient
from app.queue.supabase_pgmq import SupabasePGMQQueueClient

_queue_client_instance: BaseQueueClient | None = None


def get_queue_client() -> BaseQueueClient:
    """Returns the singleton queue client configured for the runtime."""
    global _queue_client_instance
    if _queue_client_instance is None:
        if settings.queue_type.lower() == "pgmq":
            _queue_client_instance = SupabasePGMQQueueClient()
        else:
            _queue_client_instance = TableQueueClient()
    return _queue_client_instance

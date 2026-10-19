"""Abstract base classes and schemas for queue implementations."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class QueueMessage(BaseModel):
    """Normalized message representation across queue broker implementations."""
    msg_id: Union[str, int] = Field(..., description="Unique message identifier in broker")
    queue_name: str
    payload: Dict[str, Any]
    read_count: int = 1
    enqueued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    visible_at: Optional[datetime] = None


class BaseQueueClient(ABC):
    """Abstract interface defining queue operations for TaskForge."""

    @abstractmethod
    async def initialize_queue(self, queue_name: str) -> None:
        """Ensures the queue exists and is ready for message delivery."""
        pass

    @abstractmethod
    async def send(
        self,
        queue_name: str,
        message: Dict[str, Any],
        delay_seconds: int = 0
    ) -> Union[str, int]:
        """Publishes a message to the queue with optional delay."""
        pass

    @abstractmethod
    async def read(
        self,
        queue_name: str,
        visibility_timeout_seconds: int = 60,
        limit: int = 1
    ) -> List[QueueMessage]:
        """
        Retrieves up to `limit` available messages and hides them
        for `visibility_timeout_seconds` (at-least-once lease).
        """
        pass

    @abstractmethod
    async def ack(self, queue_name: str, msg_id: Union[str, int]) -> bool:
        """Acknowledges and deletes/archives the processed message from the queue."""
        pass

    @abstractmethod
    async def nack(
        self,
        queue_name: str,
        msg_id: Union[str, int],
        delay_seconds: int = 0
    ) -> bool:
        """Negative acknowledgement: releases the message back to queue with optional delay."""
        pass

    @abstractmethod
    async def get_depth(self, queue_name: str) -> int:
        """Returns the current number of pending/visible messages in the queue."""
        pass

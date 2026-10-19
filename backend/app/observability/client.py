"""Decoupled Elasticsearch client with circuit breaker and bounded memory buffer."""

import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from elasticsearch import AsyncElasticsearch

from app.core.config import settings
from app.core.logging import logger


class ElasticsearchObservabilityClient:
    """
    Decoupled log streamer for Elasticsearch.
    Uses an in-memory bounded ring buffer and a circuit breaker so that Elasticsearch
    downtime or network partitions NEVER block worker execution or crash processes.
    """

    def __init__(
        self,
        url: str = settings.elasticsearch_url,
        api_key: Optional[str] = settings.elasticsearch_api_key,
        index_prefix: str = settings.elasticsearch_index_prefix,
        enabled: bool = settings.elasticsearch_enabled,
        max_buffer_size: int = 5000
    ):
        self.url = url
        self.api_key = api_key
        self.index_prefix = index_prefix
        self.enabled = enabled and bool(url)
        self.buffer: deque[Dict[str, Any]] = deque(maxlen=max_buffer_size)

        # Circuit breaker state
        self._circuit_open = False
        self._consecutive_failures = 0
        self._last_failure_time: Optional[float] = None
        self._cooldown_seconds = 30.0

        self.es_client: Optional[AsyncElasticsearch] = None
        if self.enabled:
            kwargs = {"hosts": [self.url]}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            try:
                self.es_client = AsyncElasticsearch(**kwargs)
            except Exception as e:
                logger.warning(f"Failed to initialize Elasticsearch client: {e}")
                self.es_client = None

    def record_event(
        self,
        level: str,
        message: str,
        job_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
        worker_id: Optional[str] = None,
        event_type: Optional[str] = None,
        duration_ms: Optional[int] = None,
        error_type: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Records an execution log event into the bounded buffer and schedules non-blocking indexing.
        """
        event: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "service": "taskforge-worker",
            "environment": settings.app_env,
            "message": message,
        }
        if job_id:
            event["job_id"] = str(job_id)
        if attempt_id:
            event["attempt_id"] = str(attempt_id)
        if worker_id:
            event["worker_id"] = str(worker_id)
        if event_type:
            event["event_type"] = event_type
        if duration_ms is not None:
            event["duration_ms"] = duration_ms
        if error_type:
            event["error_type"] = error_type
        if extra:
            event["data"] = extra

        # Append to bounded local buffer (always succeeds)
        self.buffer.append(event)

        # Trigger non-blocking async indexing if enabled and circuit is closed
        if self.enabled and self.es_client and not self._is_circuit_open():
            asyncio.create_task(self._index_single_event(event))

        return event

    async def _index_single_event(self, event: Dict[str, Any]) -> None:
        """Asynchronously indexes a single event with circuit breaker protection."""
        if not self.es_client:
            return

        date_suffix = datetime.now(timezone.utc).strftime("%Y.%m")
        index_name = f"{self.index_prefix}-{date_suffix}"

        try:
            await self.es_client.index(index=index_name, document=event)
            self._consecutive_failures = 0
            self._circuit_open = False
        except Exception as exc:
            self._consecutive_failures += 1
            logger.warning(
                f"Elasticsearch indexing failed ({self._consecutive_failures} consecutive failures): {exc}"
            )
            if self._consecutive_failures >= 3:
                import time
                self._circuit_open = True
                self._last_failure_time = time.time()
                logger.error("Elasticsearch circuit breaker tripped OPEN. Suppressing index calls for cooldown.")

    def _is_circuit_open(self) -> bool:
        """Checks if circuit breaker is open or cooling down."""
        if not self._circuit_open:
            return False
        import time
        if self._last_failure_time and (time.time() - self._last_failure_time > self._cooldown_seconds):
            # Attempt trial recovery
            self._circuit_open = False
            return False
        return True

    async def search_logs(
        self,
        job_id: str,
        attempt_id: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieves logs for a job.
        If Elasticsearch is connected, queries the index.
        Otherwise falls back to matching buffered events in memory.
        """
        # 1. Try Elasticsearch query if available
        if self.enabled and self.es_client and not self._is_circuit_open():
            try:
                must_clauses: List[Dict[str, Any]] = [{"term": {"job_id.keyword": job_id}}]
                if attempt_id:
                    must_clauses.append({"term": {"attempt_id.keyword": attempt_id}})
                if level:
                    must_clauses.append({"term": {"level.keyword": level.upper()}})

                query = {"bool": {"must": must_clauses}}
                res = await self.es_client.search(
                    index=f"{self.index_prefix}-*",
                    query=query,
                    size=limit,
                    sort=[{"timestamp": {"order": "asc"}}]
                )
                hits = res.get("hits", {}).get("hits", [])
                if hits:
                    return [hit["_source"] for hit in hits]
            except Exception as e:
                logger.warning(f"Elasticsearch search failed, falling back to local buffer: {e}")

        # 2. Local bounded buffer fallback
        matched = []
        for ev in reversed(self.buffer):
            if ev.get("job_id") == str(job_id):
                if attempt_id and ev.get("attempt_id") != str(attempt_id):
                    continue
                if level and ev.get("level") != level.upper():
                    continue
                matched.append(ev)
                if len(matched) >= limit:
                    break

        return list(reversed(matched))


# Global singleton instance
es_observability = ElasticsearchObservabilityClient()

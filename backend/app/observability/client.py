"""Decoupled Elasticsearch client with circuit breaker, bounded memory buffer, and aggregations."""

import asyncio
from collections import deque, Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from elasticsearch import AsyncElasticsearch

from app.core.config import settings
from app.core.logging import logger
from app.ai.sanitizer import sanitize_text, sanitize_payload


class ElasticsearchObservabilityClient:
    """
    Decoupled log streamer and analytics engine for Elasticsearch.
    Uses an in-memory bounded ring buffer and a circuit breaker so that Elasticsearch
    downtime or network partitions NEVER block worker execution or crash processes.
    Automatically redacts sensitive secrets from log payloads before indexing.
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
            kwargs: Dict[str, Any] = {"hosts": [self.url]}
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
        job_type: Optional[str] = None,
        event_type: Optional[str] = None,
        duration_ms: Optional[int] = None,
        error_type: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Records an execution log event into the bounded buffer and schedules non-blocking indexing.
        Redacts credentials, secrets, and authorization tokens prior to storage.
        """
        # 1. Sanitize text and dictionary payloads to prevent secret leakage
        clean_message = sanitize_text(message)
        clean_extra = sanitize_payload(extra) if extra else None

        event: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "log_level": level.upper(),
            "service": "taskforge-worker",
            "environment": settings.app_env,
            "message": clean_message,
        }
        if job_id:
            event["job_id"] = str(job_id)
        if attempt_id:
            event["attempt_id"] = str(attempt_id)
        if worker_id:
            event["worker_id"] = str(worker_id)
        if job_type:
            event["job_type"] = str(job_type)
        if event_type:
            event["event_type"] = event_type
        if duration_ms is not None:
            event["duration_ms"] = duration_ms
        if error_type:
            event["error_type"] = error_type
        if clean_extra:
            event["data"] = clean_extra

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
        job_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
        level: Optional[str] = None,
        job_type: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieves logs with optional filters.
        If Elasticsearch is connected, queries the index.
        Otherwise falls back to matching buffered events in memory.
        """
        # 1. Try Elasticsearch query if available
        if self.enabled and self.es_client and not self._is_circuit_open():
            try:
                must_clauses: List[Dict[str, Any]] = []
                if job_id:
                    must_clauses.append({"term": {"job_id.keyword": str(job_id)}})
                if attempt_id:
                    must_clauses.append({"term": {"attempt_id.keyword": str(attempt_id)}})
                if level:
                    must_clauses.append({"term": {"level.keyword": level.upper()}})
                if job_type:
                    must_clauses.append({"term": {"job_type.keyword": job_type}})
                if event_type:
                    must_clauses.append({"term": {"event_type.keyword": event_type}})

                query = {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}
                res = await self.es_client.search(
                    index=f"{self.index_prefix}-*",
                    query=query,
                    size=limit,
                    sort=[{"timestamp": {"order": "desc"}}]
                )
                hits = res.get("hits", {}).get("hits", [])
                if hits:
                    return list(reversed([hit["_source"] for hit in hits]))
            except Exception as e:
                logger.warning(f"Elasticsearch search failed, falling back to local buffer: {e}")

        # 2. Local bounded buffer fallback
        matched = []
        for ev in reversed(self.buffer):
            if job_id and ev.get("job_id") != str(job_id):
                continue
            if attempt_id and ev.get("attempt_id") != str(attempt_id):
                continue
            if level and ev.get("level") != level.upper():
                continue
            if job_type and ev.get("job_type") != job_type:
                continue
            if event_type and ev.get("event_type") != event_type:
                continue

            matched.append(ev)
            if len(matched) >= limit:
                break

        return list(reversed(matched))

    async def get_failure_patterns(self) -> Dict[str, Any]:
        """
        Analyzes failure patterns and duration aggregations using Elasticsearch aggregations
        or bounded ring buffer telemetry.
        """
        # 1. Try Elasticsearch aggregations
        if self.enabled and self.es_client and not self._is_circuit_open():
            try:
                agg_body = {
                    "error_patterns": {
                        "terms": {"field": "error_type.keyword", "size": 10}
                    },
                    "job_types_failing": {
                        "filter": {"term": {"level.keyword": "ERROR"}},
                        "aggs": {
                            "by_type": {"terms": {"field": "job_type.keyword", "size": 10}}
                        }
                    },
                    "retry_events": {
                        "filter": {"term": {"event_type.keyword": "JOB_ATTEMPT_RETRYING"}}
                    },
                    "timeout_events": {
                        "filter": {"term": {"error_type.keyword": "TimeoutError"}}
                    },
                    "duration_stats": {
                        "stats": {"field": "duration_ms"}
                    }
                }
                res = await self.es_client.search(
                    index=f"{self.index_prefix}-*",
                    query={"match_all": {}},
                    size=0,
                    aggregations=agg_body
                )
                aggs = res.get("aggregations", {})

                error_buckets = aggs.get("error_patterns", {}).get("buckets", [])
                failing_types = aggs.get("job_types_failing", {}).get("by_type", {}).get("buckets", [])
                retry_count = aggs.get("retry_events", {}).get("doc_count", 0)
                timeout_count = aggs.get("timeout_events", {}).get("doc_count", 0)
                dur_stats = aggs.get("duration_stats", {})

                return {
                    "source": "elasticsearch",
                    "top_error_patterns": [
                        {"error_type": b["key"], "count": b["doc_count"]} for b in error_buckets
                    ],
                    "failures_by_job_type": [
                        {"job_type": b["key"], "count": b["doc_count"]} for b in failing_types
                    ],
                    "total_retries_observed": retry_count,
                    "total_timeouts_observed": timeout_count,
                    "duration_metrics": {
                        "count": dur_stats.get("count", 0),
                        "avg_ms": round(dur_stats.get("avg") or 0.0, 2),
                        "min_ms": dur_stats.get("min") or 0.0,
                        "max_ms": dur_stats.get("max") or 0.0,
                    }
                }
            except Exception as e:
                logger.warning(f"Elasticsearch aggregation failed, falling back to buffer analysis: {e}")

        # 2. Local buffer fallback aggregation
        error_counter: Counter[str] = Counter()
        job_type_failure_counter: Counter[str] = Counter()
        retries = 0
        timeouts = 0
        durations: List[int] = []

        for ev in self.buffer:
            if ev.get("error_type"):
                error_counter[ev["error_type"]] += 1
            if ev.get("level") == "ERROR" and ev.get("job_type"):
                job_type_failure_counter[ev["job_type"]] += 1
            if ev.get("event_type") == "JOB_ATTEMPT_RETRYING":
                retries += 1
            if ev.get("error_type") == "TimeoutError":
                timeouts += 1
            if ev.get("duration_ms") is not None:
                durations.append(ev["duration_ms"])

        avg_dur = round(sum(durations) / len(durations), 2) if durations else 0.0
        min_dur = min(durations) if durations else 0.0
        max_dur = max(durations) if durations else 0.0

        return {
            "source": "in_memory_buffer",
            "top_error_patterns": [
                {"error_type": k, "count": v} for k, v in error_counter.most_common(10)
            ],
            "failures_by_job_type": [
                {"job_type": k, "count": v} for k, v in job_type_failure_counter.most_common(10)
            ],
            "total_retries_observed": retries,
            "total_timeouts_observed": timeouts,
            "duration_metrics": {
                "count": len(durations),
                "avg_ms": avg_dur,
                "min_ms": min_dur,
                "max_ms": max_dur,
            }
        }


# Global singleton instance
es_observability = ElasticsearchObservabilityClient()

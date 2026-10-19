"""AI-assisted Failure Investigation Service."""

import json
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.investigation import JobInvestigation
from app.models.job import Job
from app.ai.schemas import InvestigationReport
from app.ai.sanitizer import sanitize_payload, sanitize_text


class FailureInvestigatorService:
    """
    Advisory failure investigator.
    Analyzes job metadata, attempt histories, and structured logs to produce
    grounded, validated root-cause analysis reports.
    """

    @staticmethod
    def generate_grounded_analysis(
        job: Job,
        attempts: List[Any],
        logs: List[Dict[str, Any]]
    ) -> InvestigationReport:
        """
        Generates deterministic, evidence-grounded investigation report
        analyzing the real captured errors, durations, and retry counts.
        """
        last_error = job.last_error or {}
        error_type = last_error.get("error_type", "UnknownError")
        error_message = last_error.get("message", "No specific error message recorded.")
        attempt_count = job.attempt_count

        evidence: List[str] = [
            f"Job {job.id} reached terminal state '{job.status}' after {attempt_count}/{job.max_attempts} attempts.",
            f"Last recorded error: [{error_type}] {error_message}"
        ]
        references: List[str] = [f"Job ID: {job.id}", f"Attempts logged: {len(attempts)}"]

        for idx, att in enumerate(attempts, 1):
            att_dict = att.to_dict() if hasattr(att, "to_dict") else att
            evidence.append(
                f"Attempt #{att_dict.get('attempt_number', idx)} on worker '{att_dict.get('worker_id')}': "
                f"Status={att_dict.get('status')}, Duration={att_dict.get('duration_ms')}ms"
            )
            references.append(f"Attempt #{idx} ID: {att_dict.get('id')}")

        for log in logs[-5:]:
            msg = log.get("message", "")
            evidence.append(f"Structured Log [{log.get('level')}]: {msg}")

        # Diagnosis logic based on actual evidence
        if "timeout" in error_type.lower() or "timeouterror" in error_type.lower():
            probable_cause = f"The job exceeded its configured execution deadline of {job.timeout_seconds} seconds."
            alternatives = [
                "Underlying external service response latency spike.",
                "Unusually large input payload or database lock contention during processing."
            ]
            recommendations = [
                f"Increase `timeout_seconds` beyond {job.timeout_seconds}s if this job workload naturally requires more time.",
                "Inspect worker thread allocation and external API endpoint latency."
            ]
            confidence = "high"
        elif "permanent" in error_type.lower() or "poison" in job.job_type.lower():
            probable_cause = "Non-retryable payload or schema validation failure (Poison Pill)."
            alternatives = [
                "Malformed request parameters submitted by caller.",
                "Incompatible data format rejected by the registered task handler."
            ]
            recommendations = [
                "Inspect client submission payload for invalid field values.",
                "Do NOT perform automated blind retries; fix input schema before re-submitting."
            ]
            confidence = "high"
        elif "transient" in error_type.lower() or attempt_count > 1:
            probable_cause = "Transient network, upstream rate-limit, or connection timeout."
            alternatives = [
                "Temporary third-party service degradation.",
                "Short-lived database connection pool exhaustion."
            ]
            recommendations = [
                "Verify upstream service availability and health dashboard.",
                "The system backoff policy will handle transient recovery; check queue visibility if repeated."
            ]
            confidence = "medium"
        else:
            probable_cause = f"Execution interrupted by {error_type}."
            alternatives = [
                "Worker process crash or unhandled runtime exception.",
                "Resource exhaustion on execution host."
            ]
            recommendations = [
                "Review worker stack traces and system metrics.",
                "Verify memory limits on worker container nodes."
            ]
            confidence = "medium"

        return InvestigationReport(
            summary=f"Analysis of {job.job_type} failure (Status: {job.status}). Root cause attributed to {error_type}.",
            probable_root_cause=probable_cause,
            supporting_evidence=evidence,
            evidence_references=references,
            alternative_explanations=alternatives,
            recommended_next_steps=recommendations,
            confidence_level=confidence,
            uncertainty_or_missing_evidence=None if logs else "No Elasticsearch structured logs were captured for this job."
        )

    @classmethod
    async def investigate_job(
        cls,
        session: AsyncSession,
        job: Job,
        attempts: List[Any],
        logs: List[Dict[str, Any]]
    ) -> JobInvestigation:
        """
        Executes bounded, read-only AI investigation and persists report in database.
        Uses CrewAI multi-agent investigation workflow with grounded engine fallback.
        """
        # 1. Sanitize untrusted inputs (payload and logs)
        clean_payload = sanitize_payload(job.payload)
        clean_logs = [
            {**log, "message": sanitize_text(log.get("message", ""))}
            for log in logs
        ]

        # 2. Execute LLM investigation: NVIDIA NIM -> CrewAI -> Grounded Engine Fallback
        from app.ai.crewai_investigator import CrewAIFailureInvestigator

        report = None
        provider_name = "grounded-evidence-engine"

        # Try NVIDIA NIM LLM endpoint first if configured
        if settings.llm_provider in ("nvidia", "openai") and settings.llm_api_key:
            report = CrewAIFailureInvestigator.run_nvidia_investigation(
                job=job,
                attempts=attempts,
                clean_logs=clean_logs,
                clean_payload=clean_payload
            )
            if report:
                provider_name = f"nvidia-nim ({settings.llm_model})"

        # Try CrewAI multi-agent workflow
        if not report:
            report = CrewAIFailureInvestigator.run_crewai_investigation(
                job=job,
                attempts=attempts,
                logs=logs,
                clean_payload=clean_payload,
                clean_logs=clean_logs
            )
            if report:
                provider_name = "crewai"

        # Deterministic grounded evidence fallback
        if not report:
            report = CrewAIFailureInvestigator.generate_grounded_investigation(
                job=job,
                attempts=attempts,
                clean_logs=clean_logs
            )
            provider_name = "grounded-evidence-engine"


        # 3. Persist investigation report to database
        investigation = JobInvestigation(
            id=uuid.uuid4(),
            job_id=job.id,
            report=report.model_dump(),
            provider=provider_name
        )
        session.add(investigation)
        await session.commit()
        await session.refresh(investigation)

        return investigation

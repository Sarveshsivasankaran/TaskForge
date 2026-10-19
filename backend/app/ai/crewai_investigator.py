"""CrewAI-powered AI Failure Investigation Architecture.

Defines a multi-agent investigation system using CrewAI:
- Agent 1: Cloud Reliability Investigator (analyzes errors, stack traces, and logs)
- Agent 2: Evidence & Safety Auditor (verifies hypotheses against facts, flags insufficient evidence, ensures recommendations are safe)

Adheres strictly to safety constraints:
- Advisory only: No automatic operational mutations or retry bypass.
- Strictly read-only: No arbitrary command or query execution.
- Untrusted inputs sanitized prior to ingestion.
- Structured schema validation using Pydantic.
- Graceful deterministic fallback when CrewAI or external LLM API is unavailable.
"""

import json
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import logger
from app.models.job import Job
from app.ai.schemas import InvestigationReport
from app.ai.sanitizer import sanitize_payload, sanitize_text


class CrewAIFailureInvestigator:
    """Multi-agent and LLM failure investigation service powered by CrewAI and NVIDIA NIM."""

    @classmethod
    def run_nvidia_investigation(
        cls,
        job: Job,
        attempts: List[Any],
        clean_logs: List[Dict[str, Any]],
        clean_payload: Dict[str, Any]
    ) -> Optional[InvestigationReport]:
        """
        Executes root cause investigation using NVIDIA NIM OpenAI-compatible endpoint.
        Extracts reasoning_content when available.
        """
        if not settings.llm_api_key or settings.llm_provider not in ("nvidia", "openai"):
            return None

        try:
            from openai import OpenAI
            client = OpenAI(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                timeout=30.0
            )

            prompt = (
                f"You are a Senior Cloud Reliability Engineer diagnosing a background job failure in TaskForge.\n\n"
                f"Job Metadata:\n"
                f"- Job ID: {job.id}\n"
                f"- Job Type: {job.job_type}\n"
                f"- Terminal Status: {job.status}\n"
                f"- Attempts: {job.attempt_count}/{job.max_attempts}\n"
                f"- Timeout: {job.timeout_seconds} seconds\n"
                f"- Last Error: {json.dumps(job.last_error or {})}\n"
                f"- Payload: {json.dumps(clean_payload)}\n"
                f"- Recent Execution Logs: {json.dumps(clean_logs[-6:])}\n\n"
                f"Respond with a valid JSON object matching this schema:\n"
                f"{{\n"
                f'  "summary": "Concise summary of why the job failed",\n'
                f'  "probable_root_cause": "Detailed technical root cause",\n'
                f'  "supporting_evidence": ["Fact from attempts/logs", "Fact 2"],\n'
                f'  "evidence_references": ["Job ID or Attempt ID reference"],\n'
                f'  "alternative_explanations": ["Alternative possible reason"],\n'
                f'  "recommended_next_steps": ["Actionable step 1 for operator", "Actionable step 2"],\n'
                f'  "confidence_level": "high",\n'
                f'  "uncertainty_or_missing_evidence": null\n'
                f"}}"
            )

            completion = client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2048,
                stream=False
            )

            reasoning = getattr(completion.choices[0].message, "reasoning_content", None)
            if reasoning:
                logger.info(f"NVIDIA NIM Investigation reasoning: {reasoning[:120]}...")

            content = completion.choices[0].message.content or ""
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            return InvestigationReport.model_validate(parsed)
        except Exception as exc:
            logger.warning(f"NVIDIA NIM investigation error: {exc}. Utilizing grounded fallback.")
            return None

    @classmethod
    def run_crewai_investigation(
        cls,
        job: Job,
        attempts: List[Any],
        logs: List[Dict[str, Any]],
        clean_payload: Dict[str, Any],
        clean_logs: List[Dict[str, Any]]
    ) -> Optional[InvestigationReport]:
        """
        Attempts to execute multi-agent investigation using the CrewAI framework.
        Returns None if CrewAI is not installed or API key is not configured.
        """
        try:
            from crewai import Agent, Crew, Process, Task
        except ImportError:
            logger.info("CrewAI library not installed; utilizing grounded evidence engine.")
            return None

        if not settings.llm_api_key or settings.llm_provider == "mock":
            logger.info("LLM API key not configured; utilizing grounded evidence engine.")
            return None

        try:
            # 1. Define Agent 1: Cloud Reliability Investigator
            investigator_agent = Agent(
                role="Senior Cloud Reliability Engineer",
                goal="Investigate asynchronous job failure reasons from sanitized logs and execution traces",
                backstory=(
                    "You are a principal engineer specializing in distributed systems reliability, "
                    "poison pill detection, network timeouts, and concurrency deadlocks. "
                    "You only formulate hypotheses strictly supported by captured error traces."
                ),
                verbose=False,
                allow_delegation=False,
            )

            # 2. Define Agent 2: Evidence & Safety Auditor
            auditor_agent = Agent(
                role="Evidence Verification and Safety Auditor",
                goal="Audit the root-cause diagnosis against actual execution logs and confirm evidence sufficiency",
                backstory=(
                    "You are a rigorous verification specialist. You cross-reference hypotheses with "
                    "actual attempt numbers, timestamps, and error messages. If evidence is lacking or ambiguous, "
                    "you explicitly flag confidence as 'insufficient_evidence'. You ensure all remediation advice "
                    "is advisory, non-destructive, and requires human operator confirmation."
                ),
                verbose=False,
                allow_delegation=False,
            )

            # 3. Formulate Investigation Tasks
            evidence_context = json.dumps({
                "job_id": str(job.id),
                "job_type": job.job_type,
                "status": job.status,
                "attempt_count": job.attempt_count,
                "max_attempts": job.max_attempts,
                "timeout_seconds": job.timeout_seconds,
                "last_error": job.last_error,
                "payload_sample": clean_payload,
                "recent_logs": clean_logs[-8:]
            }, indent=2)

            task_analyze = Task(
                description=(
                    f"Analyze the asynchronous job failure from the following evidence:\n{evidence_context}\n"
                    "Determine observed facts and identify the most probable root cause."
                ),
                expected_output="Detailed breakdown of failure cause, observed errors, and log evidence.",
                agent=investigator_agent,
            )

            task_audit_and_report = Task(
                description=(
                    "Review the findings from the reliability investigator. Verify each claim against the evidence.\n"
                    "Generate a structured JSON output with the exact keys:\n"
                    "- summary (string)\n"
                    "- probable_root_cause (string)\n"
                    "- supporting_evidence (list of strings)\n"
                    "- evidence_references (list of strings)\n"
                    "- alternative_explanations (list of strings)\n"
                    "- recommended_next_steps (list of strings)\n"
                    "- confidence_level ('high', 'medium', 'low', or 'insufficient_evidence')\n"
                    "- uncertainty_or_missing_evidence (string or null)\n"
                ),
                expected_output="Valid JSON matching the InvestigationReport schema.",
                agent=auditor_agent,
                output_json=InvestigationReport,
            )

            # 4. Assemble and execute Crew
            crew = Crew(
                agents=[investigator_agent, auditor_agent],
                tasks=[task_analyze, task_audit_and_report],
                process=Process.sequential,
                verbose=False
            )

            crew_output = crew.kickoff()
            if hasattr(crew_output, "json_dict") and crew_output.json_dict:
                return InvestigationReport.model_validate(crew_output.json_dict)
            elif hasattr(crew_output, "raw"):
                raw_text = crew_output.raw
                # Extract JSON if enclosed in markdown code fence
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()
                data = json.loads(raw_text)
                return InvestigationReport.model_validate(data)

        except Exception as exc:
            logger.warning(f"CrewAI execution failed: {exc}. Falling back to deterministic grounded engine.")

        return None

    @classmethod
    def generate_grounded_investigation(
        cls,
        job: Job,
        attempts: List[Any],
        clean_logs: List[Dict[str, Any]]
    ) -> InvestigationReport:
        """
        Deterministic, multi-stage evidence-grounded investigation engine.
        Acts as the reference implementation and fallback when external LLM is offline.
        """
        last_error = job.last_error or {}
        error_type = last_error.get("error_type") or "UnknownError"
        error_message = last_error.get("message") or "No explicit error message captured."
        attempt_count = job.attempt_count or len(attempts)

        # Factual evidence grounded directly in execution history
        evidence: List[str] = [
            f"Job {job.id} reached terminal state '{job.status}' after {attempt_count}/{job.max_attempts} attempts.",
            f"Primary failure signature: [{error_type}] {error_message}"
        ]
        references: List[str] = [
            f"Job ID: {job.id}",
            f"Total Attempts Logged: {len(attempts)}"
        ]

        # Extract attempt-specific traces
        for idx, att in enumerate(attempts, 1):
            att_dict = att.to_dict() if hasattr(att, "to_dict") else att
            dur = att_dict.get("duration_ms")
            dur_str = f"{dur}ms" if dur is not None else "N/A"
            worker = att_dict.get("worker_id") or "worker-unknown"
            st = att_dict.get("status") or "failed"
            evidence.append(
                f"Attempt #{att_dict.get('attempt_number', idx)} on '{worker}': Status={st}, Duration={dur_str}"
            )
            references.append(f"Attempt #{idx} ID: {att_dict.get('id')}")

        # Correlated Elasticsearch logs
        for log in clean_logs[-5:]:
            msg = log.get("message", "")
            lvl = log.get("level", "INFO")
            evidence.append(f"Structured Log [{lvl}]: {msg}")

        # Insufficient evidence check: if no error was logged and no attempts failed
        if error_type == "UnknownError" and not attempts and not clean_logs:
            return InvestigationReport(
                summary=f"Insufficient telemetry to diagnose failure for job {job.id}.",
                probable_root_cause="Diagnostic logs and attempt records are unavailable for this execution.",
                supporting_evidence=evidence,
                evidence_references=references,
                alternative_explanations=[
                    "The job was prematurely cancelled or deleted from the queue broker before worker acquisition.",
                    "Log buffer reached maximum capacity or Elasticsearch connection was interrupted."
                ],
                recommended_next_steps=[
                    "Verify worker connectivity and Elasticsearch pipeline ingestion.",
                    "Check system health and queue message retention settings."
                ],
                confidence_level="insufficient_evidence",
                uncertainty_or_missing_evidence="No worker attempt records or correlated Elasticsearch log documents were found."
            )

        # Multi-factor grounded root cause analysis
        err_lower = error_type.lower()
        msg_lower = error_message.lower()

        if "timeout" in err_lower or "timeouterror" in err_lower or "timeout" in msg_lower:
            probable_cause = (
                f"Execution deadline exceeded: the task ran longer than the configured "
                f"timeout limit of {job.timeout_seconds} seconds."
            )
            alternatives = [
                "Upstream dependency or downstream database latency spike during processing.",
                "Unbounded input payload size causing CPU or network starvation.",
                "Thread contention or deadlocked async coroutine within registered handler."
            ]
            recommendations = [
                f"Evaluate workload size and consider increasing `timeout_seconds` beyond {job.timeout_seconds}s if expected.",
                "Inspect worker CPU/memory saturation metrics and external API response times.",
                "Check for unreleased database locks or synchronous blocking calls in worker threads."
            ]
            confidence = "high"
            uncertainty = None
        elif "permanent" in err_lower or "poison" in job.job_type.lower() or "validation" in msg_lower:
            probable_cause = "Non-retryable poison pill: payload failed schema validation or business rule."
            alternatives = [
                "Malformed request parameters submitted by upstream client application.",
                "Incompatible schema version between job submitter and worker task registry."
            ]
            recommendations = [
                "Do NOT perform automated retry; verify payload fields match handler schema.",
                "Sanitize and correct client submission parameters before resubmission.",
                "Verify API payload contract matches registered worker task handler."
            ]
            confidence = "high"
            uncertainty = None
        elif "transient" in err_lower or "connection" in msg_lower or "network" in msg_lower:
            probable_cause = "Transient network partition, connection timeout, or upstream rate limit."
            alternatives = [
                "Temporary database connection pool exhaustion under concurrent load.",
                "Intermittent HTTP 429 or 503 response from external third-party service."
            ]
            recommendations = [
                "Verify upstream service availability and connection pool capacity.",
                "TaskForge exponential backoff policy will handle transient recovery on retry.",
                "Check broker visibility timeout is sufficient for backoff delay intervals."
            ]
            confidence = "medium"
            uncertainty = None
        elif "abandoned" in err_lower or "lease" in msg_lower:
            probable_cause = "Worker heartbeat timeout or worker host crash while holding execution lease."
            alternatives = [
                "Worker node terminated abruptly (OOM killer or container restart).",
                "Severe network partition preventing worker from renewing lease token."
            ]
            recommendations = [
                "Inspect worker host memory consumption and kernel crash logs.",
                "Verify network connectivity between worker nodes and Supabase PostgreSQL."
            ]
            confidence = "high"
            uncertainty = None
        else:
            probable_cause = f"Execution interrupted by unhandled runtime exception: {error_type}."
            alternatives = [
                "Unhandled edge-case in job business logic.",
                "Missing environment variable or configuration on the assigned worker host."
            ]
            recommendations = [
                "Review worker stack traces in Elasticsearch for line-level traceback.",
                "Verify environment variables and dependencies across all worker nodes."
            ]
            confidence = "medium"
            uncertainty = "Full traceback may require inspection of raw worker stderr logs."

        if not clean_logs:
            uncertainty = (uncertainty or "") + " Note: No correlated Elasticsearch logs were found; diagnosis is based on database attempt metadata."

        return InvestigationReport(
            summary=f"Failure investigation for {job.job_type} job (Status: {job.status}). Root cause attributed to {error_type}.",
            probable_root_cause=probable_cause,
            supporting_evidence=evidence,
            evidence_references=references,
            alternative_explanations=alternatives,
            recommended_next_steps=recommendations,
            confidence_level=confidence,
            uncertainty_or_missing_evidence=uncertainty.strip() if uncertainty else None
        )

"""Pydantic schemas for AI failure investigation reports."""

from typing import List, Optional
from pydantic import BaseModel, Field


class InvestigationReport(BaseModel):
    """
    Structured AI failure analysis report.
    Adheres to strict schema guardrails: advisory only, evidence-grounded, no executable actions.
    """
    summary: str = Field(..., description="High-level diagnostic summary of the job failure")
    probable_root_cause: str = Field(..., description="Most probable root cause identified from evidence")
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Factual observations extracted directly from execution logs and attempt records"
    )
    evidence_references: List[str] = Field(
        default_factory=list,
        description="Specific attempt numbers, timestamps, or error codes supporting the diagnosis"
    )
    alternative_explanations: List[str] = Field(
        default_factory=list,
        description="Other plausible factors or environmental hypotheses"
    )
    recommended_next_steps: List[str] = Field(
        default_factory=list,
        description="Human operator remediation recommendations (advisory only)"
    )
    confidence_level: str = Field(
        default="medium",
        description="Confidence assessment: 'high', 'medium', 'low', or 'insufficient_evidence'"
    )
    uncertainty_or_missing_evidence: Optional[str] = Field(
        default=None,
        description="Documentation of any ambiguities, missing logs, or unconfirmed assumptions"
    )

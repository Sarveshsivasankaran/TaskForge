"""Job lifecycle statuses and transition validation rules."""

from enum import Enum
from typing import Dict, Set


class JobStatus(str, Enum):
    """Authoritative states in the TaskForge job lifecycle."""
    QUEUED = "queued"
    RUNNING = "running"
    RETRY_WAIT = "retry_wait"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


class AttemptStatus(str, Enum):
    """Execution status for an individual job attempt."""
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"


# State transition graph
# Normal automated transitions
NORMAL_TRANSITIONS: Dict[JobStatus, Set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING: {
        JobStatus.SUCCEEDED,
        JobStatus.RETRY_WAIT,
        JobStatus.FAILED,
        JobStatus.DEAD_LETTER,
        JobStatus.CANCELLED,
    },
    JobStatus.RETRY_WAIT: {JobStatus.QUEUED, JobStatus.CANCELLED},
    JobStatus.SUCCEEDED: set(),  # Terminal state
    JobStatus.FAILED: set(),     # Terminal without manual retry
    JobStatus.DEAD_LETTER: set(), # Terminal without manual retry
    JobStatus.CANCELLED: set(),  # Terminal state
}

# Transitions permitted ONLY through an explicit, authorized manual retry operation
MANUAL_RETRY_TRANSITIONS: Dict[JobStatus, Set[JobStatus]] = {
    JobStatus.FAILED: {JobStatus.QUEUED},
    JobStatus.DEAD_LETTER: {JobStatus.QUEUED},
    JobStatus.CANCELLED: {JobStatus.QUEUED},
}


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal lifecycle transition is attempted."""
    def __init__(self, current_state: str, new_state: str, reason: str = ""):
        msg = f"Invalid job state transition from '{current_state}' to '{new_state}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)
        self.current_state = current_state
        self.new_state = new_state


def validate_job_state_transition(
    current_status: JobStatus | str,
    new_status: JobStatus | str,
    is_manual_retry: bool = False
) -> None:
    """
    Validates whether a transition from current_status to new_status is allowed.
    Raises InvalidStateTransitionError if illegal.
    """
    try:
        curr = JobStatus(current_status)
        target = JobStatus(new_status)
    except ValueError as e:
        raise InvalidStateTransitionError(str(current_status), str(new_status), f"Unrecognized status enum: {e}")

    # No-op transition is permitted
    if curr == target:
        return

    allowed = NORMAL_TRANSITIONS.get(curr, set())
    if target in allowed:
        return

    if is_manual_retry:
        manual_allowed = MANUAL_RETRY_TRANSITIONS.get(curr, set())
        if target in manual_allowed:
            return

    raise InvalidStateTransitionError(
        curr.value,
        target.value,
        f"Allowed targets from '{curr.value}' are {[s.value for s in allowed]}" +
        (f" (or {[s.value for s in MANUAL_RETRY_TRANSITIONS.get(curr, set())]} via manual retry)" if not is_manual_retry else "")
    )

"""Exponential backoff calculation with randomized jitter."""

import random
from app.core.config import settings


def calculate_backoff_delay(
    attempt_number: int,
    base_delay: float = settings.retry_base_delay_seconds,
    max_delay: float = settings.retry_max_delay_seconds,
    jitter_factor: float = 0.5
) -> float:
    """
    Computes exponential backoff with full randomized jitter to prevent thundering herds:
    delay = min(max_delay, base_delay * (2 ** (attempt - 1))) + uniform(0, jitter)
    """
    if attempt_number < 1:
        attempt_number = 1

    # Exponential growth
    exponential = base_delay * (2 ** (attempt_number - 1))
    bounded_delay = min(max_delay, exponential)

    # Full randomized jitter up to jitter_factor * bounded_delay
    jitter = random.uniform(0, jitter_factor * bounded_delay)
    total_delay = min(max_delay, bounded_delay + jitter)

    return round(total_delay, 2)

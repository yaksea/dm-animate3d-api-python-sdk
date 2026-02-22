"""Enumerations for Animate 3D API."""

from enum import Enum


class Status(str, Enum):
    """Status enumeration for job status.

    REST API returns one of: PROGRESS, SUCCESS, FAILURE, RETRY
    STARTING is SDK-only, used internally for async generators.

    Attributes:
        STARTING: SDK internal use only - indicates job just submitted
        PROGRESS: Request is still being processed
        SUCCESS: Request is processed successfully
        FAILURE: Request has failed
        RETRY: Request has failed but is being retried
    """

    STARTING = "STARTING"  # SDK internal: job just submitted, not from API
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"

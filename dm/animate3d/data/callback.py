"""Callback data structures."""

from dataclasses import dataclass
from typing import List, Optional, Any


@dataclass
class ProgressCallbackData:
    """Data passed to progress callback."""

    rid: str
    progress_percent: int
    position_in_queue: int


@dataclass
class JobResult:
    """Job result data."""

    input: List[str]
    output: Any


@dataclass
class JobError:
    """Job error data."""

    code: str
    message: str


@dataclass
class ResultCallbackData:
    """Data passed to result callback."""

    rid: str
    result: Optional[JobResult] = None
    error: Optional[JobError] = None

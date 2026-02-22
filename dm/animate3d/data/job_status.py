"""Job status model."""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from dm.animate3d.error_codes import format_error_message
from dm.animate3d.data.enums import Status


@dataclass
class JobStatusDetails:
    """Job status details returned by /status API.

    For PROGRESS status:
        - step: Current processing step
        - total: Total number of steps

    For SUCCESS status:
        - input_file: Original video file
        - output_file: Processed video file

    For FAILURE/RETRY status:
        - exc_message: Error message (formatted with error codes)
        - exc_type: Exception type
    """

    step: Optional[int] = None
    total: Optional[int] = None
    exc_message: Optional[str] = None
    exc_type: Optional[str] = None
    input_file: Optional[List[str]] = None
    output_file: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobStatusDetails":
        """Create JobStatusDetails from API response."""
        # Format error message using error codes
        exc_message_raw = data.get("exc_message")
        exc_type = data.get("exc_type")
        exc_message = None
        if exc_message_raw is not None:
            exc_message = format_error_message(exc_message_raw, exc_type)

        return cls(
            step=data.get("step"),
            total=data.get("total"),
            exc_message=exc_message,
            exc_type=exc_type,
            input_file=data.get("in"),
            output_file=data.get("out"),
        )

    @property
    def progress_percent(self) -> Optional[float]:
        """Get progress as percentage (0-100)."""
        if self.step is not None and self.total is not None and self.total > 0:
            return (self.step / self.total) * 100
        return None


@dataclass
class JobStatus:
    """Job status information returned by /status API.

    Attributes:
        rid: Request ID
        status: Current status
        details: Status details (progress, errors, etc.)
    """

    rid: str
    status: Optional[Status] = None
    details: Optional[JobStatusDetails] = None
    position_in_queue: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobStatus":
        """Create JobStatus from API response."""
        status = None
        if "status" in data:
            try:
                status = Status(data["status"])
            except ValueError:
                pass

        details = None
        if "details" in data:
            details = JobStatusDetails.from_dict(data["details"])

        return cls(
            rid=data.get("rid", ""),
            status=status,
            details=details,
            position_in_queue=data.get("positionInQueue", 0)
        )

    def is_completed(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in (Status.SUCCESS, Status.FAILURE)

    def is_successful(self) -> bool:
        """Check if job completed successfully."""
        return self.status == Status.SUCCESS

    def is_failed(self) -> bool:
        """Check if job failed."""
        return self.status == Status.FAILURE

    def is_in_progress(self) -> bool:
        """Check if job is still processing."""
        return self.status == Status.PROGRESS

"""Animate 3D Python SDK.

This module provides synchronous and asynchronous clients for the Animate 3D REST API.
"""

from dm.animate3d.client import Animate3DClient
from dm.animate3d.async_client import AsyncAnimate3DClient
from dm.animate3d.data.params import ProcessParams
from dm.animate3d.data.enums import Status
from dm.animate3d.data.job import Job
from dm.animate3d.data.job_status import JobStatus, JobStatusDetails
from dm.animate3d.data.callback import (
    ProgressCallbackData,
    ResultCallbackData,
    JobResult,
    JobError,
)
from dm.animate3d.data.character import CharacterModel
from dm.animate3d.data.response import DownloadLink, DownloadUrl, DownloadFile
from dm.animate3d.exceptions import (
    Animate3DError,
    AuthenticationError,
    APIError,
    ValidationError,
)

__version__ = "2.0.0"

__all__ = [
    # Clients
    "Animate3DClient",
    "AsyncAnimate3DClient",
    # Parameters
    "ProcessParams",
    # Models
    "Status",
    "Job",
    "JobStatus",
    "JobStatusDetails",
    "ProgressCallbackData",
    "ResultCallbackData",
    "JobResult",
    "JobError",
    "CharacterModel",
    "DownloadLink",
    "DownloadUrl",
    "DownloadFile",
    # Exceptions
    "Animate3DError",
    "AuthenticationError",
    "APIError",
    "ValidationError",
]

"""Custom exceptions for Animate 3D API."""


class Animate3DError(Exception):
    """Base exception for all Animate 3D API errors."""

    pass


class AuthenticationError(Animate3DError):
    """Raised when authentication fails."""

    pass


class APIError(Animate3DError):
    """Raised when API call fails with an error code."""

    def __init__(self, message: str, status_code: int = None, error_code: int = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class ValidationError(Animate3DError):
    """Raised when input validation fails."""

    pass


class TimeoutError(Animate3DError):
    """Raised when operation times out."""

    def __init__(self, message: str, rid: str = None):
        super().__init__(message)
        self.rid = rid

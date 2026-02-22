"""Utility functions for Animate 3D SDK."""

import os
import re
from typing import Optional


def ends_with_mp_tracked_id(name: str) -> bool:
    """Check if name ends with multi-person tracking ID pattern (_XXX).

    Args:
        name: Name to check

    Returns:
        True if name ends with pattern like "_001", "_002", etc.
    """
    if len(name) < 4:
        return False
    return name[-4] == "_" and name[-3:].isdigit()


def is_http_url(path: str) -> bool:
    """Check if path is an HTTP/HTTPS URL.

    Args:
        path: Path or URL to check

    Returns:
        True if path starts with http:// or https://
    """
    return path.startswith(("http://", "https://"))


def get_file_extension(file_path: str) -> str:
    """Get file extension without the leading dot.

    Args:
        file_path: Path to file

    Returns:
        Extension without dot (e.g., "mp4", "fbx")
    """
    _, ext = os.path.splitext(file_path)
    return ext[1:] if ext else ""


def get_file_name_without_ext(file_path: str) -> str:
    """Get file name without extension.

    Args:
        file_path: Path to file

    Returns:
        Base name without extension
    """
    basename = os.path.basename(file_path)
    name, _ = os.path.splitext(basename)
    return name


def validate_file_exists(file_path: str) -> None:
    """Validate that a file exists.

    Args:
        file_path: Path to file

    Raises:
        FileNotFoundError: If file does not exist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File does not exist: {file_path}")


def validate_formats(formats: list) -> None:
    """Validate output formats.

    Args:
        formats: List of format strings

    Raises:
        ValueError: If formats are invalid
    """
    valid_formats = {"bvh", "fbx", "mp4", "glb", "png", "jpg"}
    for fmt in formats:
        if fmt.lower() not in valid_formats:
            raise ValueError(
                f"Invalid format: {fmt}. Valid formats: {', '.join(valid_formats)}"
            )


def sanitize_filename(name: str) -> str:
    """Sanitize filename by removing invalid characters.

    Args:
        name: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, "_", name)

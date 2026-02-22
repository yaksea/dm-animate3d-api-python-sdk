"""Error code mappings for Animate 3D API."""

from typing import Any, Optional

# Error code to message mapping
ERROR_CODES = {
    101: "Not enough credits",
    201: "Error downloading the video or DM asset",
    202: "Error converting the video",
    503: "Error processing the parameters",
    504: "Error loading the character assets",
    505: "Physics Filter is incompatible with the custom characters",
    506: "Error creating the pose estimation",
    507: "Error while processing the body tracking",
    508: "Input video or image doesn't meet the requirements to generate animations of good quality",
    509: "Error loading the configurations",
    510: "Error open internal files",
    511: "Processing interrupted",
    513: "Failed to detect character in the video",
    599: "Body tracking timeout",
    701: "Error processing the face tracking",
    799: "Face tracking timeout",
    901: "Error loading the mesh of the custom character",
    902: "Error loading the BVH custom character",
    903: "Error copying animations onto the custom character",
    904: "Error exporting animations for the custom character",
    905: "Custom character doesn't include skinned mesh information",
    906: "More than half of the required blendshapes are missing",
    907: "Error loading facial definition for the custom character",
    908: "Error loading facial tracking data",
    909: "Error loading the metadata of the custom character",
    999: "Animation baking timeout",
    1301: "Error creating the hand estimation",
    1302: "Error creating the hand estimation",
    1303: "Error creating the hand estimation",
    1304: "Error opening the video",
    1305: "Error parsing video path",
    1306: "Error loading internal files",
    1307: "Error processing hand tracking",
    1308: "Error processing the video",
    1399: "Hand tracking timeout",
}


def get_error_message(error_code: Any) -> str:
    """Get error message for an error code.

    Args:
        error_code: Error code, which can be an int, str, or list of codes

    Returns:
        Error message string
    """
    # Handle list format (e.g., ['101'])
    if isinstance(error_code, list):
        if not error_code:
            return "Unknown error"
        # Get messages for all codes in the list
        messages = []
        for code in error_code:
            code_int = _parse_error_code(code)
            if code_int and code_int in ERROR_CODES:
                messages.append(f"Error {code_int}: {ERROR_CODES[code_int]}")
            else:
                messages.append(f"Error {code}")
        return "; ".join(messages)

    # Handle single code
    code_int = _parse_error_code(error_code)
    if code_int and code_int in ERROR_CODES:
        return f"Error {code_int}: {ERROR_CODES[code_int]}"

    # Fallback to original value
    return str(error_code) if error_code is not None else "Unknown error"


def _parse_error_code(code: Any) -> Optional[int]:
    """Parse error code to integer.

    Args:
        code: Error code (can be int, str, etc.)

    Returns:
        Integer error code or None if cannot parse
    """
    if isinstance(code, int):
        return code
    if isinstance(code, str):
        try:
            return int(code)
        except ValueError:
            return None
    return None


def format_error_message(exc_message: Any, exc_type: Optional[str] = None) -> str:
    """Format error message from exc_message and exc_type.

    Args:
        exc_message: Exception message (can be str, list, etc.)
        exc_type: Exception type (optional)

    Returns:
        Formatted error message
    """
    # Handle exc_message which may be a string, list, or other format
    if isinstance(exc_message, list):
        # If it's a list, treat each element as an error code
        error_messages = []
        for item in exc_message:
            msg = get_error_message(item)
            error_messages.append(msg)
        message = "; ".join(error_messages)
    elif exc_message:
        # Try to parse as error code first
        parsed = _parse_error_code(exc_message)
        if parsed and parsed in ERROR_CODES:
            message = get_error_message(parsed)
        else:
            message = str(exc_message)
    else:
        message = "Unknown error"

    # Add exception type if provided
    if exc_type:
        message = f"{exc_type}: {message}"

    return message

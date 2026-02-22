"""API response models."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class DownloadFile:
    """Download file information."""

    file_type: str  # bvh, fbx, mp4, glb, etc.
    url: str

    @classmethod
    def from_dict(cls, data: List[Dict[str, str]]) -> List["DownloadFile"]:
        """Create DownloadFile list from API response.

        Args:
            data: List of dicts like [{"bvh": "url"}, {"fbx": "url"}]

        Returns:
            List of DownloadFile objects
        """
        files = []
        for file_dict in data:
            for file_type, url in file_dict.items():
                files.append(cls(file_type=file_type, url=url))
        return files


@dataclass
class DownloadUrl:
    """Download URL group."""

    name: str
    files: List[DownloadFile]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadUrl":
        """Create DownloadUrl from API response."""
        files = DownloadFile.from_dict(data.get("files", []))
        return cls(name=data.get("name", ""), files=files)

    def get_file_url(self, file_type: str) -> Optional[str]:
        """Get URL for a specific file type.

        Args:
            file_type: File type (e.g., "bvh", "fbx", "mp4")

        Returns:
            URL string or None if not found
        """
        for file in self.files:
            if file.file_type == file_type:
                return file.url
        return None


@dataclass
class DownloadLink:
    """Download link information."""

    rid: str
    name: Optional[str] = None
    size: Optional[int] = None
    duration: Optional[float] = None
    input_url: Optional[str] = None
    urls: List[DownloadUrl] = None
    mode: Optional[int] = None  # 0=single person, 1=multi person
    models: Optional[List[Dict[str, Any]]] = None

    def __post_init__(self):
        """Initialize urls if None."""
        if self.urls is None:
            self.urls = []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadLink":
        """Create DownloadLink from API response."""
        urls = []
        if "urls" in data:
            urls = [DownloadUrl.from_dict(url_data) for url_data in data["urls"]]

        return cls(
            rid=data.get("rid", ""),
            name=data.get("name"),
            size=data.get("size"),
            duration=data.get("duration"),
            input_url=data.get("input"),
            urls=urls,
            mode=data.get("mode"),
            models=data.get("models"),
        )

    def is_multi_person(self) -> bool:
        """Check if this is a multi-person job result."""
        return self.mode == 1

    def get_url_group(self, name: str) -> Optional[DownloadUrl]:
        """Get URL group by name.

        Args:
            name: Name of the URL group (e.g., "output", "all_characters")

        Returns:
            DownloadUrl object or None if not found
        """
        for url_group in self.urls:
            if url_group.name == name:
                return url_group
        return None

    def get_all_file_urls(self, file_type: str) -> List[str]:
        """Get all URLs for a specific file type across all groups.

        Args:
            file_type: File type (e.g., "bvh", "fbx", "mp4")

        Returns:
            List of URL strings
        """
        urls = []
        for url_group in self.urls:
            url = url_group.get_file_url(file_type)
            if url:
                urls.append(url)
        return urls

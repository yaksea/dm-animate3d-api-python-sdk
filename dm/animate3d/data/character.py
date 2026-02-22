"""Character model definitions."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class CharacterModel:
    """Character model information."""

    id: str
    name: str
    thumb: Optional[str] = None
    rig_id: Optional[str] = None
    platform: Optional[str] = None
    ctime: Optional[int] = None
    mtime: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterModel":
        """Create CharacterModel from API response."""
        return cls(
            id=data.get("id") or data.get("Id", ""),
            name=data.get("name", ""),
            thumb=data.get("thumb"),
            rig_id=data.get("rigId"),
            platform=data.get("platform"),
            ctime=data.get("ctime"),
            mtime=data.get("mtime"),
        )

    @property
    def created_at(self) -> Optional[datetime]:
        """Get creation time as datetime."""
        if self.ctime:
            return datetime.fromtimestamp(self.ctime / 1000.0)
        return None

    @property
    def modified_at(self) -> Optional[datetime]:
        """Get modification time as datetime."""
        if self.mtime:
            return datetime.fromtimestamp(self.mtime / 1000.0)
        return None

    def is_custom(self) -> bool:
        """Check if this is a custom (user-uploaded) model."""
        return self.platform == "custom"

    def is_stock(self) -> bool:
        """Check if this is a stock (built-in) model."""
        return self.platform != "custom"

"""Process parameters for video processing."""

import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Union


@dataclass
class ProcessParams:
    """Builder for process parameters.

    This class provides a type-safe way to configure video processing parameters.

    Example:
        params = ProcessParams(
            formats=["bvh", "fbx", "mp4"],
            model="model_id",
            track_face=1,
            track_hand=1,
        )
    """

    # Output formats
    formats: Optional[List[str]] = None

    # Character model (single person mode)
    model_id: str = None

    # Configuration
    config: str = "configDefault"

    # Physics simulation (0=off, 1=on)
    sim: Optional[int] = None

    # Face tracking (0=off, 1=on)
    track_face: Optional[int] = None

    # Hand tracking (0=off, 1=on)
    track_hand: Optional[int] = None

    # Foot locking mode: "auto", "always", "never", "grounding"
    foot_locking_mode: Optional[str] = None

    # Video speed multiplier (1.0-8.0, for slowed-down videos)
    video_speed_multiplier: Optional[float] = None

    # Pose filtering strength (0.0-1.0, higher = smoother)
    pose_filtering_strength: Optional[float] = None

    # Upper body only tracking
    upper_body_only: Optional[bool] = None

    # Root at origin
    root_at_origin: Optional[bool] = None

    # Time trim (start_seconds, end_seconds)
    trim: Optional[Tuple[float, float]] = None

    # Crop region (left, top, right, bottom) normalized 0-1
    crop: Optional[Tuple[float, float, float, float]] = None

    # Render options for MP4 output
    render_sbs: Optional[int] = None  # Side-by-side (0=character only, 1=with video)
    render_bg_color: Optional[Tuple[int, int, int, int]] = None  # RGBA 0-255
    render_backdrop: Optional[str] = None  # e.g., "studio"
    render_shadow: Optional[int] = None  # 0=off, 1=on
    render_include_audio: Optional[int] = None  # 0=off, 1=on
    render_cam_mode: Optional[int] = None  # 0=Cinematic, 1=Fixed, 2=Face

    # Internal fields (set by SDK, not by user)
    _models: Optional[List[Dict[str, str]]] = field(default=None, repr=False)
    _pipeline: Optional[str] = field(default=None, repr=False)

    def to_params_list(self) -> List[str]:
        """Convert to list of parameter strings for API.

        Returns:
            List of parameter strings in "key=value" format
        """
        params = []

        if self.config:
            params.append(f"config={self.config}")

        if self.formats:
            formats_str = ",".join(self.formats)
            params.append(f"formats={formats_str}")

        if self.model_id:
            params.append(f"model={self.model_id}")

        if self._models:
            models_json = json.dumps(self._models)
            params.append(f"models={models_json}")

        if self.sim is not None:
            params.append(f"sim={self.sim}")

        if self.track_face is not None:
            params.append(f"trackFace={self.track_face}")

        if self.track_hand is not None:
            params.append(f"trackHand={self.track_hand}")

        if self.foot_locking_mode:
            params.append(f"footLockingMode={self.foot_locking_mode}")

        if self.video_speed_multiplier is not None:
            params.append(f"videoSpeedMultiplier={self.video_speed_multiplier}")

        if self.pose_filtering_strength is not None:
            params.append(f"poseFilteringStrength={self.pose_filtering_strength}")

        if self.upper_body_only is not None:
            params.append(f"upperBodyOnly={str(self.upper_body_only).lower()}")

        if self.root_at_origin is not None:
            params.append(f"rootAtOrigin={str(self.root_at_origin).lower()}")

        if self.trim:
            params.append(f"trim={self.trim[0]},{self.trim[1]}")

        if self.crop:
            params.append(
                f"crop={self.crop[0]},{self.crop[1]},{self.crop[2]},{self.crop[3]}"
            )

        if self.render_sbs is not None:
            params.append(f"render.sbs={self.render_sbs}")

        if self.render_bg_color:
            params.append(
                f"render.bgColor={self.render_bg_color[0]},{self.render_bg_color[1]},"
                f"{self.render_bg_color[2]},{self.render_bg_color[3]}"
            )

        if self.render_backdrop:
            params.append(f"render.backdrop={self.render_backdrop}")

        if self.render_shadow is not None:
            params.append(f"render.shadow={self.render_shadow}")

        if self.render_include_audio is not None:
            params.append(f"render.includeAudio={self.render_include_audio}")

        if self.render_cam_mode is not None:
            params.append(f"render.CamMode={self.render_cam_mode}")

        if self._pipeline:
            params.append(f"pipeline={self._pipeline}")

        return params

    def copy(self) -> "ProcessParams":
        """Create a copy of this ProcessParams instance."""
        return ProcessParams(
            formats=self.formats.copy() if self.formats else None,
            model_id=self.model_id,
            config=self.config,
            sim=self.sim,
            track_face=self.track_face,
            track_hand=self.track_hand,
            foot_locking_mode=self.foot_locking_mode,
            video_speed_multiplier=self.video_speed_multiplier,
            pose_filtering_strength=self.pose_filtering_strength,
            upper_body_only=self.upper_body_only,
            root_at_origin=self.root_at_origin,
            trim=self.trim,
            crop=self.crop,
            render_sbs=self.render_sbs,
            render_bg_color=self.render_bg_color,
            render_backdrop=self.render_backdrop,
            render_shadow=self.render_shadow,
            render_include_audio=self.render_include_audio,
            render_cam_mode=self.render_cam_mode,
            _models=self._models.copy() if self._models else None,
            _pipeline=self._pipeline,
        )

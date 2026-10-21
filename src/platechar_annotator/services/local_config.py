"""Optional, uncommitted per-checkout defaults."""

import json
import math
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parents[3] / ".local_config.json"


def load_default_aspect_ratio() -> tuple[float, float]:
    """Read the local W:H default, falling back to 9:16 on bad/missing config."""
    try:
        config = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        ratio = config["aspect_ratio"]
        width, height = float(ratio["width"]), float(ratio["height"])
        if math.isfinite(width) and math.isfinite(height) and width > 0 and height > 0:
            return width, height
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return 9.0, 16.0


def load_group_pan_range_fraction() -> float:
    """Read max group-pan travel as a fraction of image size (default 0.1)."""
    try:
        config = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        value = float(config["group_pan_range_fraction"])
        if math.isfinite(value) and 0 < value <= 1:
            return value
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return 0.1


def load_zoom_step_fraction() -> float:
    """Read wheel zoom change per notch (default 0.05, or 5%)."""
    try:
        config = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        value = float(config["zoom_step_fraction"])
        if math.isfinite(value) and 0 < value <= 0.5:
            return value
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return 0.05

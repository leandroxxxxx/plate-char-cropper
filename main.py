"""Entry point for PlateChar Annotator."""

import sys
from pathlib import Path

# Allow running `python main.py` without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from platechar_annotator.app import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run())
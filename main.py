#!/usr/bin/env python3

from __future__ import annotations

import sys
import logging
from pathlib import Path

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("ai-pfi")

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from api.cli import main


if __name__ == "__main__":
    raise SystemExit(main())

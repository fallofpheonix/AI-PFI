"""
Pytest configuration — adds src/ to sys.path so that
`from pipeline.xxx import ...` works in tests without installing the package.
"""

import sys
from pathlib import Path

# Ensure src/ is on sys.path
src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

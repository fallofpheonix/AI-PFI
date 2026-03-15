"""
Pytest configuration — adds src/ to sys.path so that
`from pipeline.xxx import ...` works in tests without installing the package.
"""

import sys
from pathlib import Path

# Insert src/ at the front of sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    huggingface_cache_dir: str
    default_output_dir: str = "./out"


def load_settings() -> AppSettings:
    cache_dir = os.getenv("HF_HOME", "/tmp/huggingface_cache")
    return AppSettings(huggingface_cache_dir=cache_dir)

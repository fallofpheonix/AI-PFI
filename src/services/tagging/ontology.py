"""Ontology loader and lookup helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

_DEFAULT_ONTOLOGY = (
    Path(__file__).resolve().parents[2] / "ontology" / "foa_ontology.json"
)


class Ontology:
    """Controlled vocabulary for FOA semantic tagging."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else _DEFAULT_ONTOLOGY
        with open(self.path, "r", encoding="utf-8") as fh:
            self._data: Dict[str, Dict[str, List[str]]] = json.load(fh)
        self.categories: List[str] = list(self._data.keys())

    def terms_for(self, category: str) -> Dict[str, List[str]]:
        return self._data.get(category, {})

    def flat_terms(self, category: str) -> List[Tuple[str, str]]:
        terms = []
        for subcategory, values in self.terms_for(category).items():
            for term in values:
                terms.append((subcategory, term))
        return terms

    def to_dict(self) -> Dict[str, Dict[str, List[str]]]:
        return self._data

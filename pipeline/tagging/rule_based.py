"""
Rule-based FOA tagger.

Uses exact keyword matching against the controlled ontology.
Deterministic — produces consistent results for identical input text.
"""

import re
import logging
from collections import defaultdict
from typing import Dict, List

from .ontology import Ontology

logger = logging.getLogger(__name__)


class RuleBasedTagger:
    """
    Applies ontology terms via string matching.

    Matching rules:
    - Case-insensitive
    - Whole-word matching (word boundary anchors)
    - Multi-word phrases matched literally
    - Returns the subcategory labels that matched, deduplicated
    """

    def __init__(self, ontology: Ontology):
        self.ontology = ontology
        self._compiled = self._compile_patterns()

    def tag(self, text: str) -> Dict[str, List[str]]:
        """
        :param text: combined text of FOA fields
        :return: dict {category: [matched_subcategories, ...]}
        """
        if not text:
            return {cat: [] for cat in self.ontology.categories}

        results: Dict[str, List[str]] = defaultdict(list)
        text_lower = text.lower()

        for category, patterns in self._compiled.items():
            seen = set()
            for subcat, pattern in patterns:
                if pattern.search(text_lower) and subcat not in seen:
                    results[category].append(subcat)
                    seen.add(subcat)

        # Ensure all categories present
        for cat in self.ontology.categories:
            if cat not in results:
                results[cat] = []

        return dict(results)

    # ─────────────────────────────────────────────────────────────────────────

    def _compile_patterns(self) -> Dict[str, list]:
        """Pre-compile regex patterns for all ontology terms."""
        compiled: Dict[str, list] = {}
        for category in self.ontology.categories:
            cat_patterns = []
            for subcat, term in self.ontology.flat_terms(category):
                # Escape special chars; add word boundaries
                escaped = re.escape(term.lower())
                # For single-word terms use \b; for multi-word, lookahead/behind spaces
                if " " in term:
                    pattern = re.compile(escaped)
                else:
                    pattern = re.compile(r"\b" + escaped + r"\b")
                cat_patterns.append((subcat, pattern))
            compiled[category] = cat_patterns
        return compiled

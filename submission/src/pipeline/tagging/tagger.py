"""
Hybrid FOA Tagger.

Combines rule-based and embedding-based tagging:
  - Rule-based tags are always trusted (high precision)
  - Embedding tags supplement where rules find nothing
  - Union strategy: include tag if either method fires

Optionally integrates an LLM-assisted classifier (stretch goal).
"""

import logging
from typing import Dict, List, Optional

from .ontology import Ontology
from .rule_based import RuleBasedTagger
from .embedding_tagger import EmbeddingTagger

logger = logging.getLogger(__name__)


class HybridTagger:
    """
    Orchestrates rule-based + embedding tagging with a union strategy.

    Parameters
    ----------
    use_embeddings : bool
        Enable embedding-based tagging (requires sentence-transformers).
    use_llm : bool
        Enable LLM-assisted tagging (stretch goal; requires API key).
    embedding_threshold : float
        Cosine similarity threshold for embedding tagger.
    """

    def __init__(
        self,
        ontology_path: Optional[str] = None,
        use_embeddings: bool = True,
        use_llm: bool = False,
        embedding_threshold: float = 0.35,
    ):
        from pathlib import Path
        from .ontology import _DEFAULT_ONTOLOGY

        path = Path(ontology_path) if ontology_path else _DEFAULT_ONTOLOGY
        self.ontology = Ontology(path)

        self.rule_tagger = RuleBasedTagger(self.ontology)
        self.embedding_tagger = (
            EmbeddingTagger(self.ontology, threshold=embedding_threshold)
            if use_embeddings
            else None
        )
        self.use_llm = use_llm
        self.llm_tagger = None
        if use_llm:
            from .llm_tagger import LLMTagger

            self.llm_tagger = LLMTagger(self.ontology)

        logger.info(
            f"HybridTagger initialized | rules=True "
            f"embeddings={use_embeddings and (self.embedding_tagger.available if self.embedding_tagger else False)} "
            f"llm={use_llm}"
        )

    def tag(self, foa_record) -> Dict[str, List[str]]:
        """
        Tag an FOARecord.

        :param foa_record: FOARecord dataclass
        :return: dict of tags by category
        """
        text = self._build_text(foa_record)
        return self.tag_text(text)

    def tag_text(self, text: str) -> Dict[str, List[str]]:
        """Tag raw text directly (useful for evaluation)."""
        rule_tags = self.rule_tagger.tag(text)
        combined = {cat: list(tags) for cat, tags in rule_tags.items()}

        if self.embedding_tagger and self.embedding_tagger.available:
            emb_tags = self.embedding_tagger.tag(text)
            combined = self._merge_tags(combined, emb_tags)

        if self.llm_tagger:
            llm_tags = self.llm_tagger.tag(text)
            combined = self._merge_tags(combined, llm_tags)

        return combined

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_text(self, foa_record) -> str:
        """Concatenate relevant FOA fields for tagging."""
        parts = [
            foa_record.title,
            foa_record.agency,
            foa_record.description,
            foa_record.eligibility,
        ]
        return "\n\n".join(p for p in parts if p)

    def _merge_tags(
        self,
        primary: Dict[str, List[str]],
        secondary: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:
        """Union merge: add secondary tags not already in primary."""
        merged = {}
        all_cats = set(primary) | set(secondary)
        for cat in all_cats:
            p = primary.get(cat, [])
            s = secondary.get(cat, [])
            seen = set(p)
            extra = [t for t in s if t not in seen]
            merged[cat] = p + extra
        return merged

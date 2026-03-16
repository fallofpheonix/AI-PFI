"""
Embedding-based FOA tagger.

Uses sentence-transformers to compute cosine similarity between
FOA text and ontology subcategory label embeddings.
Falls back gracefully if sentence-transformers is not installed.
"""

import logging
from typing import Dict, List, Optional

from .ontology import Ontology

logger = logging.getLogger(__name__)

# Similarity threshold above which a tag is assigned
DEFAULT_THRESHOLD = 0.35


class EmbeddingTagger:
    """
    Semantic similarity tagger using sentence-transformers.

    Model: all-MiniLM-L6-v2 (fast, small, good quality)
    """

    def __init__(
        self,
        ontology: Ontology,
        model_name: str = "all-MiniLM-L6-v2",
        threshold: float = DEFAULT_THRESHOLD,
    ):
        self.ontology = ontology
        self.threshold = threshold
        self._model = None
        self._label_embeddings: Optional[dict] = None

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(model_name)
            self._label_embeddings = self._build_label_embeddings()
            logger.info(f"EmbeddingTagger loaded model: {model_name}")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "EmbeddingTagger will return empty results. "
                "Install with: pip install sentence-transformers"
            )

    @property
    def available(self) -> bool:
        return self._model is not None

    def tag(self, text: str) -> Dict[str, List[str]]:
        """Return embedding-based tags or empty dict if unavailable."""
        empty = {cat: [] for cat in self.ontology.categories}
        if not self.available or not text:
            return empty

        import numpy as np
        from sentence_transformers import util

        # Embed a 512-token summary of the FOA text
        text_snippet = text[:2000]
        text_emb = self._model.encode(text_snippet, convert_to_tensor=True)

        results: Dict[str, List[str]] = {}
        for category, label_embs in self._label_embeddings.items():
            matched = []
            for subcat, emb in label_embs.items():
                score = float(util.cos_sim(text_emb, emb)[0][0])
                if score >= self.threshold:
                    matched.append((subcat, score))
            # Sort by score descending, take labels only
            matched.sort(key=lambda x: x[1], reverse=True)
            results[category] = [m[0] for m in matched]

        return results

    # ─────────────────────────────────────────────────────────────────────────

    def _build_label_embeddings(self) -> dict:
        """Pre-compute embeddings for each subcategory label."""
        embeddings = {}
        for category in self.ontology.categories:
            cat_embs = {}
            subcats = list(self.ontology.terms_for(category).keys())
            if not subcats:
                continue
            # Use both the subcategory key and its sample terms as the embedding text
            texts = []
            for subcat in subcats:
                terms = self.ontology.terms_for(category).get(subcat, [])
                combined = subcat.replace("_", " ") + ": " + ", ".join(terms[:8])
                texts.append(combined)

            emb_matrix = self._model.encode(texts, convert_to_tensor=True)
            for subcat, emb in zip(subcats, emb_matrix):
                cat_embs[subcat] = emb
            embeddings[category] = cat_embs

        return embeddings

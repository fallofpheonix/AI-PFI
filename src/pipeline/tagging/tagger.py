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
        self.embedding_tagger = EmbeddingTagger(
            self.ontology, threshold=embedding_threshold
        ) if use_embeddings else None
        self.use_llm = use_llm

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

        if self.use_llm:
            llm_tags = self._llm_tag(text)
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

    def _llm_tag(self, text: str) -> Dict[str, List[str]]:
        """
        LLM-assisted tagging (stretch goal).
        Requires ANTHROPIC_API_KEY or OPENAI_API_KEY env variable.
        """
        import os, json

        # ── Try Anthropic Claude ───────────────────────────────────────────
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                prompt = self._build_llm_prompt(text)
                msg = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = msg.content[0].text
                return self._parse_llm_response(raw)
            except Exception as e:
                logger.warning(f"LLM tagging (Anthropic) failed: {e}")

        # ── Try OpenAI ─────────────────────────────────────────────────────
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                prompt = self._build_llm_prompt(text)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                )
                raw = resp.choices[0].message.content
                return self._parse_llm_response(raw)
            except Exception as e:
                logger.warning(f"LLM tagging (OpenAI) failed: {e}")

        return {}

    def _build_llm_prompt(self, text: str) -> str:
        categories = {cat: list(self.ontology.terms_for(cat).keys())
                      for cat in self.ontology.categories}
        import json
        return (
            "You are a research grants classifier. "
            "Given the following Funding Opportunity Announcement text, "
            "return a JSON object with these keys: "
            + ", ".join(self.ontology.categories)
            + ". Each key should map to a list of applicable subcategory labels "
            "chosen ONLY from the allowed values shown here:\n"
            + json.dumps(categories, indent=2)
            + "\n\nFOA Text (first 1500 chars):\n"
            + text[:1500]
            + "\n\nRespond with ONLY valid JSON, no explanation."
        )

    def _parse_llm_response(self, raw: str) -> Dict[str, List[str]]:
        import json, re
        try:
            # Strip markdown fences if present
            raw = re.sub(r"```(?:json)?", "", raw).strip()
            data = json.loads(raw)
            # Validate structure
            result = {}
            for cat in self.ontology.categories:
                val = data.get(cat, [])
                if isinstance(val, list):
                    result[cat] = [str(v) for v in val]
            return result
        except Exception as e:
            logger.warning(f"Failed to parse LLM tag response: {e}")
            return {}

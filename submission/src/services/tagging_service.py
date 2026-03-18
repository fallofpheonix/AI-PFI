from __future__ import annotations

from pipeline.tagging import HybridTagger


class FOATaggingService:
    def __init__(
        self,
        *,
        ontology_path: str | None = None,
        use_embeddings: bool = True,
        use_llm: bool = False,
    ):
        self._tagger = HybridTagger(
            ontology_path=ontology_path,
            use_embeddings=use_embeddings,
            use_llm=use_llm,
        )

    @property
    def tagger(self) -> HybridTagger:
        return self._tagger

    def tag_record(self, record) -> dict:
        return self._tagger.tag(record)

from typing import List
from core.models import FOARecord
from services.tagging.tagger import HybridTagger


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

    def tag_record(self, record: FOARecord) -> List[str]:
        tag_dict = self._tagger.tag(record)
        # Flatten dictionary of lists into a single list of unique tags
        flattened = set()
        for tags in tag_dict.values():
            if isinstance(tags, list):
                flattened.update(tags)
            else:
                flattened.add(str(tags))
        record.tags = sorted(list(flattened))
        return record.tags

from __future__ import annotations

from core.normalization import FOANormalizer
from services.evaluation_service import FOAEvaluationService
from services.export_service import FOAExportService
from services.extraction_service import FOAExtractionService
from services.ingestion_service import FOAIngestionService
from services.tagging_service import FOATaggingService


class FOAPipelineService:
    def __init__(
        self,
        *,
        use_embeddings: bool = True,
        use_llm: bool = False,
        ontology_path: str | None = None,
        store_path: str | None = None,
    ):
        self.ingestion = FOAIngestionService()
        self.extraction = FOAExtractionService()
        self.normalizer = FOANormalizer()
        self.tagging = FOATaggingService(
            ontology_path=ontology_path,
            use_embeddings=use_embeddings,
            use_llm=use_llm,
        )
        self.exporter = FOAExportService(store_path=store_path)
        self.evaluation = FOAEvaluationService(self.tagging.tagger)

    def process_url(self, source_url: str):
        raw_foa = self.ingestion.fetch_raw_foa(source_url)
        extracted = self.extraction.extract_fields(raw_foa)
        record = self.normalizer.normalize(extracted, raw_foa=raw_foa)
        record.tags = self.tagging.tag_record(record)
        self.exporter.maybe_upsert(record)
        return record

"""
FOA Intelligence Pipeline
=========================
Top-level package exposing the main Pipeline class and sub-packages.
"""

from .ingestion import IngestionRouter, RawFOA
from .extraction import HTMLExtractor, FOANormalizer, FOARecord, extract_text_from_pdf
from .tagging import HybridTagger
from .storage import export_json, export_csv, FOAStore
from .evaluation import run_evaluation

__version__ = "1.0.0"
__all__ = [
    "Pipeline",
    "IngestionRouter",
    "RawFOA",
    "HTMLExtractor",
    "FOANormalizer",
    "FOARecord",
    "HybridTagger",
    "export_json",
    "export_csv",
    "FOAStore",
    "run_evaluation",
]


class Pipeline:
    """
    High-level orchestrator for the full FOA intelligence pipeline.

    Usage:
        pipeline = Pipeline()
        record = pipeline.process(url="https://grants.gov/...")
        pipeline.export(record, out_dir="./out")
    """

    def __init__(
        self,
        use_embeddings: bool = True,
        use_llm: bool = False,
        ontology_path: str = None,
        store_path: str = None,
    ):
        self.router = IngestionRouter()
        self.extractor = HTMLExtractor()
        self.normalizer = FOANormalizer()
        self.tagger = HybridTagger(
            ontology_path=ontology_path,
            use_embeddings=use_embeddings,
            use_llm=use_llm,
        )
        self.store = FOAStore(store_path) if store_path else None

    def process(self, url: str) -> FOARecord:
        """Full pipeline: ingest -> extract -> normalize -> tag."""
        raw = self.router.ingest(url)

        if raw.raw_pdf_bytes:
            raw.raw_text = extract_text_from_pdf(raw.raw_pdf_bytes)

        extracted = self.extractor.extract(raw)
        record = self.normalizer.normalize(extracted, raw_foa=raw)
        record.tags = self.tagger.tag(record)

        if self.store:
            self.store.upsert(record)

        return record

    def export(self, record: FOARecord, out_dir: str):
        """Export a single record as JSON + CSV."""
        json_path = export_json(record, out_dir)
        csv_path = export_csv(record, out_dir)
        return json_path, csv_path

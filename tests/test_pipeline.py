from __future__ import annotations

from pathlib import Path

from core.normalization import FOANormalizer
from pipeline.ingestion.base import RawFOA
from services.foa_pipeline_service import FOAPipelineService


def test_normalizer_generates_fallback_id_for_empty_input():
    normalizer = FOANormalizer()
    record = normalizer.normalize({"title": "  Example Title  ", "source_url": "https://example.test/foa"})
    assert record.foa_id.startswith("FOA-")
    assert record.title == "Example Title"


def test_pipeline_service_processes_single_url(monkeypatch):
    service = FOAPipelineService(use_embeddings=False)

    fake_raw = RawFOA(source_url="https://example.test", source_name="nih", raw_text="test")
    monkeypatch.setattr(service.ingestion, "fetch_raw_foa", lambda _: fake_raw)
    monkeypatch.setattr(
        service.extraction,
        "extract_fields",
        lambda _: {
            "foa_id": "PAR-24-001",
            "title": "Cancer AI",
            "agency": "NIH",
            "source_url": "https://example.test",
            "description": "Cancer research with machine learning.",
        },
    )
    monkeypatch.setattr(service.tagging, "tag_record", lambda _: {"research_domains": ["biomedical"]})

    record = service.process_url("https://example.test")

    assert record.foa_id == "PAR-24-001"
    assert record.tags["research_domains"] == ["biomedical"]


def test_cli_batch_loader_deduplicates_comments_and_blanks(tmp_path):
    from api.cli import _load_batch_urls

    path = tmp_path / "batch.txt"
    path.write_text("# comment\nhttps://a\n\nhttps://a\nhttps://b\n", encoding="utf-8")

    urls = _load_batch_urls(str(path))
    assert urls == ["https://a", "https://b"]

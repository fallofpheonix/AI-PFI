"""
Test suite for the FOA Intelligence Pipeline.
Run with: pytest tests/ -v
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.extraction.html_extractor import HTMLExtractor, _parse_date, _extract_award_range
from pipeline.extraction.normalizer import FOANormalizer, FOARecord
from pipeline.tagging.ontology import Ontology
from pipeline.tagging.rule_based import RuleBasedTagger
from pipeline.tagging.tagger import HybridTagger
from pipeline.storage.exporter import export_json, export_csv, FOAStore
from pipeline.evaluation.metrics import run_evaluation, compute_metrics, EVAL_DATASET


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_foa_text():
    return """
    Funding Opportunity: PAR-24-001
    Title: Advancing Cancer Immunotherapy Through Machine Learning
    Agency: National Cancer Institute, NIH
    
    Program Description:
    This funding opportunity supports innovative research at the intersection of
    biomedical research and artificial intelligence. We seek projects applying
    deep learning and neural network approaches to identify biomarkers in
    oncology and immunology.
    
    Eligibility:
    Open to universities, research institutions, and pediatric hospitals.
    Applications from investigators in underrepresented minority groups
    are especially encouraged.
    
    Open Date: 2024-01-15
    Close Date: 2024-03-31
    Award Range: $500,000 – $2,000,000 per year
    """


@pytest.fixture
def ontology():
    return Ontology()


@pytest.fixture
def rule_tagger(ontology):
    return RuleBasedTagger(ontology)


@pytest.fixture
def hybrid_tagger():
    return HybridTagger(use_embeddings=False)


@pytest.fixture
def sample_record():
    r = FOARecord()
    r.foa_id = "PAR-24-001"
    r.title = "Advancing Cancer Immunotherapy Through Machine Learning"
    r.agency = "National Cancer Institute, NIH"
    r.open_date = "2024-01-15"
    r.close_date = "2024-03-31"
    r.description = "Research on cancer immunotherapy using deep learning and neural networks."
    r.eligibility = "Universities, research institutions, pediatric hospitals."
    r.award_range = {"min": 500000, "max": 2000000}
    r.source_url = "https://grants.nih.gov/grants/guide/pa-files/PAR-24-001.html"
    r.source_name = "nih"
    r.tags = {}
    return r


# ── Date parsing tests ────────────────────────────────────────────────────────

class TestDateParsing:
    def test_iso_date(self):
        assert _parse_date("2024-03-15") == "2024-03-15"

    def test_us_long_date(self):
        assert _parse_date("March 15, 2024") == "2024-03-15"

    def test_us_short_date(self):
        assert _parse_date("03/15/2024") == "2024-03-15"

    def test_abbreviated_month(self):
        result = _parse_date("Mar 15, 2024")
        assert result == "2024-03-15"

    def test_invalid_date(self):
        assert _parse_date("not a date") is None

    def test_empty_string(self):
        assert _parse_date("") is None


# ── Award range tests ─────────────────────────────────────────────────────────

class TestAwardExtraction:
    def test_dollar_amounts(self):
        result = _extract_award_range("Award: $500,000 – $2,000,000")
        assert result.get("min") == 500000
        assert result.get("max") == 2000000

    def test_millions_suffix(self):
        result = _extract_award_range("Up to $1.5M per year")
        assert result.get("max") == 1500000

    def test_no_amounts(self):
        result = _extract_award_range("No funding information available.")
        assert result == {}


# ── HTML extractor tests ──────────────────────────────────────────────────────

class TestHTMLExtractor:
    def test_extract_from_text(self, sample_foa_text):
        from pipeline.ingestion.base import RawFOA
        raw = RawFOA(source_url="http://test.gov", source_name="nih", raw_text=sample_foa_text)
        extractor = HTMLExtractor()
        result = extractor.extract(raw)
        assert result["foa_id"] == "PAR-24-001"
        assert "Cancer" in result["title"] or "Immunotherapy" in result["title"]
        assert result["open_date"] == "2024-01-15"
        assert result["close_date"] == "2024-03-31"
        assert result["award_range"].get("max") == 2000000

    def test_extract_agency(self, sample_foa_text):
        from pipeline.ingestion.base import RawFOA
        raw = RawFOA(source_url="http://nih.gov", source_name="nih", raw_text=sample_foa_text)
        extractor = HTMLExtractor()
        result = extractor.extract(raw)
        assert "NIH" in result["agency"] or "National Institutes" in result["agency"]


# ── Normalizer tests ──────────────────────────────────────────────────────────

class TestNormalizer:
    def test_basic_normalization(self):
        normalizer = FOANormalizer()
        extracted = {
            "foa_id": "PAR-24-001",
            "title": "Test FOA",
            "agency": "NIH",
            "open_date": "2024-01-15",
            "close_date": "2024-03-31",
            "description": "A test description.",
            "eligibility": "Universities.",
            "award_range": {"min": 100000, "max": 500000},
            "source_url": "http://test.gov",
        }
        record = normalizer.normalize(extracted)
        assert record.foa_id == "PAR-24-001"
        assert record.title == "Test FOA"
        assert record.award_range == {"min": 100000, "max": 500000}
        assert record.ingested_at != ""

    def test_id_generation(self):
        normalizer = FOANormalizer()
        record = normalizer.normalize({"title": "Test", "source_url": "http://example.com"})
        assert record.foa_id.startswith("FOA-")

    def test_whitespace_cleanup(self):
        normalizer = FOANormalizer()
        record = normalizer.normalize({"title": "  Test   FOA  \n  Title  "})
        assert record.title == "Test FOA Title"


# ── Ontology tests ────────────────────────────────────────────────────────────

class TestOntology:
    def test_loads(self, ontology):
        assert len(ontology.categories) == 4

    def test_categories(self, ontology):
        cats = ontology.categories
        assert "research_domains" in cats
        assert "methods_approaches" in cats
        assert "populations" in cats
        assert "sponsor_themes" in cats

    def test_terms_for(self, ontology):
        terms = ontology.terms_for("research_domains")
        assert "biomedical" in terms

    def test_flat_terms(self, ontology):
        flat = ontology.flat_terms("research_domains")
        assert len(flat) > 0
        assert all(len(t) == 2 for t in flat)


# ── Rule-based tagger tests ───────────────────────────────────────────────────

class TestRuleBasedTagger:
    def test_biomedical_tags(self, rule_tagger):
        tags = rule_tagger.tag("Cancer immunotherapy using genomics in oncology patients.")
        assert "biomedical" in tags["research_domains"]

    def test_cs_tags(self, rule_tagger):
        tags = rule_tagger.tag("Machine learning and deep learning algorithms.")
        assert "computer_science" in tags["research_domains"]

    def test_population_tags(self, rule_tagger):
        tags = rule_tagger.tag("Study of elderly veterans with disabilities.")
        pops = tags["populations"]
        assert "elderly" in pops or "veterans" in pops

    def test_empty_text(self, rule_tagger):
        tags = rule_tagger.tag("")
        for cat in tags.values():
            assert isinstance(cat, list)

    def test_determinism(self, rule_tagger):
        text = "Machine learning for cancer detection in pediatric patients."
        tags1 = rule_tagger.tag(text)
        tags2 = rule_tagger.tag(text)
        assert tags1 == tags2

    def test_all_categories_present(self, rule_tagger):
        tags = rule_tagger.tag("some text")
        from pipeline.tagging.ontology import _DEFAULT_ONTOLOGY
        import json
        with open(_DEFAULT_ONTOLOGY) as f:
            ontology_data = json.load(f)
        for cat in ontology_data:
            assert cat in tags


# ── Hybrid tagger tests ───────────────────────────────────────────────────────

class TestHybridTagger:
    def test_tags_foa_record(self, hybrid_tagger, sample_record):
        tags = hybrid_tagger.tag(sample_record)
        assert isinstance(tags, dict)
        assert "research_domains" in tags
        assert "biomedical" in tags["research_domains"] or "computer_science" in tags["research_domains"]

    def test_tags_text(self, hybrid_tagger):
        tags = hybrid_tagger.tag_text("Climate change and biodiversity conservation.")
        assert "environmental" in tags["research_domains"]


# ── Export tests ──────────────────────────────────────────────────────────────

class TestExport:
    def test_json_export(self, sample_record, tmp_path):
        path = export_json(sample_record, tmp_path)
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert data["foa_id"] == "PAR-24-001"
        assert data["title"] == sample_record.title
        assert "tags" in data

    def test_csv_export(self, sample_record, tmp_path):
        import csv
        path = export_csv(sample_record, tmp_path)
        assert path.exists()
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["foa_id"] == "PAR-24-001"
        assert rows[0]["award_max"] == "2000000"

    def test_csv_fieldnames(self):
        fields = FOARecord.csv_fieldnames()
        required = ["foa_id", "title", "agency", "open_date", "close_date",
                    "award_min", "award_max", "source_url"]
        for f in required:
            assert f in fields

    def test_foa_store(self, sample_record, tmp_path):
        store_path = tmp_path / "store.jsonl"
        store = FOAStore(store_path)
        assert not store.contains(sample_record.foa_id)
        store.upsert(sample_record)
        assert store.contains(sample_record.foa_id)

        # Reload and check persistence
        store2 = FOAStore(store_path)
        assert store2.contains(sample_record.foa_id)

    def test_foa_store_upsert_no_duplicate_lines(self, sample_record, tmp_path):
        store_path = tmp_path / "store.jsonl"
        store = FOAStore(store_path)

        changed = store.upsert(sample_record)
        assert changed is True
        changed = store.upsert(sample_record)
        assert changed is False

        with open(store_path, "r", encoding="utf-8") as fh:
            lines = [line for line in fh if line.strip()]
        assert len(lines) == 1


# ── Evaluation tests ──────────────────────────────────────────────────────────

class TestEvaluation:
    def test_compute_metrics(self):
        preds = [{"research_domains": ["biomedical", "computer_science"]}]
        gold = [{"research_domains": ["biomedical"]}]
        report = compute_metrics(preds, gold)
        assert report.per_category["research_domains"].precision == 0.5
        assert report.per_category["research_domains"].recall == 1.0

    def test_eval_dataset_structure(self):
        for ex in EVAL_DATASET:
            assert "id" in ex
            assert "description" in ex
            assert "gold_tags" in ex
            for cat in ["research_domains", "methods_approaches", "populations", "sponsor_themes"]:
                assert cat in ex["gold_tags"]

    def test_run_evaluation(self, hybrid_tagger):
        report = run_evaluation(hybrid_tagger, verbose=False)
        assert report.n_examples == len(EVAL_DATASET)
        assert 0.0 <= report.macro_f1 <= 1.0

    def test_evaluation_report_to_dict(self, hybrid_tagger):
        report = run_evaluation(hybrid_tagger, verbose=False)
        d = report.to_dict()
        assert "macro_precision" in d
        assert "macro_recall" in d
        assert "macro_f1" in d
        assert "per_category" in d

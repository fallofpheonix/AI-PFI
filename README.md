# FOA Intelligence Pipeline

An open-source pipeline that automatically ingests Funding Opportunity Announcements (FOAs) from public sources, extracts structured fields, and applies ontology-based semantic tags to support institutional research discovery and grant matching.

## Features

- **Multi-source ingestion** — Grants.gov, NSF, NIH (with API + HTML scraping + PDF fallback)
- **Structured extraction** — Normalizes all FOAs into a consistent JSON/CSV schema
- **Hybrid semantic tagging** — Rule-based + embedding similarity against a controlled ontology
- **LLM tagging** (stretch) — Optional Claude/OpenAI-assisted classification
- **Persistent store** — Incremental update workflow (JSON-lines, skip already-ingested FOAs)
- **Vector search** (stretch) — FAISS/Chroma similarity search
- **Evaluation suite** — 8-example gold-standard dataset with precision/recall/F1 metrics

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

For embedding-based tagging (recommended):
```bash
pip install sentence-transformers
```

### 2. Run the screening task (single FOA)

```bash
python main.py --url "https://www.grants.gov/web/grants/view-opportunity.html?oppId=350002" --out_dir ./out
```

Outputs:
```
out/foa.json
out/foa.csv
```

### 3. Batch ingest

```bash
python main.py --batch urls.txt --out_dir ./out
```

`urls.txt` — one URL per line (lines starting with `#` are ignored).

### 4. Run evaluation

```bash
python main.py --evaluate --out_dir ./out
```

Outputs `out/evaluation_report.json` with precision/recall/F1 per tag category.

### 5. Enable LLM tagging (stretch goal)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python main.py --url "..." --out_dir ./out --llm
```

---

## Output Schema

Every processed FOA produces a record conforming to this schema (`schema_version: "1.0"`):

| Field | Type | Description |
|-------|------|-------------|
| `foa_id` | string | Funding opportunity number (generated if missing) |
| `title` | string | FOA title |
| `agency` | string | Funding agency name |
| `open_date` | ISO-8601 | Date posted / open |
| `close_date` | ISO-8601 | Application deadline |
| `eligibility` | string | Eligible applicant types |
| `description` | string | Program description / synopsis |
| `award_range.min` | int | Minimum award amount (USD) |
| `award_range.max` | int | Maximum award amount (USD) |
| `source_url` | string | Original FOA URL |
| `source_name` | string | `grants.gov` / `nsf` / `nih` |
| `ingested_at` | ISO-8601 datetime | Pipeline ingestion timestamp |
| `tags.research_domains` | list[string] | Ontology subcategory labels |
| `tags.methods_approaches` | list[string] | Ontology subcategory labels |
| `tags.populations` | list[string] | Ontology subcategory labels |
| `tags.sponsor_themes` | list[string] | Ontology subcategory labels |
| `schema_version` | string | `"1.0"` |

---

## Project Structure

```
foa-pipeline/
├── main.py                          # CLI entry point
├── requirements.txt
├── README.md
│
├── pipeline/
│   ├── __init__.py                  # Pipeline orchestrator class
│   │
│   ├── ingestion/
│   │   ├── base.py                  # BaseIngester + RawFOA dataclass
│   │   ├── grants_gov.py            # Grants.gov (API + HTML)
│   │   ├── nsf.py                   # NSF (API + HTML + PDF)
│   │   ├── nih.py                   # NIH (Reporter API + Guide pages)
│   │   └── __init__.py              # IngestionRouter
│   │
│   ├── extraction/
│   │   ├── html_extractor.py        # Regex/heuristic field extractor
│   │   ├── pdf_extractor.py         # PDF → text (pdfminer / pypdf)
│   │   ├── normalizer.py            # FOARecord schema + FOANormalizer
│   │   └── __init__.py
│   │
│   ├── tagging/
│   │   ├── ontology.py              # Ontology loader
│   │   ├── rule_based.py            # Keyword/regex tagger
│   │   ├── embedding_tagger.py      # sentence-transformers tagger
│   │   ├── tagger.py                # HybridTagger (union strategy)
│   │   └── __init__.py
│   │
│   ├── storage/
│   │   ├── exporter.py              # JSON/CSV export + FOAStore
│   │   └── __init__.py
│   │
│   └── evaluation/
│       ├── metrics.py               # eval dataset + P/R/F1 computation
│       └── __init__.py
│
├── ontology/
│   └── foa_ontology.json            # Controlled ontology (4 categories)
│
├── out/                             # Default output directory
│   ├── foa.json
│   └── foa.csv
│
└── tests/
    └── test_pipeline.py             # pytest test suite (31 tests)
```

---

## Ontology

The controlled ontology (`ontology/foa_ontology.json`) covers four top-level categories with subcategory labels and associated keyword terms:

| Category | Subcategories (examples) |
|----------|--------------------------|
| `research_domains` | biomedical, computer_science, engineering, environmental, social_sciences, ... |
| `methods_approaches` | experimental, computational, ai_ml, systematic_review, mixed_methods, ... |
| `populations` | pediatric, elderly, minority, rural, veterans, global, ... |
| `sponsor_themes` | workforce_development, innovation, equity_inclusion, early_career, ... |

---

## Tagging Architecture

```
FOA Text
   │
   ├──▶ RuleBasedTagger      (regex keyword matching — deterministic, high precision)
   │         │
   └──▶ EmbeddingTagger      (cosine similarity via sentence-transformers — semantic coverage)
             │
             ▼
         HybridTagger         (union merge: include tag if either method fires)
             │
             ▼ (optional)
         LLM Classifier       (Claude/OpenAI — stretch goal, requires API key)
```

---

## Supported Sources

| Source | URL patterns | Method |
|--------|-------------|--------|
| Grants.gov | `grants.gov/...?oppId=...` | REST API + HTML scraping |
| NSF | `nsf.gov/...` | API + HTML + PDF |
| NIH | `grants.nih.gov/...`, `nih.gov/...` | Reporter API + Guide pages |

---

## CLI Reference

```
python main.py [OPTIONS]

Options:
  --url URL             FOA URL to ingest
  --out_dir DIR         Output directory (default: ./out)
  --batch FILE          File with one URL per line
  --no-embeddings       Disable embedding-based tagging
  --llm                 Enable LLM-assisted tagging
  --evaluate            Run built-in evaluation suite
  --store FILE          Path to persistent JSON-lines store
  --ontology FILE       Path to custom ontology JSON
  --verbose / -v        Enable debug logging
```

---

## Running Tests

```bash
# With pytest (if installed):
pytest tests/ -v

# Without pytest:
python -m unittest tests.test_pipeline -v
```

---

## Stretch Goals

| Goal | Status | Notes |
|------|--------|-------|
| NIH source | ✅ Implemented | `pipeline/ingestion/nih.py` |
| LLM tagging | ✅ Implemented | Pass `--llm` flag + set API key |
| Vector indexing | 🔲 Scaffold ready | Uncomment FAISS/Chroma in `requirements.txt` |
| Search UI | 🔲 Planned | CLI search via `--query` flag |

---

## Reproducibility

1. Clone repository
2. `pip install -r requirements.txt`
3. `python main.py --url "<your-url>" --out_dir ./out`

All outputs are deterministic for identical input text when using rule-based tagging only (`--no-embeddings`). Embedding-based tags may vary slightly across hardware due to floating-point precision.

---

## License

MIT License. See `LICENSE` for details.

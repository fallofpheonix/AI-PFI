# System Architecture

## Design Principles

- Separate source-specific ingestion from source-agnostic normalization.
- Keep semantic tagging auditable and modular.
- Use a canonical FOA record as the contract between modules.
- Make generated outputs reproducible and easy to inspect.

## Module Layout

### `pipeline/ingestion`

Responsible for retrieving raw FOA content from external sources.

Key responsibilities:
- route by URL pattern
- fetch HTML or API payloads
- retrieve linked PDF bytes when required
- preserve source metadata

### `pipeline/extraction`

Responsible for extracting structured candidate fields from raw content.

Key responsibilities:
- HTML text extraction
- PDF text extraction
- date parsing
- award range extraction
- section-level heuristics for title, description, and eligibility

### `pipeline/extraction/normalizer.py`

Responsible for converting extracted fields into a canonical FOA schema.

Key responsibilities:
- whitespace cleanup
- field validation
- FOA ID generation when absent
- ISO-format normalization

### `pipeline/tagging`

Responsible for semantic tagging against the ontology.

Components:
- `rule_based.py`
- `embedding_tagger.py`
- `tagger.py`

Current strategy:
- rules provide high-precision deterministic matches
- embeddings expand recall using semantic similarity
- optional LLM tagging is merged as an extension path

### `pipeline/storage`

Responsible for export and incremental persistence.

Key responsibilities:
- JSON export
- CSV export
- JSONL-backed update store

### `pipeline/evaluation`

Responsible for benchmark loading and metric computation.

Current state:
- built-in evaluation dataset
- multi-label precision/recall/F1
- bootstrap confidence interval support

## Canonical Data Flow

```text
FOA URL
  -> ingestion router
  -> source adapter
  -> raw payload
  -> HTML/PDF extraction
  -> normalized FOARecord
  -> hybrid tagger
  -> export/store
  -> evaluation or downstream integration
```

## Canonical Record

The normalized FOA record is the project contract. It must carry:
- source provenance
- normalized metadata
- cleaned narrative fields
- semantic tags

This separation prevents downstream modules from depending on raw HTML layout details.

## Extension Strategy

New source:
- add a new adapter under `pipeline/ingestion`
- reuse extraction and normalization where possible

New tagging method:
- implement a new tagging component under `pipeline/tagging`
- merge at the `HybridTagger` layer

New export target:
- extend `pipeline/storage` without changing normalization or tagging modules

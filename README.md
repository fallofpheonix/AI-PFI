# AI-Powered Funding Intelligence

Open-source pipeline for ingesting Funding Opportunity Announcements (FOAs), extracting structured funding metadata, and applying ontology-based semantic tags for downstream research discovery and grant matching.

## Purpose

This repository is being organized as a documentation-first engineering base for future development. The primary project knowledge now lives in the markdown files under `docs/` and in this `README.md`.

## Primary Documentation

- [Project Scope](docs/PROJECT_SCOPE.md)
- [System Architecture](docs/ARCHITECTURE.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [Evaluation Plan](docs/EVALUATION.md)
- [GSoC Proposal Draft](docs/GSOC_PROPOSAL.md)
- [Contribution Guide](CONTRIBUTING.md)

## Current Repository Scope

Core pipeline capabilities in the codebase:
- Multi-source FOA ingestion via public agency pages and APIs
- Structured extraction and schema normalization
- Hybrid semantic tagging:
  - deterministic rule-based tagging
  - embedding similarity tagging
  - optional LLM-assisted tagging
- JSON and CSV export
- Basic built-in evaluation utilities

## Quick Start

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Process a single FOA:

```bash
python main.py --url "https://www.grants.gov/web/grants/view-opportunity.html?oppId=350002" --out_dir ./out --no-embeddings
```

Run the built-in evaluation:

```bash
python main.py --evaluate --out_dir ./out --no-embeddings
```

## Repository Layout

```text
main.py
ontology/
pipeline/
tests/
docs/
CONTRIBUTING.md
requirements.txt
```

## Development Status

The repository contains a working baseline implementation. The next phase is to harden it into a maintainable open-source project with:
- clearer documentation ownership
- stronger evaluation discipline
- cleaner reproducibility controls
- a roadmap aligned to future HumanAI/ISSR integration

## Notes

- Generated outputs under `out/` are intentionally not versioned.
- Validation logs and temporary review artifacts are intentionally not versioned.
- Historical local documents have been migrated into canonical `docs/` files and removed from the working tree.

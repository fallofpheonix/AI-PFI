# Project Scope

## Project

AI-Powered Funding Intelligence (FOA Ingestion + Semantic Tagging)

## Objective

Build an open-source pipeline that:
- ingests FOAs from at least two public sources
- normalizes them into a consistent machine-readable schema
- applies ontology-based semantic tags
- exports reproducible outputs for downstream grant matching and discovery workflows

## Problem

Funding Opportunity Announcements are distributed across multiple agencies and formats. They are difficult to process at scale because:
- agency websites expose inconsistent HTML structures
- some opportunities require PDF parsing
- fields such as award range and eligibility are often semi-structured
- manual categorization is slow and not reproducible

## In-Scope Deliverables

- Source adapters for at least two agencies
- HTML and PDF ingestion support
- Canonical FOA schema with normalized fields:
  - FOA ID
  - title
  - agency
  - open date
  - close date
  - eligibility
  - description
  - award range
  - source URL
- Controlled ontology for semantic tagging
- Hybrid tagging implementation
- JSON and CSV export
- Update workflow for incremental ingestion
- Basic evaluation utilities and benchmark dataset

## Out of Scope for the Core Build

- Full production grant recommendation system
- Institution-specific investigator ranking
- Large-scale annotation platform
- Full UI product
- Hard real-time synchronization with agency feeds

## Engineering Constraints

- Python is the implementation language.
- The pipeline must be CLI-driven and reproducible.
- Core behavior must remain deterministic when LLM mode is disabled.
- All output records must conform to a documented schema.
- The architecture must support adding new agencies without rewriting the full pipeline.

## Success Criteria

- A reviewer can run the CLI against a supported FOA URL and obtain valid `JSON` and `CSV` outputs.
- The codebase has source separation between ingestion, extraction, normalization, tagging, storage, and evaluation.
- The tagging system produces auditable multi-label outputs aligned to the ontology.
- Repository documentation is sufficient to continue development without relying on external notes.

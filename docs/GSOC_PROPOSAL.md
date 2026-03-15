# GSoC Proposal Draft

## Project Title

AI-Powered Funding Intelligence: Modular FOA Ingestion, Normalization, and Semantic Tagging Pipeline

## Abstract

Funding Opportunity Announcements are distributed across multiple public agency sites, vary substantially in structure, and require labor-intensive manual review before they become useful to research development teams. The proposed project builds an open-source Python pipeline that ingests FOAs from at least two public sources, extracts key metadata into a canonical schema, and applies ontology-based semantic tagging to create structured, queryable funding intelligence.

The implementation focuses on engineering practicality: source adapters for heterogeneous agency content, normalized JSON and CSV outputs, deterministic rule-based tagging augmented with embedding similarity, and a documented update workflow for ingesting new announcements. The architecture is intentionally modular so that additional sources, search layers, or grant-matching systems can be added without rewriting the core pipeline.

The expected impact is a reusable infrastructure layer for HumanAI and ISSR. Instead of a one-off scraper, the project delivers a maintainable ingestion and tagging system that reduces manual FOA processing, improves discoverability of opportunities, and creates a stable foundation for downstream institutional workflows.

## Problem Statement

Research development teams spend substantial time reading, filtering, and circulating FOAs because agencies publish opportunities with inconsistent page structures, uneven metadata quality, and mixed HTML/PDF delivery. Existing ad hoc scripts are usually source-specific and fragile, while manual categorization is slow and not reproducible.

The project addresses three technical gaps:
- robust multi-source FOA ingestion
- schema normalization into a canonical record
- semantic tagging aligned to a controlled ontology

This matters because downstream grant matching and institutional discovery require structured records, not just raw text.

## Constraints and Assumptions

- Support at least two public sources in the core scope.
- Handle HTML first, with PDF fallback where needed.
- Keep the pipeline CLI-driven and reproducible.
- Treat LLM support as optional and non-blocking.
- Build for extension, not for immediate full-scale production search or recommendation.

## Proposed Solution

Core architecture:
- ingestion router
- source adapters
- extraction utilities
- schema normalizer
- hybrid tagger
- export and update workflow
- evaluation utilities

Flow:

```text
URL -> adapter -> raw content -> extraction -> normalization -> tagging -> export
```

Tagging strategy:
- deterministic rule-based matching for precision
- embedding similarity for semantic recall
- optional LLM classification for ambiguous cases

## Technical Methodology

Technologies:
- Python
- requests
- BeautifulSoup4
- pypdf or pdfminer.six
- sentence-transformers
- pytest

Implementation approach:
- isolate source-specific code in adapter modules
- keep a single FOA schema between extraction and tagging
- version the ontology as data
- make exports simple and interoperable

Testing:
- unit tests for parsers and taggers
- integration tests for supported sources
- regression fixtures for extraction failures

Evaluation:
- multi-label precision/recall/F1
- rule-based vs hybrid comparison
- documented benchmark limitations

## Timeline Summary

- Weeks 1-2: repository structure, schema, source router
- Weeks 3-4: Grants.gov and NSF ingestion
- Weeks 5-6: normalization and export
- Weeks 7-8: rule-based and embedding tagging
- Weeks 9-10: evaluation and error analysis
- Weeks 11-12: hardening, documentation, and stretch work

## Expected Outcomes

- multi-source FOA ingestion pipeline
- normalized JSON and CSV outputs
- ontology-driven semantic tagging module
- reproducible development and evaluation documentation
- foundation for future search and matching systems

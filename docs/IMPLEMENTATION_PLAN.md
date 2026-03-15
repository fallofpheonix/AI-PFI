# Implementation Plan

## Phase 1 - Repository Hardening

- make documentation the primary project reference
- clean generated artifacts from version control
- define the canonical module responsibilities
- align CLI, schema, and docs

## Phase 2 - Ingestion Stability

- verify Grants.gov and NSF ingestion paths against saved fixtures
- isolate brittle parsing logic behind source-specific adapters
- improve timeout handling, error reporting, and malformed response handling
- add regression fixtures for supported sources

## Phase 3 - Extraction and Normalization Quality

- improve field extraction coverage for title, dates, eligibility, and award range
- document fallback behavior for missing fields
- tighten normalization invariants on dates, IDs, and text cleanup
- add fixture-driven unit tests for extraction edge cases

## Phase 4 - Semantic Tagging Quality

- review ontology coverage and tagging conflicts
- keep deterministic rules as the precision-oriented baseline
- calibrate embedding threshold on a separate validation set once one exists
- add ablation reporting for rules-only, embedding-enabled, and optional LLM variants

## Phase 5 - Reproducibility and Evaluation

- move from convenience evaluation to documented benchmark protocol
- define a small but independent benchmark process
- record model IDs, ontology version, threshold, and run configuration
- produce stable evaluation artifacts from code, not hand-maintained notes

## Phase 6 - Future Integration Readiness

- document storage interfaces for future search or grant-matching integration
- prepare for additional sources such as NIH
- keep interfaces narrow enough for future UI, vector indexing, or recommender layers

## Target Milestones

- M1: Documentation-first repo structure complete
- M2: Two-source ingestion stable on saved fixtures
- M3: Canonical extraction and export path hardened
- M4: Tagging ablation and evaluation plan documented
- M5: Repository ready for sustained open-source iteration

## 12-Week GSoC-Oriented Roadmap

### Community Bonding

- confirm scope and success criteria with mentors
- review target source formats and failure cases
- finalize schema and ontology governance

### Week 1

- repository cleanup
- docs-first restructuring
- development workflow setup

### Week 2

- ingestion router review
- Grants.gov source verification

### Week 3

- NSF source verification
- PDF extraction edge-case testing

### Week 4

- normalization invariants
- export contract review

### Week 5

- deterministic rule-based tagging refinement
- ontology cleanup and documentation

### Week 6

- embedding tagging review
- threshold parameterization and ablation wiring

### Week 7

- incremental update workflow hardening
- batch ingestion path review

### Week 8

- benchmark curation
- evaluation reporting and reproducibility metadata

### Week 9

- source-specific bug fixing from error analysis
- regression fixture expansion

### Week 10

- documentation pass
- contribution workflow stabilization

### Week 11

- stretch window:
  - additional source, or
  - optional LLM path hardening, or
  - search/indexing groundwork

### Week 12

- final integration cleanup
- final report, demo path, and maintainer handoff documentation

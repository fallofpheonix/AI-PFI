# Evaluation Plan

## Purpose

Evaluation should measure tagging quality on unseen FOAs, not just agreement with ontology-authored examples.

## Current State

The repository currently includes a small built-in benchmark for convenience testing. It is useful for smoke checks and regression detection, but it is not sufficient as a final external-quality estimate because:
- the dataset is very small
- examples are synthetic
- ontology terms overlap strongly with benchmark text

## Required Evaluation Principles

- Use a held-out dataset for final reporting.
- Keep threshold calibration on validation data only.
- Report rule-based and hybrid variants separately.
- Treat semantic tagging as multi-label evaluation.

## Minimum Metrics

- macro precision
- macro recall
- macro F1
- micro precision
- micro recall
- micro F1
- per-category support

## Recommended Benchmark Structure

- Train or calibration split:
  - ontology/rule refinement
  - threshold exploration
- Validation split:
  - threshold selection
  - ablation comparisons
- Test split:
  - final untouched reporting

## Benchmark Construction Rules

- Use real FOAs from supported sources.
- Do not author the evaluation text to match ontology terms.
- Keep records deduplicated by stable FOA identity.
- Store annotation provenance and labeling instructions.

## Ablations

Required comparisons:
- rules only
- hybrid without LLM
- hybrid with LLM if enabled

Recommended additions:
- embedding-only baseline
- trivial baseline for category frequency

## Reproducibility Requirements

Every evaluation run should record:
- ontology version
- model IDs
- embedding threshold
- bootstrap seed
- dataset identifier or hash
- CLI configuration used

## Immediate Repository Goal

Short term:
- keep the built-in dataset as a regression check only
- document its limitations clearly

Next step:
- replace it with an independently constructed benchmark suitable for real reporting

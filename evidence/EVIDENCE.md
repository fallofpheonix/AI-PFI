# Validation Evidence

This directory contains 3 independent validation evidences.

## Evidence 1: Unit/Integration Test Pass
- File: `evidence/01_pytest.log`
- Validation: full test suite execution result
- Expected indicator: `35 passed`

## Evidence 2: Tagging Evaluation Metrics
- File: `evidence/02_evaluation.log`
- Validation: reproducible evaluation run over built-in dataset
- Expected indicators: macro precision/recall/F1 values

## Evidence 3: Real FOA End-to-End Run
- File: `evidence/03_foa_run.log`
- Validation: URL ingestion + extraction + tagging + export
- Expected indicators: populated FOA ID/title/agency and output paths

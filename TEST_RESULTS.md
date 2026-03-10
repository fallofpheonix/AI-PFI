# Test Results

Last verified: 2026-03-10 23:23:09 IST

## Environment
- Python virtual environment: `.venv`
- Working directory: `/Users/fallofpheonix/Project/Human AI/AI-PFI`

## Commands Executed
- `pytest -q tests/test_pipeline.py`
- `python main.py --evaluate --out_dir ./out --no-embeddings`
- `python main.py --url "https://www.grants.gov/web/grants/view-opportunity.html?oppId=350002" --out_dir ./out --no-embeddings`

## Results Summary
- Tests: **35 passed**
- Evaluation examples: **8**
- Macro Precision: **0.9479**
- Macro Recall: **0.7079**
- Macro F1: **0.8048**

## FOA Output Check (`out/foa.json`)
- `foa_id`: `350002`
- `title`: `Accelerating Research through International Network-to-Network Collaborations`
- `agency`: `U.S. National Science Foundation`
- `open_date`: `2023-08-26`
- `close_date`: `2026-09-21`

## Evidence Files
- `evidence/01_pytest.log`
- `evidence/02_evaluation.log`
- `evidence/03_foa_run.log`

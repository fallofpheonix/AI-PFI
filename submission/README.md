# AI-PFI

AI-PFI ingests funding opportunity pages (Grants.gov, NSF, NIH), extracts normalized FOA metadata, and tags records using a lightweight ontology.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py --url "https://www.grants.gov/web/grants/view-opportunity.html?oppId=350002" --out_dir out --no-embeddings
python main.py --evaluate --out_dir out --no-embeddings
```

## Project layout

```text
src/
  api/       # CLI entrypoints and argument handling
  core/      # domain record schema + normalization rules
  services/  # orchestration and source-facing use-cases
  utils/     # cross-cutting helpers (logging)
  config/    # environment-backed app settings
  pipeline/  # legacy compatibility package (gradual migration)
tests/       # critical-path tests only
docs/        # architecture and planning documents
```

## Key decisions

- Keep a service layer between CLI and pipeline modules so behavior can be tested without network calls.
- Preserve `pipeline.*` imports for compatibility while moving new work into `core/` + `services/`.
- Prefer deterministic defaults (`--no-embeddings`) for CI and reproducibility.

## Notes

- `.env.example` documents the small runtime surface we currently support.
- `out/` and local virtualenvs are intentionally ignored.

# Contributing

## Project Priorities

This repository is currently in a cleanup and hardening phase. Contributions should prioritize:
- source adapter stability
- extraction correctness
- schema consistency
- evaluation rigor
- documentation quality

## Development Workflow

1. Create a branch from `main`.
2. Keep changes scoped to one concern when possible.
3. Add or update tests for parser, extraction, or tagging behavior.
4. Update the relevant markdown in `docs/` when behavior or scope changes.

## Code Guidelines

- Prefer deterministic behavior by default.
- Keep source-specific logic isolated from canonical normalization.
- Avoid introducing heavy dependencies without a clear operational reason.
- Treat ontology changes as data changes that require documentation.

## Testing Expectations

Before opening a change:

```bash
python -m pytest tests/ -v
```

If source behavior changes, also verify:
- a representative supported FOA URL
- JSON export shape
- CSV export shape

## Documentation Ownership

Primary repository knowledge must live in:
- `README.md`
- `docs/PROJECT_SCOPE.md`
- `docs/ARCHITECTURE.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/EVALUATION.md`

Do not store long-term project decisions only in temporary notes or generated logs.

## Pull Request Expectations

- explain the problem being solved
- describe design tradeoffs
- include validation steps
- call out any schema or ontology changes explicitly

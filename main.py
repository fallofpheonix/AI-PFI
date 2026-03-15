#!/usr/bin/env python3
"""
FOA Intelligence Pipeline — CLI Entry Point
============================================

Screening-task compatible usage:
    python main.py --url "https://www.grants.gov/..." --out_dir ./out

Full options:
    python main.py --url URL --out_dir ./out [--no-embeddings] [--llm] [--evaluate] [--batch FILE]

Outputs:
    <out_dir>/foa.json
    <out_dir>/foa.csv
"""

import argparse
import json
import logging
import sys
import os
from pathlib import Path

# ── Make sure the project root and src/ are on sys.path ────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FOA Intelligence Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single FOA — Grants.gov
  python main.py --url "https://www.grants.gov/web/grants/view-opportunity.html?oppId=350002" --out_dir ./out

  # Single FOA — NSF
  python main.py --url "https://www.nsf.gov/pubs/2023/nsf23615/nsf23615.htm" --out_dir ./out

  # Batch ingest from a file of URLs (one per line)
  python main.py --batch urls.txt --out_dir ./out

  # Run evaluation
  python main.py --evaluate --out_dir ./out

  # Enable LLM tagging (requires ANTHROPIC_API_KEY or OPENAI_API_KEY)
  python main.py --url "..." --out_dir ./out --llm
        """,
    )
    parser.add_argument("--url", type=str, help="FOA URL to ingest (Grants.gov / NSF / NIH)")
    parser.add_argument("--out_dir", type=str, default="./out", help="Output directory (default: ./out)")
    parser.add_argument("--batch", type=str, help="File containing one URL per line for batch processing")
    parser.add_argument("--no-embeddings", action="store_true", help="Disable embedding-based tagging")
    parser.add_argument("--llm", action="store_true", help="Enable LLM-assisted tagging (stretch goal)")
    parser.add_argument("--evaluate", action="store_true", help="Run evaluation on built-in eval dataset")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    parser.add_argument("--store", type=str, help="Path to persistent JSON-lines store for incremental updates")
    parser.add_argument("--ontology", type=str, help="Path to custom ontology JSON file")
    return parser


def process_single(pipeline, url: str, out_dir: str) -> int:
    """Process one URL. Returns exit code."""
    print(f"\n[FOA Pipeline] Processing: {url}")
    try:
        record = pipeline.process(url)
    except Exception as e:
        print(f"[ERROR] Failed to process URL: {e}", file=sys.stderr)
        logging.exception(e)
        return 1

    json_path, csv_path = pipeline.export(record, out_dir)

    print(f"\n{'='*60}")
    print(f"  FOA Record")
    print(f"{'='*60}")
    print(f"  ID         : {record.foa_id}")
    print(f"  Title      : {record.title[:80]}")
    print(f"  Agency     : {record.agency}")
    print(f"  Open       : {record.open_date or '—'}")
    print(f"  Close      : {record.close_date or '—'}")
    if record.award_range:
        lo = record.award_range.get("min")
        hi = record.award_range.get("max")
        print(f"  Award      : {f'${lo:,}' if lo else ''}{' – ' if lo and hi else ''}{f'${hi:,}' if hi else ''}")
    print(f"\n  Tags:")
    for cat, tags in record.tags.items():
        if tags:
            print(f"    {cat:<25} {', '.join(tags)}")
    print(f"\n  JSON → {json_path}")
    print(f"  CSV  → {csv_path}")
    print(f"{'='*60}\n")
    return 0


def process_batch(pipeline, batch_file: str, out_dir: str) -> int:
    """Process all URLs in a text file."""
    from pipeline.storage import export_batch_json, export_batch_csv

    with open(batch_file, "r") as fh:
        urls = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

    print(f"[FOA Pipeline] Batch mode: {len(urls)} URLs")
    records = []
    errors = 0
    for i, url in enumerate(urls, 1):
        print(f"  [{i}/{len(urls)}] {url}")
        try:
            record = pipeline.process(url)
            records.append(record)
        except Exception as e:
            print(f"    [ERROR] {e}", file=sys.stderr)
            errors += 1

    if records:
        export_batch_json(records, out_dir)
        export_batch_csv(records, out_dir)
        print(f"\n[Batch complete] {len(records)} succeeded, {errors} failed.")
        print(f"  Outputs in: {Path(out_dir).resolve()}")
    return 0 if errors == 0 else 1


def run_eval(pipeline, out_dir: str) -> int:
    """Run the built-in evaluation suite."""
    from pipeline.evaluation import run_evaluation
    import json

    print("\n[FOA Pipeline] Running evaluation on built-in dataset...")
    report = run_evaluation(pipeline.tagger, verbose=True)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    eval_path = out_dir / "evaluation_report.json"
    with open(eval_path, "w") as fh:
        json.dump(report.to_dict(), fh, indent=2)
    print(f"  Evaluation report → {eval_path}")
    return 0


def main():
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(args.verbose)

    if not args.url and not args.batch and not args.evaluate:
        parser.print_help()
        sys.exit(0)

    # Build pipeline
    from pipeline import Pipeline
    pipeline = Pipeline(
        use_embeddings=not args.no_embeddings,
        use_llm=args.llm,
        ontology_path=args.ontology,
        store_path=args.store,
    )

    exit_code = 0

    if args.evaluate:
        exit_code |= run_eval(pipeline, args.out_dir)

    if args.url:
        exit_code |= process_single(pipeline, args.url, args.out_dir)

    if args.batch:
        exit_code |= process_batch(pipeline, args.batch, args.out_dir)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

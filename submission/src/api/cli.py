from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from pathlib import Path

from config import load_settings
from services import FOAPipelineService
from utils.logging import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FOA Intelligence Pipeline")
    parser.add_argument("--url", type=str, help="Single FOA URL")
    parser.add_argument("--batch", type=str, help="Text file with one URL per line")
    parser.add_argument("--out_dir", type=str, default="./out")
    parser.add_argument("--no-embeddings", action="store_true")
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--store", type=str, help="JSONL store path")
    parser.add_argument("--ontology", type=str, help="Custom ontology path")
    return parser


def _load_batch_urls(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as handle:
        urls = [line.strip() for line in handle if line.strip() and not line.strip().startswith("#")]
    deduped = list(dict.fromkeys(urls))
    return deduped


def _print_record(record, json_path, csv_path) -> None:
    print(f"\n[FOA] {record.foa_id} — {record.title[:90]}")
    print(f"  agency: {record.agency or 'unknown'}")
    print(f"  open: {record.open_date or 'n/a'}  close: {record.close_date or 'n/a'}")
    print(f"  json: {json_path}")
    print(f"  csv:  {csv_path}")


def _process_single(service: FOAPipelineService, url: str, out_dir: str) -> int:
    try:
        record = service.process_url(url)
    except Exception as exc:
        print(f"[ERROR] Failed to process {url}: {exc}", file=sys.stderr)
        return 1

    json_path, csv_path = service.exporter.export_single(record, out_dir)
    _print_record(record, json_path, csv_path)
    return 0


def _process_batch(service: FOAPipelineService, batch_file: str, out_dir: str) -> int:
    urls = _load_batch_urls(batch_file)
    if not urls:
        print("[WARN] No URLs in batch file")
        return 0

    print(f"[FOA] Processing batch of {len(urls)} URLs")
    processed = []
    failed = 0

    # TODO: Make worker count configurable once we collect runtime telemetry.
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(service.process_url, url): url for url in urls}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            url = futures[future]
            try:
                record = future.result()
                processed.append(record)
                print(f"  [{index}/{len(urls)}] ok: {record.foa_id} ({url})")
            except Exception as exc:
                failed += 1
                print(f"  [{index}/{len(urls)}] fail: {url} ({exc})", file=sys.stderr)

    batch_json, batch_csv = service.exporter.export_batch(processed, out_dir)
    print(f"[FOA] Batch export: {batch_json}, {batch_csv}")
    return 0 if failed == 0 else 1


def _run_eval(service: FOAPipelineService, out_dir: str) -> int:
    report = service.evaluation.run(verbose=True)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    report_path = out_path / "evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2)
    print(f"[FOA] Evaluation report: {report_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.url and not args.batch and not args.evaluate:
        parser.print_help()
        return 0

    settings = load_settings()
    configure_logging(verbose=args.verbose)

    # Why: sentence-transformers defaults can fail in restricted environments.
    import os

    os.environ["HF_HOME"] = settings.huggingface_cache_dir

    service = FOAPipelineService(
        use_embeddings=not args.no_embeddings,
        use_llm=args.llm,
        ontology_path=args.ontology,
        store_path=args.store,
    )

    code = 0
    if args.evaluate:
        code |= _run_eval(service, args.out_dir)
    if args.url:
        code |= _process_single(service, args.url, args.out_dir)
    if args.batch:
        code |= _process_batch(service, args.batch, args.out_dir)
    return code

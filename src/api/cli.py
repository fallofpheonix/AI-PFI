from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import sys
from pathlib import Path

import requests

from config import settings
from services import FOAPipelineService
from core.exceptions import ParseError

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FOA Intelligence Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Process/Ingest command (default behavior)
    process_parser = subparsers.add_parser("process", help="Ingest FOAs from URLs")
    process_parser.add_argument("--url", type=str, help="Single FOA URL")
    process_parser.add_argument("--batch", type=str, help="Text file with one URL per line")
    process_parser.add_argument("--out_dir", type=str, default="./out")
    process_parser.add_argument("--no-embeddings", action="store_true")
    process_parser.add_argument("--llm", action="store_true")
    process_parser.add_argument("--evaluate", action="store_true")
    process_parser.add_argument("--store", type=str, help="JSONL store path")
    process_parser.add_argument("--ontology", type=str, help="Custom ontology path")
    
    # Serve command
    subparsers.add_parser("serve", help="Start the FastAPI server")
    
    # Dashboard command
    subparsers.add_parser("dashboard", help="Start the Streamlit dashboard")
    
    # Global args
    parser.add_argument("--verbose", "-v", action="store_true")
    
    return parser


def _load_batch_urls(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as handle:
        urls = [line.strip() for line in handle if line.strip() and not line.strip().startswith("#")]
    deduped = list(dict.fromkeys(urls))
    return deduped


def _print_record(record, json_path, csv_path) -> None:
    logger.info(f"FOA Processed: {record.foa_id} — {record.title[:90]}")
    logger.info(f"  agency: {record.agency or 'unknown'}")
    logger.info(f"  open: {record.open_date or 'n/a'}  close: {record.close_date or 'n/a'}")
    logger.info(f"  json: {json_path}")
    logger.info(f"  csv:  {csv_path}")


def _process_single(service: FOAPipelineService, url: str, out_dir: str) -> int:
    try:
        record = service.process_url(url)
    except (requests.Timeout, requests.ConnectionError) as exc:
        logger.error(f"Network error processing {url}: {exc}")
        return 1
    except (ValueError, ParseError) as exc:
        logger.error(f"Data error processing {url}: {exc}")
        return 1
    except Exception as exc:
        logger.error(f"Unexpected error processing {url}: {exc}")
        return 1

    json_path, csv_path = service.exporter.export_single(record, out_dir)
    _print_record(record, json_path, csv_path)
    return 0


def _process_batch(service: FOAPipelineService, batch_file: str, out_dir: str) -> int:
    urls = _load_batch_urls(batch_file)
    if not urls:
        logger.warning("No URLs in batch file")
        return 0

    logger.info(f"Processing batch of {len(urls)} URLs")
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
                logger.info(f"  [{index}/{len(urls)}] ok: {record.foa_id} ({url})")
            except (requests.Timeout, requests.ConnectionError) as exc:
                failed += 1
                logger.error(f"  [{index}/{len(urls)}] fail (network): {url} ({exc})")
            except (ValueError, ParseError) as exc:
                failed += 1
                logger.error(f"  [{index}/{len(urls)}] fail (data): {url} ({exc})")
            except Exception as exc:
                failed += 1
                logger.error(f"  [{index}/{len(urls)}] fail (unexpected): {url} ({exc})")

    batch_json, batch_csv = service.exporter.export_batch(processed, out_dir)
    logger.info(f"Batch export: {batch_json}, {batch_csv}")
    return 0 if failed == 0 else 1


def _run_eval(service: FOAPipelineService, out_dir: str) -> int:
    report = service.evaluation.run(verbose=True)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    report_path = out_path / "evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2)
    logger.info(f"Evaluation report: {report_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    
    # For compatibility, if no command is given but args are, 
    # we default to "process" if --url or --batch or --evaluate is present.
    if argv and not any(arg in {"process", "serve"} for arg in argv):
        if any(arg in {"--url", "--batch", "--evaluate"} for arg in argv):
            argv.insert(0, "process")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    # Why: sentence-transformers defaults can fail in restricted environments.
    import os
    if settings.HF_HOME:
        os.environ["HF_HOME"] = settings.HF_HOME

    if args.command == "serve":
        from .server import start_server
        start_server()
        return 0

    if args.command == "dashboard":
        import subprocess
        dashboard_path = Path(__file__).resolve().parent.parent / "frontend" / "app.py"
        subprocess.run(["streamlit", "run", str(dashboard_path)])
        return 0

    service = FOAPipelineService(
        use_embeddings=not args.no_embeddings,
        use_llm=args.llm,
        ontology_path=args.ontology,
        store_path=args.store,
    )

    out_dir = args.out_dir or settings.OUTPUT_DIR

    code = 0
    if args.evaluate:
        code |= _run_eval(service, out_dir)
    if args.url:
        code |= _process_single(service, args.url, out_dir)
    if args.batch:
        code |= _process_batch(service, args.batch, out_dir)
    return code

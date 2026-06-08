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
    args = parser.parse_args(argv)

    if not args.url and not args.batch and not args.evaluate:
        parser.print_help()
        return 0

    # Why: sentence-transformers defaults can fail in restricted environments.
    import os
    if settings.HF_HOME:
        os.environ["HF_HOME"] = settings.HF_HOME

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

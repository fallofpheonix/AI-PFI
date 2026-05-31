from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List

from config import load_settings
from services.foa_pipeline_service import FOAPipelineService
from utils.logging import configure_logging
from utils.telemetry import flush_metrics

logger = logging.getLogger(__name__)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FOA Intelligence Pipeline")
    parser.add_argument("--url", type=str, help="Single FOA URL")
    parser.add_argument("--batch", type=str, help="Text file with one URL per line")
    parser.add_argument("--out_dir", type=str, default="./out")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent extractions")
    parser.add_argument("--no-embeddings", action="store_true")
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--store", type=str, help="SQLite store path")
    parser.add_argument("--ontology", type=str, help="Custom ontology path")
    return parser

def _load_batch_urls(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as handle:
        urls = [line.strip() for line in handle if line.strip() and not line.strip().startswith("#")]
    return list(dict.fromkeys(urls))

async def _process_single_async(url: str, pipeline: FOAPipelineService):
    try:
        record = await pipeline.process_url(url)
        logger.info(f"Successfully processed: {record.foa_id} - {url}")
    except Exception as exc:
        logger.error(f"Failed to process {url}: {exc}")

async def _process_batch_async(urls: List[str], pipeline: FOAPipelineService, concurrency: int):
    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded_process(url: str):
        async with semaphore:
            await _process_single_async(url, pipeline)

    tasks = [_bounded_process(url) for url in urls]
    await asyncio.gather(*tasks)

def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.url and not args.batch:
        parser.print_help()
        return 0

    settings = load_settings()
    configure_logging(verbose=args.verbose)

    pipeline = FOAPipelineService(
        use_embeddings=not args.no_embeddings,
        use_llm=args.llm,
        ontology_path=args.ontology,
        store_path=args.store or str(Path(args.out_dir) / "foa_store.db"),
    )

    if args.url:
        asyncio.run(_process_single_async(args.url, pipeline))
    if args.batch:
        urls = _load_batch_urls(args.batch)
        asyncio.run(_process_batch_async(urls, pipeline, args.concurrency))
    
    flush_metrics()
    return 0

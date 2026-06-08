"""
FastAPI Server for AI-PFI.
Exposes ingestion and search endpoints.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from config import settings
from services import FOAPipelineService
from core.models import FOARecord

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-PFI API",
    description="AI-Powered Funding Intelligence API",
    version="1.0.0"
)

# Shared service instances
# In a production app, these would be managed via dependency injection
service = FOAPipelineService()


class IngestRequest(BaseModel):
    urls: List[str]


class IngestResponse(BaseModel):
    status: str
    message: str
    processed_count: int


@app.get("/")
async def root():
    return {"message": "AI-PFI API is running"}


@app.post("/api/v1/foa/ingest", response_model=IngestResponse)
async def ingest_urls(request: IngestRequest, background_tasks: BackgroundTasks):
    """Trigger ingestion for a list of URLs."""
    # Run in background to avoid timeouts for large batches
    background_tasks.add_task(_process_batch_background, request.urls)
    
    return IngestResponse(
        status="accepted",
        message=f"Processing {len(request.urls)} URLs in background.",
        processed_count=len(request.urls)
    )


@app.get("/api/v1/foa", response_model=List[FOARecord])
async def list_foas(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List funding opportunities with pagination."""
    return service.exporter._store.all_records(limit=limit, offset=offset)


@app.get("/api/v1/foa/search", response_model=List[FOARecord])
async def search_foas(
    q: str = Query(..., min_length=2, description="Natural language search query"),
    limit: int = Query(10, ge=1, le=50)
):
    """Perform semantic search for relevant grants."""
    try:
        return service.exporter._store.search_semantic(q, limit=limit)
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search engine failure")


@app.get("/api/v1/foa/{foa_id}", response_model=FOARecord)
async def get_foa(foa_id: str):
    """Retrieve a specific FOA by its identifier."""
    # We add a helper to FOAStore for single retrieval
    with service.exporter._store as store:
        # Note: FOAStore currently doesn't have a direct get(id) but all_records can be used
        # or we can add it. For now, let's assume we find it in all_records or add a quick helper.
        from sqlmodel import Session, select
        from core.database.entities import FOAEntity
        from core.database.session import engine
        
        with Session(engine) as session:
            entity = session.get(FOAEntity, foa_id)
            if not entity:
                raise HTTPException(status_code=404, detail=f"FOA {foa_id} not found")
            return service.exporter._store._entity_to_record(entity)


def _process_batch_background(urls: List[str]):
    """Background task for batch ingestion."""
    for url in urls:
        try:
            logger.info(f"Background ingestion starting for: {url}")
            service.process_url(url)
            logger.info(f"Background ingestion completed for: {url}")
        except Exception as e:
            logger.error(f"Background ingestion failed for {url}: {e}")


def start_server():
    """Start the Uvicorn server."""
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=False
    )

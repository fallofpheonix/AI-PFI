from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, HttpUrl

from services.foa_pipeline_service import FOAPipelineService
from config import load_settings
from utils.logging import configure_logging

logger = logging.getLogger(__name__)

# Load settings and configure logging
settings = load_settings()
configure_logging(verbose=True)

app = FastAPI(
    title="AI-PFI Engine API",
    description="RESTful API for the FOA Intelligence Pipeline",
    version="1.0.0",
)

# Initialize the pipeline service
# In production, this might be managed via dependency injection or a startup event
pipeline = FOAPipelineService(
    use_embeddings=True,
    use_llm=False,
)

class ProcessRequest(BaseModel):
    url: HttpUrl
    use_llm: bool = False
    ontology: Optional[str] = None

class ProcessResponse(BaseModel):
    foa_id: str
    title: str
    agency: str
    open_date: str
    close_date: str
    tags: dict
    source_url: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI-PFI Engine"}

@app.post("/process", response_model=ProcessResponse)
async def process_url(request: ProcessRequest):
    """
    Process a single FOA URL through the ingestion and extraction pipeline.
    """
    try:
        logger.info(f"Processing URL: {request.url}")
        record = await pipeline.process_url(str(request.url))
        return record.to_dict()
    except Exception as e:
        logger.error(f"Error processing {request.url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch")
async def process_batch(urls: List[HttpUrl], use_llm: bool = False):
    """
    Process a batch of FOA URLs.
    Note: For long-running tasks, consider using BackgroundTasks or a task queue.
    """
    results = []
    for url in urls:
        try:
            record = await pipeline.process_url(str(url))
            results.append({"url": str(url), "status": "success", "foa_id": record.foa_id})
        except Exception as e:
            results.append({"url": str(url), "status": "failed", "error": str(e)})
    return {"processed": len(urls), "results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

import os
import logging
from prometheus_client import CollectorRegistry, Counter, Histogram, push_to_gateway

logger = logging.getLogger(__name__)

# Use a dedicated registry to avoid conflicts with global default registry
REGISTRY = CollectorRegistry()

# Instrumentation
EXTRACTION_LATENCY = Histogram(
    'foa_extraction_seconds', 
    'Time spent extracting FOA data', 
    ['type'], 
    registry=REGISTRY
)

INGESTION_ERRORS = Counter(
    'foa_ingestion_errors_total', 
    'Total errors per ingestion type', 
    ['type'], 
    registry=REGISTRY
)

def flush_metrics(job_name: str = "ai-pfi-ingestion"):
    """Pushes collected metrics to the configured PushGateway."""
    gateway_url = os.getenv("PROMETHEUS_PUSHGATEWAY_URL")
    if gateway_url:
        try:
            push_to_gateway(gateway_url, job=job_name, registry=REGISTRY)
            logger.info(f"Metrics successfully pushed to {gateway_url}")
        except Exception as e:
            logger.error(f"Failed to push metrics to gateway: {e}")

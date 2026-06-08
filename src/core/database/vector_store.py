"""
Vector store for semantic search using ChromaDB.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import chromadb
from chromadb.utils import embedding_functions

from config import settings
from core.models import FOARecord

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Handles semantic indexing and search using ChromaDB.
    """

    def __init__(self, path: str = None):
        self.path = path or settings.CHROMA_DB_PATH
        self.client = chromadb.PersistentClient(path=self.path)
        
        # Use the same model as EmbeddingTagger for consistency
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self.collection = self.client.get_or_create_collection(
            name="funding_opportunities",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"VectorStore initialized at {self.path}")

    def upsert(self, record: FOARecord):
        """Add or update an FOA record in the vector store."""
        # We index the title and description
        document = f"{record.title or ''}\n\n{record.description or ''}"
        if not document.strip():
            logger.warning(f"Skipping vector index for {record.foa_id}: No text content.")
            return

        self.collection.upsert(
            ids=[record.foa_id],
            documents=[document],
            metadatas=[{
                "title": record.title or "",
                "agency": record.agency or "",
                "url": record.url,
                "source": record.source.value
            }]
        )
        logger.debug(f"VectorStore: Indexed {record.foa_id}")

    def search(self, query: str, limit: int = 10) -> List[tuple[str, float]]:
        """
        Perform semantic search.
        Returns a list of (foa_id, distance) tuples.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=limit
        )
        
        # ChromaDB returns results in nested lists
        if not results or not results["ids"]:
            return []
            
        ids = results["ids"][0]
        distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)
        
        # Convert distances (cosine distance) to similarity scores if needed, 
        # but here we just return them.
        return list(zip(ids, distances))

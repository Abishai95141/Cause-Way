"""Document service for ChromaDB RAG operations."""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

import chromadb
from chromadb.utils import embedding_functions

from app.config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL, DATA_DIR, RAG_TOP_K

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document retrieval using ChromaDB."""

    def __init__(self):
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection: Optional[chromadb.Collection] = None
        self._embedding_fn = None

    def _get_client(self) -> chromadb.PersistentClient:
        """Lazy initialization of ChromaDB client."""
        if self._client is None:
            Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        return self._client

    def _get_embedding_fn(self):
        """Get the embedding function."""
        if self._embedding_fn is None:
            self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )
        return self._embedding_fn

    def _get_collection(self) -> chromadb.Collection:
        """Get or create the documents collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name="decision_documents",
                embedding_function=self._get_embedding_fn()
            )
        return self._collection

    def check_availability(self) -> bool:
        """Check if ChromaDB is available and has documents."""
        try:
            collection = self._get_collection()
            return collection.count() > 0
        except Exception as e:
            logger.error(f"ChromaDB availability check failed: {e}")
            return False

    def get_document_count(self) -> int:
        """Get the number of documents in the collection."""
        try:
            return self._get_collection().count()
        except Exception:
            return 0

    def retrieve_context(
        self,
        query: str,
        treatment: str,
        outcomes: List[str],
        n_results: int = RAG_TOP_K
    ) -> Dict[str, Any]:
        """Retrieve relevant context from documents."""
        result = {
            "relevant_experiments": "",
            "relevant_changes": [],
            "kpi_info": {},
            "warnings": []
        }

        try:
            collection = self._get_collection()
            
            if collection.count() == 0:
                result["warnings"].append("No documents indexed. Run ingest_documents.py")
                return result

            # Build search query
            search_query = f"{query} {treatment} {' '.join(outcomes)}"
            
            # Semantic search
            search_results = collection.query(
                query_texts=[search_query],
                n_results=n_results,
                include=["documents", "metadatas"]
            )

            # Process results
            docs = search_results.get("documents", [[]])[0]
            metas = search_results.get("metadatas", [[]])[0]

            experiments = []
            for doc, meta in zip(docs, metas):
                doc_type = meta.get("type", "unknown")
                if doc_type == "experiment":
                    experiments.append(doc)
                elif doc_type == "kpi":
                    # Parse KPI info
                    try:
                        kpi_data = json.loads(doc)
                        result["kpi_info"].update(kpi_data)
                    except json.JSONDecodeError:
                        result["kpi_info"]["raw"] = doc

            result["relevant_experiments"] = "\n---\n".join(experiments) if experiments else "No relevant experiments found."

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            result["warnings"].append(f"Document retrieval error: {str(e)}")

        return result

    def get_recent_changes(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get recent company changes from the raw JSON file."""
        changes = []
        changes_file = DATA_DIR / "documents" / "company_changes.json"
        
        try:
            if changes_file.exists():
                with open(changes_file, "r") as f:
                    all_changes = json.load(f)
                    changes = all_changes  # Return all for now, filtering done in confounder service
        except Exception as e:
            logger.error(f"Failed to load company changes: {e}")
        
        return changes


# Singleton instance
document_service = DocumentService()

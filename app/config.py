"""Configuration settings for the Causality-Aware Decision API."""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = BASE_DIR / "database"

# Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TEMPERATURE = 0.1  # Low temperature for consistent JSON output

# Confounder detection
CONFOUNDING_WINDOW_DAYS = 14

# ChromaDB settings
CHROMA_PERSIST_DIR = str(DATA_DIR / "chroma_db")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Database settings
DATABASE_URL = f"sqlite:///{DATABASE_DIR}/decisions.db"

# RAG settings
RAG_TOP_K = 5

# LLM retry settings
LLM_MAX_RETRIES = 2

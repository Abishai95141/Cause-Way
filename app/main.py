"""FastAPI main application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import init_db, get_db
from app.schemas import (
    AnalyzeRequest, AnalyzeResponse, HealthResponse, ErrorResponse
)
from app.services.llm_service import (
    llm_service, OllamaUnavailableError, ModelNotFoundError
)
from app.services.document_service import document_service
from app.services.decision_analyzer import decision_analyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="Causality-Aware Decision Intelligence API",
    description="Analyzes business decisions and identifies causal confounders",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    ollama_available = await llm_service.check_availability()
    chromadb_available = document_service.check_availability()
    
    # Database is available if we got here (init_db succeeded)
    database_available = True
    
    status = "healthy" if (ollama_available and chromadb_available) else "degraded"
    
    return HealthResponse(
        status=status,
        ollama_available=ollama_available,
        chromadb_available=chromadb_available,
        database_available=database_available
    )


@app.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
    responses={
        503: {"model": ErrorResponse, "description": "Ollama unavailable"},
        500: {"model": ErrorResponse, "description": "Internal error"}
    },
    tags=["Analysis"]
)
async def analyze_decision(
    request: AnalyzeRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze a business decision question.
    
    Detects causal confounders from recent company changes and provides
    recommendations on whether it's safe to proceed.
    """
    try:
        response = await decision_analyzer.analyze(request, db)
        return response
    except OllamaUnavailableError as e:
        logger.error(f"Ollama unavailable: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Ollama unavailable. Run: ollama serve",
                "suggestion": "Start Ollama server with: ollama serve"
            }
        )
    except ModelNotFoundError as e:
        logger.error(f"Model not found: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Model missing. Run: ollama pull qwen2.5:7b",
                "suggestion": "Download the model with: ollama pull qwen2.5:7b"
            }
        )
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Analysis failed: {str(e)}",
                "suggestion": "Check logs for details"
            }
        )


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirects to docs."""
    return {
        "message": "Causality-Aware Decision Intelligence API",
        "docs": "/docs",
        "health": "/health"
    }

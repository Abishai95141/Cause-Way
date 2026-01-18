"""Pydantic schemas for request/response models."""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# --- Request Models ---

class AnalyzeRequest(BaseModel):
    """Request model for decision analysis."""
    question: str = Field(..., description="The business decision question to analyze")
    requester_team: Optional[str] = Field(None, description="Team requesting the analysis")


# --- Internal Models ---

class ParsedQuestion(BaseModel):
    """Parsed components of a user question."""
    treatment: str = Field(..., description="The proposed action/change")
    outcomes: List[str] = Field(..., description="Metrics that will be affected")
    decision_type: str = Field(..., description="Type: impact_analysis, root_cause, or should_we")


class ConfounderInfo(BaseModel):
    """Information about a detected confounder."""
    change_id: str = Field(..., description="ID of the confounding change")
    description: str = Field(..., description="Description of the change")
    days_ago: int = Field(..., description="Days since the change occurred")
    affected_metrics: List[str] = Field(..., description="Metrics affected by both change and proposed treatment")
    confidence: float = Field(..., description="Confidence score for confounder detection (0.7-1.0)")


class TeamImpact(BaseModel):
    """Cross-functional impact on a team."""
    team: str = Field(..., description="Team name")
    affected_metrics: List[str] = Field(..., description="Team's metrics that would be affected")
    direction: str = Field(..., description="Expected direction: positive, negative, or uncertain")
    risk_level: str = Field(..., description="Risk level: low, medium, or high")


# --- Response Models ---

class AnalyzeResponse(BaseModel):
    """Response model for decision analysis."""
    decision_id: str = Field(..., description="Unique identifier for this decision")
    question: str = Field(..., description="Original question asked")
    treatment: Optional[str] = Field(None, description="Extracted treatment/action")
    outcomes: Optional[List[str]] = Field(None, description="Extracted outcome metrics")
    
    # Core decision
    decision_safe: bool = Field(..., description="Whether it's safe to proceed")
    confidence_level: str = Field(..., description="Confidence: HIGH, MEDIUM, or LOW")
    suggested_action: str = Field(..., description="Action: PROCEED, WAIT, or RUN_EXPERIMENT")
    
    # Reasoning
    reasoning: str = Field(..., description="2-3 sentence explanation")
    action_details: Optional[str] = Field(None, description="Specific next steps")
    
    # Confounders
    confounders_detected: List[ConfounderInfo] = Field(default_factory=list)
    
    # Monitoring
    monitoring_required: Optional[List[str]] = Field(None, description="Metrics to monitor")
    stop_loss_triggers: Optional[List[str]] = Field(None, description="Conditions to stop")
    
    # Cross-functional
    team_impacts: Optional[List[TeamImpact]] = Field(None, description="Impact on other teams")
    
    # Metadata
    warnings: Optional[List[str]] = Field(None, description="Any warnings during processing")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Health status")
    ollama_available: bool = Field(..., description="Whether Ollama is reachable")
    chromadb_available: bool = Field(..., description="Whether ChromaDB is available")
    database_available: bool = Field(..., description="Whether SQLite is available")


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error message")
    suggestion: Optional[str] = Field(None, description="Suggestion to fix the error")

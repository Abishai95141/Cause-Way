"""SQLAlchemy models for decision logging."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Decision(Base):
    """Model for storing analyzed decisions."""
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(String(50), unique=True, nullable=False, index=True)
    question = Column(Text, nullable=False)
    requester_team = Column(String(50), nullable=True)
    treatment = Column(Text, nullable=True)
    outcomes = Column(Text, nullable=True)  # JSON array stored as text
    confounders_detected = Column(Text, nullable=True)  # JSON array stored as text
    decision_safe = Column(Boolean, nullable=False)
    confidence_level = Column(String(20), nullable=True)
    suggested_action = Column(String(50), nullable=True)
    reasoning = Column(Text, nullable=True)
    full_response = Column(Text, nullable=True)  # Complete JSON response
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Additional indexes
    __table_args__ = (
        Index("idx_decision_safe", "decision_safe"),
    )

    def __repr__(self):
        return f"<Decision(id={self.id}, decision_id={self.decision_id}, safe={self.decision_safe})>"

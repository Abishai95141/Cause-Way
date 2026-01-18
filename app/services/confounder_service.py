"""Confounder detection service with date-based logic."""
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
from dateutil.parser import parse as parse_date

from app.config import CONFOUNDING_WINDOW_DAYS
from app.schemas import ConfounderInfo

logger = logging.getLogger(__name__)


class ConfounderService:
    """Service for detecting causal confounders based on recent changes."""

    def __init__(self, reference_date: datetime = None):
        """Initialize with optional reference date for testing."""
        self._reference_date = reference_date

    def _get_current_date(self) -> datetime:
        """Get current date (or mock date for testing)."""
        if self._reference_date:
            return self._reference_date
        return datetime.now(timezone.utc)

    def detect_confounders(
        self,
        recent_changes: List[Dict[str, Any]],
        outcomes: List[str]
    ) -> Dict[str, Any]:
        """
        Detect confounders from recent changes that affect target outcomes.
        
        Algorithm (from documentation):
        FOR EACH change in recent_changes:
            days_since_change = (today - change.date).days
            IF days_since_change <= CONFOUNDING_WINDOW_DAYS:
                IF change.affected_metrics INTERSECTS outcomes:
                    confidence = 1.0 - (days_since_change / CONFOUNDING_WINDOW_DAYS) * 0.3
                    confounders.append(...)
        decision_safe = (LENGTH(confounders) == 0)
        """
        confounders: List[ConfounderInfo] = []
        current_date = self._get_current_date()

        for change in recent_changes:
            try:
                # Parse change date
                change_date_str = change.get("date", "")
                if not change_date_str:
                    continue
                
                change_date = parse_date(change_date_str)
                # Make timezone-aware if needed
                if change_date.tzinfo is None:
                    change_date = change_date.replace(tzinfo=timezone.utc)
                
                # Ensure current_date is also timezone-aware
                if current_date.tzinfo is None:
                    current_date = current_date.replace(tzinfo=timezone.utc)

                # Calculate days since change
                days_since_change = (current_date - change_date).days

                # Check if within confounding window
                if days_since_change <= CONFOUNDING_WINDOW_DAYS and days_since_change >= 0:
                    # Check metric intersection
                    change_metrics = set(change.get("affected_metrics", []))
                    outcome_set = set(outcomes)
                    intersection = change_metrics.intersection(outcome_set)

                    if intersection:
                        # Calculate confidence (decay formula from docs)
                        confidence = 1.0 - (days_since_change / CONFOUNDING_WINDOW_DAYS) * 0.3
                        confidence = round(confidence, 3)

                        confounder = ConfounderInfo(
                            change_id=change.get("id", "unknown"),
                            description=change.get("description", "Unknown change"),
                            days_ago=days_since_change,
                            affected_metrics=list(intersection),
                            confidence=confidence
                        )
                        confounders.append(confounder)

            except Exception as e:
                logger.warning(f"Error processing change {change.get('id', 'unknown')}: {e}")
                continue

        # Sort by confidence (higher first)
        confounders.sort(key=lambda x: x.confidence, reverse=True)

        decision_safe = len(confounders) == 0

        return {
            "confounders": confounders,
            "decision_safe": decision_safe,
            "total_confounders": len(confounders)
        }


# Singleton instance (can be replaced with custom date for testing)
confounder_service = ConfounderService()


def create_confounder_service(reference_date: datetime = None) -> ConfounderService:
    """Factory function to create confounder service with optional mock date."""
    return ConfounderService(reference_date=reference_date)

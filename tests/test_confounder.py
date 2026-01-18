"""Tests for confounder detection service."""
import pytest
from datetime import datetime, timezone

from app.services.confounder_service import create_confounder_service


class TestConfounderDetection:
    """Test confounder detection logic."""

    def test_confounder_detection_recent_change(self):
        """Test detection of a change 3 days ago."""
        # Mock date: 2026-01-18
        reference_date = datetime(2026, 1, 18, tzinfo=timezone.utc)
        service = create_confounder_service(reference_date)
        
        # Change from 3 days ago
        recent_changes = [
            {
                "id": "CHG-2026-001",
                "date": "2026-01-15",
                "type": "pricing",
                "description": "Increased enterprise tier pricing by 15%",
                "affected_metrics": ["conversion_rate", "revenue", "churn_rate"]
            }
        ]
        
        outcomes = ["conversion_rate", "activation_rate"]
        
        result = service.detect_confounders(recent_changes, outcomes)
        
        assert len(result["confounders"]) == 1
        assert result["decision_safe"] == False
        
        confounder = result["confounders"][0]
        assert confounder.change_id == "CHG-2026-001"
        assert confounder.days_ago == 3
        assert confounder.confidence > 0.93  # 1.0 - (3/14)*0.3 = 0.936
        assert "conversion_rate" in confounder.affected_metrics

    def test_safe_decision_no_confounders(self):
        """Test that no confounders returns decision_safe=True."""
        reference_date = datetime(2026, 1, 18, tzinfo=timezone.utc)
        service = create_confounder_service(reference_date)
        
        # No recent changes
        recent_changes = []
        outcomes = ["conversion_rate"]
        
        result = service.detect_confounders(recent_changes, outcomes)
        
        assert len(result["confounders"]) == 0
        assert result["decision_safe"] == True

    def test_safe_decision_old_change(self):
        """Test that changes older than 14 days are not confounders."""
        reference_date = datetime(2026, 1, 18, tzinfo=timezone.utc)
        service = create_confounder_service(reference_date)
        
        # Change from 20 days ago (outside window)
        recent_changes = [
            {
                "id": "CHG-OLD",
                "date": "2025-12-29",
                "description": "Old change",
                "affected_metrics": ["conversion_rate"]
            }
        ]
        
        outcomes = ["conversion_rate"]
        
        result = service.detect_confounders(recent_changes, outcomes)
        
        assert len(result["confounders"]) == 0
        assert result["decision_safe"] == True

    def test_no_confounder_if_no_metric_overlap(self):
        """Test that changes with non-overlapping metrics are not confounders."""
        reference_date = datetime(2026, 1, 18, tzinfo=timezone.utc)
        service = create_confounder_service(reference_date)
        
        # Recent change but affects different metrics
        recent_changes = [
            {
                "id": "CHG-2026-001",
                "date": "2026-01-15",
                "description": "Support change",
                "affected_metrics": ["nps", "support_satisfaction"]
            }
        ]
        
        outcomes = ["conversion_rate", "revenue"]
        
        result = service.detect_confounders(recent_changes, outcomes)
        
        assert len(result["confounders"]) == 0
        assert result["decision_safe"] == True

    def test_confidence_decay(self):
        """Test that confidence decays with time."""
        reference_date = datetime(2026, 1, 18, tzinfo=timezone.utc)
        service = create_confounder_service(reference_date)
        
        recent_changes = [
            {
                "id": "CHG-1",
                "date": "2026-01-17",  # 1 day ago
                "description": "Recent",
                "affected_metrics": ["conversion_rate"]
            },
            {
                "id": "CHG-2",
                "date": "2026-01-11",  # 7 days ago
                "description": "Older",
                "affected_metrics": ["conversion_rate"]
            }
        ]
        
        outcomes = ["conversion_rate"]
        
        result = service.detect_confounders(recent_changes, outcomes)
        
        assert len(result["confounders"]) == 2
        
        # Find confounders by ID
        c1 = next(c for c in result["confounders"] if c.change_id == "CHG-1")
        c2 = next(c for c in result["confounders"] if c.change_id == "CHG-2")
        
        # Confidence: 1.0 - (days/14)*0.3
        # 1 day: 1.0 - (1/14)*0.3 ≈ 0.979
        # 7 days: 1.0 - (7/14)*0.3 = 0.85
        assert c1.confidence > c2.confidence
        assert c1.confidence > 0.97
        assert 0.84 < c2.confidence < 0.86

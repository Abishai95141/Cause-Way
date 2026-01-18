"""Decision Analyzer - Core orchestration service."""
import json
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.schemas import (
    AnalyzeRequest, AnalyzeResponse, ParsedQuestion,
    ConfounderInfo, TeamImpact
)
from app.models import Decision
from app.services.llm_service import (
    llm_service, OllamaUnavailableError, ModelNotFoundError
)
from app.services.document_service import document_service
from app.services.confounder_service import confounder_service

logger = logging.getLogger(__name__)


# Team to metrics mapping (from kpi_definitions.json)
TEAM_METRICS = {
    "growth": ["conversion_rate", "trial_to_paid", "cac"],
    "product": ["activation_rate", "churn_rate", "time_to_value"],
    "finance": ["revenue"],
    "support": ["nps", "support_satisfaction"],
    "operations": []
}


class DecisionAnalyzer:
    """Core service that orchestrates the decision analysis flow."""

    async def analyze(
        self,
        request: AnalyzeRequest,
        db: Session
    ) -> AnalyzeResponse:
        """
        Main analysis flow:
        1. Parse question (LLM)
        2. Retrieve context (ChromaDB)
        3. Detect confounders (date logic)
        4. Generate recommendation (LLM)
        5. Log decision (SQLite)
        """
        decision_id = f"DEC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        warnings = []

        # Step 1: Parse question
        try:
            parsed = await llm_service.parse_question(request.question)
        except OllamaUnavailableError as e:
            raise e
        except ModelNotFoundError as e:
            raise e
        except Exception as e:
            logger.warning(f"Question parsing error: {e}")
            parsed = ParsedQuestion(
                treatment="unknown",
                outcomes=["conversion_rate"],
                decision_type="should_we"
            )
            warnings.append("Question parsing used fallback mode")

        # Step 2: Retrieve context
        context = document_service.retrieve_context(
            query=request.question,
            treatment=parsed.treatment,
            outcomes=parsed.outcomes
        )
        if context.get("warnings"):
            warnings.extend(context["warnings"])

        # Step 3: Get recent changes and detect confounders
        recent_changes = document_service.get_recent_changes()
        confounder_result = confounder_service.detect_confounders(
            recent_changes=recent_changes,
            outcomes=parsed.outcomes
        )
        confounders = confounder_result["confounders"]
        decision_safe = confounder_result["decision_safe"]

        # Step 4: Generate recommendation
        try:
            recommendation = await llm_service.generate_recommendation(
                question=request.question,
                treatment=parsed.treatment,
                outcomes=parsed.outcomes,
                confounders=[c.model_dump() for c in confounders],
                relevant_experiments=context.get("relevant_experiments", "")
            )
        except OllamaUnavailableError as e:
            raise e
        except ModelNotFoundError as e:
            raise e
        except Exception as e:
            logger.warning(f"Recommendation generation error: {e}")
            recommendation = {
                "decision_safe": decision_safe,
                "confidence_level": "LOW",
                "reasoning": "Unable to generate full recommendation. Based on confounder analysis only.",
                "suggested_action": "WAIT" if confounders else "RUN_EXPERIMENT",
                "action_details": "Review detected confounders.",
                "monitoring_required": parsed.outcomes,
                "stop_loss_triggers": []
            }
            warnings.append("Recommendation generation used fallback mode")

        # Step 5: Cross-functional impact assessment
        team_impacts = self._assess_team_impacts(
            outcomes=parsed.outcomes,
            confounders=confounders
        )

        # Build response
        response = AnalyzeResponse(
            decision_id=decision_id,
            question=request.question,
            treatment=parsed.treatment,
            outcomes=parsed.outcomes,
            decision_safe=recommendation.get("decision_safe", decision_safe),
            confidence_level=recommendation.get("confidence_level", "LOW"),
            suggested_action=recommendation.get("suggested_action", "WAIT"),
            reasoning=recommendation.get("reasoning", ""),
            action_details=recommendation.get("action_details"),
            confounders_detected=confounders,
            monitoring_required=recommendation.get("monitoring_required"),
            stop_loss_triggers=recommendation.get("stop_loss_triggers"),
            team_impacts=team_impacts if team_impacts else None,
            warnings=warnings if warnings else None,
            created_at=datetime.now(timezone.utc)
        )

        # Step 6: Log decision to database
        try:
            self._log_decision(db, request, response)
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
            if response.warnings is None:
                response.warnings = []
            response.warnings.append("Decision logging failed")

        return response

    def _assess_team_impacts(
        self,
        outcomes: list,
        confounders: list
    ) -> list:
        """Assess cross-functional impact on teams."""
        impacts = []
        outcome_set = set(outcomes)

        for team, team_metrics in TEAM_METRICS.items():
            affected = set(team_metrics).intersection(outcome_set)
            if affected:
                # Determine risk level based on confounders
                risk_level = "low"
                if confounders:
                    confounder_metrics = set()
                    for c in confounders:
                        confounder_metrics.update(c.affected_metrics)
                    if affected.intersection(confounder_metrics):
                        risk_level = "high"
                    else:
                        risk_level = "medium"

                impacts.append(TeamImpact(
                    team=team,
                    affected_metrics=list(affected),
                    direction="uncertain",  # Would need more context
                    risk_level=risk_level
                ))

        return impacts

    def _log_decision(
        self,
        db: Session,
        request: AnalyzeRequest,
        response: AnalyzeResponse
    ):
        """Log decision to database."""
        decision = Decision(
            decision_id=response.decision_id,
            question=request.question,
            requester_team=request.requester_team,
            treatment=response.treatment,
            outcomes=json.dumps(response.outcomes) if response.outcomes else None,
            confounders_detected=json.dumps(
                [c.model_dump() for c in response.confounders_detected]
            ) if response.confounders_detected else None,
            decision_safe=response.decision_safe,
            confidence_level=response.confidence_level,
            suggested_action=response.suggested_action,
            reasoning=response.reasoning,
            full_response=response.model_dump_json()
        )
        db.add(decision)
        db.commit()


# Singleton instance
decision_analyzer = DecisionAnalyzer()

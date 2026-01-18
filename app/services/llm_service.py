"""LLM service for Ollama integration."""
import json
import logging
import httpx
from typing import Optional, Dict, Any

from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TEMPERATURE, LLM_MAX_RETRIES
from app.schemas import ParsedQuestion

logger = logging.getLogger(__name__)


class OllamaUnavailableError(Exception):
    """Raised when Ollama server is not reachable."""
    pass


class ModelNotFoundError(Exception):
    """Raised when the specified model is not available."""
    pass


class LLMService:
    """Service for LLM operations via Ollama."""

    def __init__(self):
        self._llm: Optional[ChatOllama] = None

    def _get_llm(self) -> ChatOllama:
        """Lazy initialization of ChatOllama."""
        if self._llm is None:
            self._llm = ChatOllama(
                model=OLLAMA_MODEL,
                base_url=OLLAMA_BASE_URL,
                temperature=OLLAMA_TEMPERATURE,
                format="json"
            )
        return self._llm

    async def check_availability(self) -> bool:
        """Check if Ollama is available and model is loaded."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
                if response.status_code != 200:
                    return False
                tags = response.json()
                models = [m.get("name", "") for m in tags.get("models", [])]
                # Check if our model is available (handle version suffix)
                return any(OLLAMA_MODEL in m for m in models)
        except Exception as e:
            logger.error(f"Ollama availability check failed: {e}")
            return False

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling common issues."""
        # Clean up response
        text = response_text.strip()
        
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try finding JSON block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass
        
        # Try finding any JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        
        raise ValueError(f"Could not parse JSON from response: {text[:200]}")

    async def parse_question(self, question: str) -> ParsedQuestion:
        """Parse a user question to extract treatment, outcomes, and decision type."""
        prompt = f"""You are a causal reasoning expert analyzing business decisions.
Question: {question}
Extract the following in JSON format:
1. "treatment": What action/change is being proposed?
2. "outcomes": What metrics will this affect? (list)
3. "decision_type": "impact_analysis" | "root_cause" | "should_we"
Return ONLY valid JSON, no explanation."""

        for attempt in range(LLM_MAX_RETRIES + 1):
            try:
                llm = self._get_llm()
                response = llm.invoke([HumanMessage(content=prompt)])
                result = self._parse_json_response(response.content)
                
                return ParsedQuestion(
                    treatment=result.get("treatment", "unknown"),
                    outcomes=result.get("outcomes", []),
                    decision_type=result.get("decision_type", "should_we")
                )
            except httpx.ConnectError:
                raise OllamaUnavailableError("Ollama unavailable. Run: ollama serve")
            except Exception as e:
                if "not found" in str(e).lower():
                    raise ModelNotFoundError(f"Model missing. Run: ollama pull {OLLAMA_MODEL}")
                if attempt < LLM_MAX_RETRIES:
                    logger.warning(f"LLM parse attempt {attempt + 1} failed: {e}")
                    prompt += "\nReturn ONLY JSON, nothing else."
                else:
                    # Fallback to rule-based parsing
                    return self._rule_based_parse(question)

    def _rule_based_parse(self, question: str) -> ParsedQuestion:
        """Fallback rule-based parsing when LLM fails."""
        question_lower = question.lower()
        
        # Extract treatment
        treatment = "unknown_change"
        keywords = ["reduce", "increase", "change", "add", "remove", "launch", "stop"]
        for kw in keywords:
            if kw in question_lower:
                # Get words after the keyword
                idx = question_lower.find(kw)
                treatment = question[idx:idx+50].split("?")[0].strip()
                break
        
        # Extract outcomes (common metrics)
        outcomes = []
        metric_keywords = {
            "trial": "trial_to_paid",
            "conversion": "conversion_rate",
            "churn": "churn_rate",
            "revenue": "revenue",
            "activation": "activation_rate",
            "pricing": "conversion_rate"
        }
        for kw, metric in metric_keywords.items():
            if kw in question_lower:
                outcomes.append(metric)
        if not outcomes:
            outcomes = ["conversion_rate"]  # Default
        
        # Determine decision type
        decision_type = "should_we"
        if "why" in question_lower or "cause" in question_lower:
            decision_type = "root_cause"
        elif "impact" in question_lower or "effect" in question_lower:
            decision_type = "impact_analysis"
        
        return ParsedQuestion(treatment=treatment, outcomes=outcomes, decision_type=decision_type)

    async def generate_recommendation(
        self,
        question: str,
        treatment: str,
        outcomes: list,
        confounders: list,
        relevant_experiments: str
    ) -> Dict[str, Any]:
        """Generate decision recommendation based on analysis."""
        prompt = f"""You are generating a decision brief for business leaders.
Question: {question}
Treatment: {treatment}
Outcomes: {outcomes}
Confounders Detected: {json.dumps(confounders)}
Past Experiments: {relevant_experiments}
Generate a recommendation in JSON format:
{{
"decision_safe": true/false,
"confidence_level": "HIGH|MEDIUM|LOW",
"reasoning": "2-3 sentence explanation",
"suggested_action": "PROCEED|WAIT|RUN_EXPERIMENT",
"action_details": "Specific next steps",
"monitoring_required": ["metric1", "metric2"],
"stop_loss_triggers": ["condition1", "condition2"]
}}
If confounders exist, decision_safe MUST be false.
Return ONLY valid JSON."""

        for attempt in range(LLM_MAX_RETRIES + 1):
            try:
                llm = self._get_llm()
                response = llm.invoke([HumanMessage(content=prompt)])
                result = self._parse_json_response(response.content)
                
                # Enforce confounder rule
                if confounders:
                    result["decision_safe"] = False
                
                return result
            except httpx.ConnectError:
                raise OllamaUnavailableError("Ollama unavailable. Run: ollama serve")
            except Exception as e:
                if "not found" in str(e).lower():
                    raise ModelNotFoundError(f"Model missing. Run: ollama pull {OLLAMA_MODEL}")
                if attempt < LLM_MAX_RETRIES:
                    logger.warning(f"LLM recommendation attempt {attempt + 1} failed: {e}")
                    prompt += "\nReturn ONLY JSON, nothing else."
                else:
                    # Fallback response
                    return self._rule_based_recommendation(confounders, outcomes)

    def _rule_based_recommendation(self, confounders: list, outcomes: list) -> Dict[str, Any]:
        """Fallback rule-based recommendation when LLM fails."""
        has_confounders = len(confounders) > 0
        
        return {
            "decision_safe": not has_confounders,
            "confidence_level": "LOW",
            "reasoning": f"{'Confounders detected - cannot safely attribute changes to proposed treatment.' if has_confounders else 'No recent confounders detected.'} (LLM fallback mode)",
            "suggested_action": "WAIT" if has_confounders else "RUN_EXPERIMENT",
            "action_details": "Review confounders and wait for washout period." if has_confounders else "Consider running a controlled experiment.",
            "monitoring_required": outcomes[:3],
            "stop_loss_triggers": ["Significant metric degradation", "Unexpected side effects"]
        }


# Singleton instance
llm_service = LLMService()

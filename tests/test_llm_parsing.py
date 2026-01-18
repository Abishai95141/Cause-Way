"""Tests for LLM parsing (mocked)."""
import pytest
from unittest.mock import patch, MagicMock

from app.services.llm_service import LLMService
from app.schemas import ParsedQuestion


class TestLLMParsing:
    """Test LLM question parsing."""

    def test_rule_based_parse_pricing(self):
        """Test rule-based fallback for pricing question."""
        service = LLMService()
        
        result = service._rule_based_parse("Should we change pricing?")
        
        assert isinstance(result, ParsedQuestion)
        assert "pricing" in result.treatment.lower() or "change" in result.treatment.lower()
        assert "conversion_rate" in result.outcomes
        assert result.decision_type == "should_we"

    def test_rule_based_parse_trial(self):
        """Test rule-based fallback for trial question."""
        service = LLMService()
        
        result = service._rule_based_parse("Should we reduce trial duration?")
        
        assert isinstance(result, ParsedQuestion)
        assert "reduce" in result.treatment.lower()
        assert "trial_to_paid" in result.outcomes

    def test_rule_based_parse_churn(self):
        """Test rule-based fallback for churn question."""
        service = LLMService()
        
        result = service._rule_based_parse("Why is churn increasing?")
        
        assert isinstance(result, ParsedQuestion)
        assert "churn_rate" in result.outcomes
        assert result.decision_type == "root_cause"

    def test_json_parsing_valid(self):
        """Test JSON parsing with valid JSON."""
        service = LLMService()
        
        result = service._parse_json_response('{"treatment": "test", "outcomes": ["a"]}')
        
        assert result["treatment"] == "test"
        assert result["outcomes"] == ["a"]

    def test_json_parsing_with_markdown(self):
        """Test JSON parsing with markdown code block."""
        service = LLMService()
        
        response = '''Here is the result:
```json
{"treatment": "reduce_trial", "outcomes": ["conversion"]}
```'''
        
        result = service._parse_json_response(response)
        
        assert result["treatment"] == "reduce_trial"

    def test_json_parsing_with_extra_text(self):
        """Test JSON parsing with surrounding text."""
        service = LLMService()
        
        response = 'The analysis shows: {"treatment": "test", "outcomes": ["a"]} as the result.'
        
        result = service._parse_json_response(response)
        
        assert result["treatment"] == "test"

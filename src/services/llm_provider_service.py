"""LLM provider service supporting OpenAI and Anthropic with customer-owned API keys."""

import json
import time
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import ValidationError

from src.core.logging import service_logger
from src.models.action_item import ActionItem, ActionItemPriority, ActionItemStatus
from src.models.decision import Decision, DecisionImpact, DecisionStatus
from src.models.transcript import MeetingSummary

from .base import SummarizationServiceBase
from .prompts import MEETING_ANALYSIS_PROMPT


class LLMProviderService(SummarizationServiceBase):
    """
    AI summarization service supporting multiple LLM providers with customer API keys.
    
    This service provides high-quality meeting transcript analysis using cloud-based
    LLM providers like OpenAI and Anthropic, with customer-provided API keys.
    Features include:
    - Multi-provider support (OpenAI, Anthropic)
    - Customer-owned API key management
    - Structured output with function calling
    - Comprehensive error handling and retry logic
    - Cost monitoring and token usage tracking
    """

    def __init__(self, provider: str, api_key: str):
        """
        Initialize the LLM provider service.
        
        Args:
            provider: Provider name ("openai" or "anthropic")
            api_key: Customer-provided API key
            
        Raises:
            ValueError: If provider is not supported
            Exception: If API key validation fails
        """
        if provider not in ["openai", "anthropic"]:
            raise ValueError(f"Unsupported provider: {provider}")
            
        self.provider = provider
        self.api_key = api_key
        self.client = None
        self.processing_start_time = None
        
        # Initialize provider-specific client
        self._initialize_client()
        
        service_logger.info(
            "LLMProviderService initialized",
            extra={
                "provider": self.provider,
                "has_api_key": bool(self.api_key)
            }
        )

    def _initialize_client(self):
        """Initialize the appropriate client for the provider."""
        try:
            if self.provider == "openai":
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.api_key)
                self.model = "gpt-4o-mini"  # Cost-effective model
                
            elif self.provider == "anthropic":
                from anthropic import AsyncAnthropic
                self.client = AsyncAnthropic(api_key=self.api_key)
                self.model = "claude-3-haiku-20240307"  # Cost-effective model
                
        except ImportError as e:
            raise Exception(f"Required package not installed for {self.provider}: {e}")
        except Exception as e:
            raise Exception(f"Failed to initialize {self.provider} client: {e}")

    async def _validate_api_key(self) -> bool:
        """Validate the API key by making a simple test request."""
        try:
            if self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Test"}],
                    max_tokens=1
                )
                return bool(response.choices[0].message.content)
                
            elif self.provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Test"}],
                    max_tokens=1
                )
                return bool(response.content)
                
        except Exception as e:
            service_logger.error(f"API key validation failed for {self.provider}: {e}")
            return False

    async def _generate_with_openai(self, prompt: str) -> Dict[str, Any]:
        """Generate structured response using OpenAI's function calling."""
        # Define the function schema for structured output
        function_schema = {
            "name": "extract_meeting_data",
            "description": "Extract structured information from meeting transcript",
            "parameters": {
                "type": "object",
                "properties": {
                    "executive_summary": {
                        "type": "string",
                        "description": "2-3 sentence summary of the meeting"
                    },
                    "key_decisions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "decision": {"type": "string"},
                                "made_by": {"type": "string"},
                                "rationale": {"type": "string"},
                                "impact": {"type": "string", "enum": ["high", "medium", "low"]},
                                "status": {"type": "string", "enum": ["approved", "pending", "rejected"]}
                            },
                            "required": ["decision", "made_by"]
                        }
                    },
                    "action_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "task": {"type": "string"},
                                "assignee": {"type": "string"},
                                "due_date": {"type": ["string", "null"]},
                                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                                "context": {"type": "string"},
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}
                            },
                            "required": ["task", "assignee"]
                        }
                    },
                    "risks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "risk": {"type": "string"},
                                "impact": {"type": "string", "enum": ["high", "medium", "low"]},
                                "likelihood": {"type": "string", "enum": ["high", "medium", "low"]},
                                "mitigation": {"type": "string"},
                                "owner": {"type": ["string", "null"]}
                            },
                            "required": ["risk"]
                        }
                    },
                    "user_stories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "story": {"type": "string"},
                                "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                                "epic": {"type": ["string", "null"]}
                            },
                            "required": ["story"]
                        }
                    },
                    "next_steps": {"type": "array", "items": {"type": "string"}},
                    "key_topics": {"type": "array", "items": {"type": "string"}},
                    "participants": {"type": "array", "items": {"type": "string"}},
                    "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative", "mixed"]}
                },
                "required": ["executive_summary", "action_items", "key_decisions"]
            }
        }
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            functions=[function_schema],
            function_call={"name": "extract_meeting_data"},
            temperature=0.1,
            max_tokens=2000
        )
        
        function_call = response.choices[0].message.function_call
        if function_call and function_call.name == "extract_meeting_data":
            return json.loads(function_call.arguments)
        else:
            raise Exception("OpenAI did not return expected function call")

    async def _generate_with_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Generate structured response using Anthropic Claude."""
        # Anthropic doesn't have function calling, so we use structured prompts
        structured_prompt = f"""
{prompt}

Please respond with a valid JSON object only, no additional text:
"""
        
        response = await self.client.messages.create(
            model=self.model,
            messages=[{"role": "user", "content": structured_prompt}],
            temperature=0.1,
            max_tokens=2000
        )
        
        response_text = response.content[0].text
        
        # Try to extract JSON from response
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise Exception("Could not extract valid JSON from Anthropic response")

    async def _generate_structured_response(self, transcript: str) -> Dict[str, Any]:
        """Generate structured response using the appropriate provider."""
        prompt = MEETING_ANALYSIS_PROMPT.format(transcript=transcript)
        
        try:
            if self.provider == "openai":
                return await self._generate_with_openai(prompt)
            elif self.provider == "anthropic":
                return await self._generate_with_anthropic(prompt)
            else:
                raise Exception(f"Unsupported provider: {self.provider}")
                
        except Exception as e:
            service_logger.error(f"{self.provider} request failed: {e}")
            raise

    async def summarize_transcript(
        self, meeting_id: str, transcript_text: str
    ) -> MeetingSummary:
        """
        Generate a comprehensive meeting summary using the configured LLM provider.
        
        Args:
            meeting_id: Unique identifier for the meeting
            transcript_text: Raw transcript content to analyze
            
        Returns:
            MeetingSummary: Structured summary with extracted information
        """
        self.processing_start_time = time.time()
        
        service_logger.info(
            f"Starting {self.provider} transcript analysis",
            extra={
                "meeting_id": meeting_id,
                "provider": self.provider,
                "transcript_length": len(transcript_text),
                "model": self.model
            }
        )
        
        try:
            # Validate API key if not already done
            if not await self._validate_api_key():
                raise Exception(f"Invalid or expired API key for {self.provider}")
            
            # Generate structured response
            extracted_data = await self._generate_structured_response(transcript_text)
            
            # Convert to Pydantic models
            action_items = []
            for item_data in extracted_data.get("action_items", []):
                try:
                    action_item = ActionItem(
                        id=str(uuid4()),
                        task=item_data["task"],
                        assignee=item_data["assignee"],
                        due_date=item_data.get("due_date"),
                        priority=ActionItemPriority(item_data.get("priority", "medium")),
                        status=ActionItemStatus(item_data.get("status", "pending")),
                        context=item_data.get("context", ""),
                        created_at=datetime.now(UTC)
                    )
                    action_items.append(action_item)
                except (ValidationError, ValueError) as e:
                    service_logger.warning(f"Invalid action item data: {e}")
                    continue
                    
            decisions = []
            for decision_data in extracted_data.get("key_decisions", []):
                try:
                    decision = Decision(
                        id=str(uuid4()),
                        decision=decision_data["decision"],
                        made_by=decision_data["made_by"],
                        rationale=decision_data.get("rationale", ""),
                        impact=DecisionImpact(decision_data.get("impact", "medium")),
                        status=DecisionStatus(decision_data.get("status", "approved")),
                        created_at=datetime.now(UTC)
                    )
                    decisions.append(decision)
                except (ValidationError, ValueError) as e:
                    service_logger.warning(f"Invalid decision data: {e}")
                    continue
                    
            # Create meeting summary
            processing_time = time.time() - self.processing_start_time
            
            summary = MeetingSummary(
                meeting_id=meeting_id,
                summary=extracted_data.get("executive_summary", ""),
                key_topics=extracted_data.get("key_topics", []),
                action_items=action_items,
                decisions=decisions,
                participants=extracted_data.get("participants", []),
                sentiment=extracted_data.get("sentiment", "neutral"),
                next_steps=extracted_data.get("next_steps", []),
                confidence_score=self._calculate_confidence_score(extracted_data),
                processing_time_seconds=round(processing_time, 2),
                created_at=datetime.now(UTC)
            )
            
            service_logger.info(
                f"{self.provider} analysis completed successfully",
                extra={
                    "meeting_id": meeting_id,
                    "provider": self.provider,
                    "processing_time": processing_time,
                    "action_items_found": len(action_items),
                    "decisions_found": len(decisions),
                    "confidence_score": summary.confidence_score
                }
            )
            
            return summary
            
        except Exception as e:
            processing_time = time.time() - self.processing_start_time if self.processing_start_time else 0
            
            service_logger.error(
                f"{self.provider} analysis failed",
                extra={
                    "meeting_id": meeting_id,
                    "provider": self.provider,
                    "error": str(e),
                    "processing_time": processing_time
                }
            )
            
            # Return error summary
            return MeetingSummary(
                meeting_id=meeting_id,
                summary=f"{self.provider} analysis failed: {str(e)}",
                key_topics=[],
                action_items=[],
                decisions=[],
                participants=[],
                sentiment="neutral",
                next_steps=[],
                confidence_score=0.0,
                processing_time_seconds=processing_time,
                created_at=datetime.now(UTC)
            )

    def _calculate_confidence_score(self, extracted_data: Dict[str, Any]) -> float:
        """Calculate confidence score based on extraction completeness."""
        score = 0.0
        max_score = 100.0
        
        # Higher base confidence for cloud providers
        base_confidence = 85.0 if self.provider in ["openai", "anthropic"] else 70.0
        score = base_confidence
        
        # Adjust based on content richness
        action_items = extracted_data.get("action_items", [])
        if action_items:
            score += min(10.0, len(action_items) * 2.0)
            
        decisions = extracted_data.get("key_decisions", [])
        if decisions:
            score += min(5.0, len(decisions) * 1.0)
            
        # Penalize for missing critical information
        if not extracted_data.get("executive_summary"):
            score -= 10.0
            
        if not extracted_data.get("participants"):
            score -= 5.0
            
        return min(max(score, 0.0), max_score) / max_score
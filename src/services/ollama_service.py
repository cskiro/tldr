"""Ollama-based AI summarization service with structured output support."""

import asyncio
import json
import re
import time
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from pydantic import ValidationError

from src.core.logging import service_logger
from src.models.action_item import ActionItem, ActionItemPriority, ActionItemStatus
from src.models.decision import Decision, DecisionImpact, DecisionStatus
from src.models.transcript import MeetingSummary

from .base import SummarizationServiceBase
from .prompts import (
    FALLBACK_EXTRACTION_PATTERNS,
    MEETING_ANALYSIS_PROMPT,
    SIMPLE_SUMMARY_PROMPT,
)


class OllamaService(SummarizationServiceBase):
    """
    Local AI summarization service using Ollama with structured output support.

    This service provides meeting transcript analysis using local LLM models via Ollama,
    with no external API costs. Features include:
    - Structured JSON output using Pydantic schemas
    - Fallback to regex extraction if structured output fails
    - Retry logic for malformed responses
    - Comprehensive error handling and logging
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
        timeout: float = 120.0,
    ):
        """
        Initialize the Ollama service.

        Args:
            base_url: Ollama server URL
            model: Model name to use for inference
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.processing_start_time = None

        service_logger.info(
            "OllamaService initialized",
            extra={
                "base_url": self.base_url,
                "model": self.model,
                "timeout": self.timeout,
            },
        )

    async def _check_ollama_health(self) -> bool:
        """Check if Ollama server is accessible."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            service_logger.error(f"Ollama health check failed: {e}")
            return False

    async def _generate_with_ollama(
        self,
        prompt: str,
        format_schema: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> str:
        """
        Generate response using Ollama API with optional structured output.

        Args:
            prompt: Input prompt
            format_schema: Optional JSON schema for structured output
            max_retries: Maximum retry attempts

        Returns:
            Generated response text
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistency
                "top_k": 40,
                "top_p": 0.9,
                "num_predict": 2000,  # Limit output length
            },
        }

        if format_schema:
            payload["format"] = format_schema

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/api/generate", json=payload
                    )
                    response.raise_for_status()

                    result = response.json()
                    return result.get("response", "")

            except httpx.TimeoutException:
                service_logger.warning(
                    f"Ollama request timeout (attempt {attempt + 1})"
                )
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)  # Exponential backoff

            except Exception as e:
                service_logger.error(
                    f"Ollama request failed (attempt {attempt + 1}): {e}"
                )
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)

        raise Exception("Max retries exceeded for Ollama request")

    async def _extract_with_structured_output(self, transcript: str) -> Dict[str, Any]:
        """Extract structured information using Ollama's format parameter."""
        try:
            # Define JSON schema based on our MeetingSummary model
            schema = {
                "type": "object",
                "properties": {
                    "executive_summary": {"type": "string"},
                    "key_decisions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "decision": {"type": "string"},
                                "made_by": {"type": "string"},
                                "rationale": {"type": "string"},
                                "impact": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["approved", "pending", "rejected"],
                                },
                            },
                            "required": ["decision", "made_by"],
                        },
                    },
                    "action_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "task": {"type": "string"},
                                "assignee": {"type": "string"},
                                "due_date": {"type": ["string", "null"]},
                                "priority": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                },
                                "context": {"type": "string"},
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "completed"],
                                },
                            },
                            "required": ["task", "assignee"],
                        },
                    },
                    "risks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "risk": {"type": "string"},
                                "impact": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                },
                                "likelihood": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                },
                                "mitigation": {"type": "string"},
                                "owner": {"type": ["string", "null"]},
                            },
                            "required": ["risk"],
                        },
                    },
                    "user_stories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "story": {"type": "string"},
                                "acceptance_criteria": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "priority": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                },
                                "epic": {"type": ["string", "null"]},
                            },
                            "required": ["story"],
                        },
                    },
                    "next_steps": {"type": "array", "items": {"type": "string"}},
                    "key_topics": {"type": "array", "items": {"type": "string"}},
                    "participants": {"type": "array", "items": {"type": "string"}},
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative", "mixed"],
                    },
                },
                "required": ["executive_summary", "action_items", "key_decisions"],
            }

            prompt = MEETING_ANALYSIS_PROMPT.format(transcript=transcript)
            response_text = await self._generate_with_ollama(prompt, schema)

            # Try to parse JSON
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                service_logger.warning(f"JSON parsing failed, attempting cleanup: {e}")
                # Try to extract JSON from response (sometimes models add extra text)
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                raise

        except Exception as e:
            service_logger.error(f"Structured output extraction failed: {e}")
            return await self._extract_with_fallback(transcript)

    async def _extract_with_fallback(self, transcript: str) -> Dict[str, Any]:
        """Fallback extraction using regex patterns and simple prompts."""
        service_logger.info("Using fallback extraction methods")

        try:
            # Get basic summary first
            simple_prompt = SIMPLE_SUMMARY_PROMPT.format(transcript=transcript)
            summary_text = await self._generate_with_ollama(simple_prompt)

            # Extract structured data using regex patterns
            extracted_data = {
                "executive_summary": self._extract_summary_from_text(summary_text),
                "action_items": self._extract_action_items_regex(transcript),
                "key_decisions": self._extract_decisions_regex(transcript),
                "risks": self._extract_risks_regex(transcript),
                "user_stories": self._extract_user_stories_regex(transcript),
                "next_steps": self._extract_next_steps_regex(transcript),
                "key_topics": self._extract_topics_regex(transcript),
                "participants": self._extract_participants_regex(transcript),
                "sentiment": "neutral",  # Default sentiment
            }

            return extracted_data

        except Exception as e:
            service_logger.error(f"Fallback extraction failed: {e}")
            return self._create_minimal_response(transcript)

    def _extract_summary_from_text(self, text: str) -> str:
        """Extract executive summary from generated text."""
        # Look for summary patterns
        lines = text.strip().split("\n")
        summary_lines = []

        for line in lines:
            if line.strip() and not line.strip().startswith("-"):
                summary_lines.append(line.strip())
                if len(summary_lines) >= 3:  # Limit to 3 sentences
                    break

        return (
            " ".join(summary_lines)
            if summary_lines
            else "Meeting summary not available."
        )

    def _extract_action_items_regex(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract action items using regex patterns."""
        action_items = []

        for pattern in FALLBACK_EXTRACTION_PATTERNS["action_items"]:
            matches = re.findall(pattern, transcript, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    task = match[1] if len(match) > 1 else match[0]
                    assignee = match[0] if len(match) > 1 else "Unassigned"
                    due_date = match[2] if len(match) > 2 else None
                else:
                    task = match
                    assignee = "Unassigned"
                    due_date = None

                if task and len(task.strip()) > 3:
                    action_items.append(
                        {
                            "task": task.strip(),
                            "assignee": assignee.strip(),
                            "due_date": due_date,
                            "priority": "medium",
                            "context": "",
                            "status": "pending",
                        }
                    )

        return action_items[:10]  # Limit to 10 items

    def _extract_decisions_regex(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract decisions using regex patterns."""
        decisions = []

        for pattern in FALLBACK_EXTRACTION_PATTERNS["decisions"]:
            matches = re.findall(pattern, transcript, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if match and len(match.strip()) > 3:
                    decisions.append(
                        {
                            "decision": match.strip(),
                            "made_by": "Team",
                            "rationale": "",
                            "impact": "medium",
                            "status": "approved",
                        }
                    )

        return decisions[:5]  # Limit to 5 decisions

    def _extract_risks_regex(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract risks using regex patterns."""
        risks = []

        for pattern in FALLBACK_EXTRACTION_PATTERNS["risks"]:
            matches = re.findall(pattern, transcript, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if match and len(match.strip()) > 3:
                    risks.append(
                        {
                            "risk": match.strip(),
                            "impact": "medium",
                            "likelihood": "medium",
                            "mitigation": "",
                            "owner": None,
                        }
                    )

        return risks[:5]  # Limit to 5 risks

    def _extract_user_stories_regex(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract user stories using regex patterns."""
        user_stories = []

        for pattern in FALLBACK_EXTRACTION_PATTERNS["user_stories"]:
            matches = re.findall(pattern, transcript, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 3:
                    story = f"As a {match[0]}, I want {match[1]}, so that {match[2]}"
                else:
                    story = match if isinstance(match, str) else str(match)

                if story and len(story.strip()) > 10:
                    user_stories.append(
                        {
                            "story": story.strip(),
                            "acceptance_criteria": [],
                            "priority": "medium",
                            "epic": None,
                        }
                    )

        return user_stories[:3]  # Limit to 3 stories

    def _extract_next_steps_regex(self, transcript: str) -> List[str]:
        """Extract next steps from transcript."""
        next_steps = []

        # Look for explicit next steps mentions
        next_step_patterns = [
            r"next steps?:\s*(.+?)(?:\n|$)",
            r"follow[- ]up:\s*(.+?)(?:\n|$)",
            r"action plan:\s*(.+?)(?:\n|$)",
        ]

        for pattern in next_step_patterns:
            matches = re.findall(pattern, transcript, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if match and len(match.strip()) > 3:
                    next_steps.append(match.strip())

        return next_steps[:5]  # Limit to 5 steps

    def _extract_topics_regex(self, transcript: str) -> List[str]:
        """Extract key topics from transcript."""
        # Simple topic extraction based on repeated important words
        words = re.findall(r"\b[A-Z][a-z]+\b", transcript)
        word_count = {}

        for word in words:
            if len(word) > 3:  # Skip short words
                word_count[word] = word_count.get(word, 0) + 1

        # Get top topics
        topics = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:5]
        topic_list = [topic[0] for topic in topics]

        # Ensure at least one topic (validation requirement)
        if not topic_list:
            topic_list = ["General Discussion"]

        return topic_list

    def _extract_participants_regex(self, transcript: str) -> List[str]:
        """Extract participant names from transcript."""
        participants = set()

        for pattern in FALLBACK_EXTRACTION_PATTERNS["participants"]:
            matches = re.findall(pattern, transcript, re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    name = match[1] if len(match) > 1 else match[0]
                else:
                    name = match

                if name and len(name.strip()) > 1:
                    participants.add(name.strip())

        return list(participants)[:10]  # Limit to 10 participants

    def _create_minimal_response(self, transcript: str) -> Dict[str, Any]:
        """Create minimal response when all extraction methods fail."""
        # Ensure we meet minimum validation requirements
        return {
            "executive_summary": "Meeting transcript processed. Unable to generate detailed summary due to extraction limitations.",
            "action_items": [],
            "key_decisions": [],
            "risks": [],
            "user_stories": [],
            "next_steps": [],
            "key_topics": ["General Discussion"],  # At least one topic required
            "participants": [],
            "sentiment": "neutral",
        }

    async def summarize_transcript(
        self, meeting_id: str, transcript_text: str
    ) -> MeetingSummary:
        """
        Generate a comprehensive meeting summary using Ollama.

        Args:
            meeting_id: Unique identifier for the meeting
            transcript_text: Raw transcript content to analyze

        Returns:
            MeetingSummary: Structured summary with extracted information
        """
        self.processing_start_time = time.time()

        service_logger.info(
            "Starting Ollama transcript analysis",
            extra={
                "meeting_id": meeting_id,
                "transcript_length": len(transcript_text),
                "model": self.model,
            },
        )

        try:
            # Check Ollama health
            if not await self._check_ollama_health():
                raise Exception("Ollama server is not accessible")

            # Extract structured data
            extracted_data = await self._extract_with_structured_output(transcript_text)

            # Convert to Pydantic models
            action_items = []
            for item_data in extracted_data.get("action_items", []):
                try:
                    # Parse due_date string to datetime if provided
                    due_date = None
                    if item_data.get("due_date"):
                        try:
                            from dateutil import parser

                            due_date = parser.parse(item_data["due_date"])
                            # Ensure timezone awareness
                            if due_date.tzinfo is None:
                                due_date = due_date.replace(tzinfo=UTC)
                        except Exception:
                            # If parsing fails, leave as None
                            due_date = None

                    action_item = ActionItem(
                        id=str(uuid4()),
                        task=item_data["task"],
                        assignee=item_data["assignee"],
                        due_date=due_date,
                        priority=ActionItemPriority(
                            item_data.get("priority", "medium")
                        ),
                        status=ActionItemStatus(item_data.get("status", "pending")),
                        context=item_data.get("context", ""),
                        created_at=datetime.now(UTC),
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
                        created_at=datetime.now(UTC),
                    )
                    decisions.append(decision)
                except (ValidationError, ValueError) as e:
                    service_logger.warning(f"Invalid decision data: {e}")
                    continue

            # Create meeting summary
            processing_time = time.time() - self.processing_start_time

            summary = MeetingSummary(
                meeting_id=meeting_id,
                summary=extracted_data.get(
                    "executive_summary", "Meeting transcript processed successfully."
                ),
                key_topics=extracted_data.get("key_topics", ["General Discussion"]),
                action_items=action_items,
                decisions=decisions,
                participants=extracted_data.get("participants", []),
                sentiment=extracted_data.get("sentiment", "neutral"),
                next_steps=extracted_data.get("next_steps", []),
                confidence_score=self._calculate_confidence_score(extracted_data),
                processing_time_seconds=round(processing_time, 2),
                created_at=datetime.now(UTC),
            )

            service_logger.info(
                "Ollama analysis completed successfully",
                extra={
                    "meeting_id": meeting_id,
                    "processing_time": processing_time,
                    "action_items_found": len(action_items),
                    "decisions_found": len(decisions),
                    "confidence_score": summary.confidence_score,
                },
            )

            return summary

        except Exception as e:
            processing_time = (
                time.time() - self.processing_start_time
                if self.processing_start_time
                else 0
            )

            service_logger.error(
                "Ollama analysis failed",
                extra={
                    "meeting_id": meeting_id,
                    "error": str(e),
                    "processing_time": processing_time,
                },
            )

            # Return minimal summary on failure (ensure validation requirements are met)
            return MeetingSummary(
                meeting_id=meeting_id,
                summary=f"Analysis failed: {str(e)}",
                key_topics=["Processing Error"],  # At least one topic required
                action_items=[],
                decisions=[],
                participants=[],
                sentiment="neutral",
                next_steps=[],
                confidence_score=0.0,
                processing_time_seconds=processing_time,
                created_at=datetime.now(UTC),
            )

    def _calculate_confidence_score(self, extracted_data: Dict[str, Any]) -> float:
        """Calculate confidence score based on extraction completeness."""
        score = 0.0
        max_score = 100.0

        # Base score for having summary
        if extracted_data.get("executive_summary"):
            score += 20.0

        # Score for action items
        action_items = extracted_data.get("action_items", [])
        if action_items:
            score += min(20.0, len(action_items) * 4.0)

        # Score for decisions
        decisions = extracted_data.get("key_decisions", [])
        if decisions:
            score += min(20.0, len(decisions) * 5.0)

        # Score for participants
        participants = extracted_data.get("participants", [])
        if participants:
            score += min(15.0, len(participants) * 2.0)

        # Score for topics
        topics = extracted_data.get("key_topics", [])
        if topics:
            score += min(10.0, len(topics) * 2.0)

        # Score for next steps
        next_steps = extracted_data.get("next_steps", [])
        if next_steps:
            score += min(10.0, len(next_steps) * 2.0)

        # Score for risks
        risks = extracted_data.get("risks", [])
        if risks:
            score += min(5.0, len(risks) * 1.0)

        return min(score, max_score) / max_score

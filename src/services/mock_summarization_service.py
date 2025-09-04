"""Mock AI summarization service using rule-based text analysis."""

import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.core.logging import processing_logger, service_logger
from src.models.action_item import ActionItem, ActionItemPriority, ActionItemStatus
from src.models.decision import Decision, DecisionImpact, DecisionStatus
from src.models.transcript import MeetingSummary

from .base import SummarizationServiceBase
from .text_analysis_utils import (
    extract_action_items_from_text,
    extract_decisions_from_text,
    extract_participants_from_transcript,
    generate_executive_summary,
    identify_key_topics_from_text,
)


class MockSummarizationService(SummarizationServiceBase):
    """
    Mock AI summarization service using intelligent rule-based analysis.

    This service provides realistic summarization without external AI APIs by using:
    - Keyword pattern matching for action items and decisions
    - Participant name extraction from transcript formats
    - Topic identification through frequency analysis
    - Contextual summary generation

    Designed to validate system architecture and provide meaningful test data.
    """

    def __init__(self):
        """Initialize the mock summarization service."""
        self.processing_start_time = None
        service_logger.info("MockSummarizationService initialized")

    async def summarize_transcript(self, meeting_id: str, transcript_text: str) -> MeetingSummary:
        """
        Generate a comprehensive meeting summary using rule-based analysis.

        Args:
            meeting_id: Unique identifier for the meeting
            transcript_text: Raw transcript content to analyze

        Returns:
            MeetingSummary with extracted information

        Raises:
            ProcessingError: If analysis fails
        """
        start_time = time.time()
        self.processing_start_time = start_time

        processing_logger.log_processing_start(
            meeting_id=meeting_id,
            processing_type="mock_summarization",
            text_length=len(transcript_text)
        )

        try:
            service_logger.info(
                f"Starting mock summarization for meeting {meeting_id}",
                text_length=len(transcript_text),
                word_count=len(transcript_text.split())
            )

            # Extract all components in parallel
            participants = await self.extract_participants(transcript_text)
            key_topics = await self.identify_key_topics(transcript_text)

            # Generate executive summary
            summary_text = generate_executive_summary(transcript_text, participants, key_topics)

            # Extract structured data
            action_items_data = await self.extract_action_items(transcript_text)
            decisions_data = await self.extract_decisions(transcript_text)

            # Convert to model instances
            action_items = [
                ActionItem(
                    id=uuid4(),
                    task=item["task"],
                    assignee=item["assignee"],
                    due_date=self._parse_due_date(item.get("due_date")),
                    priority=ActionItemPriority(item["priority"]),
                    status=ActionItemStatus(item["status"]),
                    context=item.get("context", "")
                )
                for item in action_items_data
            ]

            decisions = [
                Decision(
                    id=uuid4(),
                    decision=decision["decision"],
                    made_by=decision["made_by"],
                    rationale=decision["rationale"],
                    impact=DecisionImpact(decision["impact"]),
                    status=DecisionStatus(decision["status"]),
                    context=decision.get("context", "")
                )
                for decision in decisions_data
            ]

            # Identify next steps from action items
            next_steps = self._generate_next_steps(action_items, decisions)

            # Calculate sentiment (simple keyword-based approach)
            sentiment = self._analyze_sentiment(transcript_text)

            # Calculate confidence score based on extraction quality
            confidence_score = self._calculate_confidence_score(
                transcript_text, participants, action_items, decisions, key_topics
            )

            processing_time = time.time() - start_time

            # Create the meeting summary
            meeting_summary = MeetingSummary(
                id=uuid4(),
                meeting_id=meeting_id,
                summary=summary_text,
                key_topics=key_topics[:20],  # Limit to top 20 topics
                decisions=decisions,
                action_items=action_items,
                participants=participants,
                sentiment=sentiment,
                next_steps=next_steps,
                confidence_score=confidence_score,
                processing_time_seconds=processing_time
            )

            processing_logger.log_processing_complete(
                meeting_id=meeting_id,
                processing_type="mock_summarization",
                duration_seconds=processing_time,
                participants_count=len(participants),
                action_items_count=len(action_items),
                decisions_count=len(decisions),
                topics_count=len(key_topics),
                confidence_score=confidence_score
            )

            service_logger.info(
                f"Mock summarization completed for meeting {meeting_id}",
                processing_time_seconds=round(processing_time, 2),
                participants_count=len(participants),
                action_items_count=len(action_items),
                decisions_count=len(decisions),
                confidence_score=round(confidence_score, 2)
            )

            return meeting_summary

        except Exception as e:
            processing_time = time.time() - start_time

            processing_logger.log_processing_error(
                meeting_id=meeting_id,
                processing_type="mock_summarization",
                error=str(e),
                duration_seconds=processing_time
            )

            service_logger.error(
                f"Mock summarization failed for meeting {meeting_id}",
                error=str(e),
                error_type=type(e).__name__,
                processing_time_seconds=round(processing_time, 2)
            )

            raise

    async def extract_action_items(self, transcript_text: str) -> list[dict[str, Any]]:
        """Extract action items from transcript using pattern matching."""
        try:
            return extract_action_items_from_text(transcript_text)
        except Exception as e:
            service_logger.error(f"Failed to extract action items: {str(e)}")
            return []

    async def extract_decisions(self, transcript_text: str) -> list[dict[str, Any]]:
        """Extract decisions from transcript using keyword patterns."""
        try:
            return extract_decisions_from_text(transcript_text)
        except Exception as e:
            service_logger.error(f"Failed to extract decisions: {str(e)}")
            return []

    async def identify_key_topics(self, transcript_text: str) -> list[str]:
        """Identify key topics through frequency analysis and pattern matching."""
        try:
            return identify_key_topics_from_text(transcript_text)
        except Exception as e:
            service_logger.error(f"Failed to identify key topics: {str(e)}")
            return ["General Discussion"]

    async def extract_participants(self, transcript_text: str) -> list[str]:
        """Extract participant names from transcript using speaker patterns."""
        try:
            return extract_participants_from_transcript(transcript_text)
        except Exception as e:
            service_logger.error(f"Failed to extract participants: {str(e)}")
            return ["Unknown Speaker"]

    def _parse_due_date(self, due_date_str: str | None) -> datetime | None:
        """Parse due date string into datetime object."""
        if not due_date_str:
            return None

        try:
            # Simple parsing for common formats
            # This could be enhanced with more sophisticated date parsing
            if "today" in due_date_str.lower():
                return datetime.now(UTC)
            elif "tomorrow" in due_date_str.lower():
                return datetime.now(UTC).replace(day=datetime.now().day + 1)
            elif "friday" in due_date_str.lower():
                # Simple approximation - would need proper date logic
                return datetime.now(UTC).replace(day=datetime.now().day + 7)

            # For now, return None for unparseable dates
            return None

        except Exception:
            return None

    def _generate_next_steps(self, action_items: list[ActionItem], decisions: list[Decision]) -> list[str]:
        """Generate next steps based on action items and decisions."""
        next_steps = []

        # Add high-priority action items as next steps
        high_priority_items = [
            item for item in action_items
            if item.priority == ActionItemPriority.HIGH
        ][:3]  # Limit to top 3

        for item in high_priority_items:
            next_steps.append(f"{item.assignee}: {item.task}")

        # Add approved decisions that require follow-up
        approved_decisions = [
            decision for decision in decisions
            if decision.status == DecisionStatus.APPROVED and
            decision.impact in [DecisionImpact.HIGH, DecisionImpact.MEDIUM]
        ][:2]  # Limit to top 2

        for decision in approved_decisions:
            next_steps.append(f"Follow up on: {decision.decision}")

        # Add generic next steps if we don't have enough specific ones
        if len(next_steps) < 2:
            next_steps.extend([
                "Schedule follow-up meeting to review progress",
                "Distribute meeting notes to all participants"
            ])

        return next_steps[:5]  # Limit to 5 next steps

    def _analyze_sentiment(self, transcript_text: str) -> str:
        """Analyze overall meeting sentiment using keyword analysis."""
        text_lower = transcript_text.lower()

        positive_keywords = [
            "great", "excellent", "good", "positive", "success", "achieved",
            "accomplished", "agree", "approved", "happy", "pleased", "excited"
        ]

        negative_keywords = [
            "problem", "issue", "concern", "difficult", "challenge", "failed",
            "rejected", "disappointed", "frustrated", "worried", "delayed"
        ]

        neutral_keywords = [
            "discussed", "reviewed", "considered", "noted", "mentioned",
            "presented", "updated", "reported", "planned"
        ]

        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
        neutral_count = sum(1 for keyword in neutral_keywords if keyword in text_lower)

        total_sentiment_words = positive_count + negative_count + neutral_count

        if total_sentiment_words == 0:
            return "neutral"

        positive_ratio = positive_count / total_sentiment_words
        negative_ratio = negative_count / total_sentiment_words

        if positive_ratio > 0.4:
            return "positive"
        elif negative_ratio > 0.3:
            return "negative"
        else:
            return "neutral"

    def _calculate_confidence_score(
        self,
        transcript_text: str,
        participants: list[str],
        action_items: list[ActionItem],
        decisions: list[Decision],
        key_topics: list[str]
    ) -> float:
        """
        Calculate confidence score based on extraction quality indicators.

        Returns score between 0.0 and 1.0 indicating confidence in the analysis.
        """
        score_factors = []

        # Text quality factors
        word_count = len(transcript_text.split())
        if word_count > 500:
            score_factors.append(0.9)  # Good length for analysis
        elif word_count > 100:
            score_factors.append(0.7)
        else:
            score_factors.append(0.4)  # Too short for reliable analysis

        # Participant identification success
        if len(participants) > 1:
            score_factors.append(0.8)  # Multiple participants identified
        elif len(participants) == 1:
            score_factors.append(0.6)
        else:
            score_factors.append(0.3)  # No clear participants

        # Action item extraction success
        if len(action_items) > 3:
            score_factors.append(0.8)  # Good number of action items
        elif len(action_items) > 0:
            score_factors.append(0.7)
        else:
            score_factors.append(0.5)  # No action items found

        # Decision extraction success
        if len(decisions) > 0:
            score_factors.append(0.8)  # Decisions found
        else:
            score_factors.append(0.6)  # No decisions (common in some meetings)

        # Topic identification success
        if len(key_topics) > 5:
            score_factors.append(0.8)
        elif len(key_topics) > 2:
            score_factors.append(0.7)
        else:
            score_factors.append(0.5)

        # Calculate weighted average (mock service gets lower confidence than real AI)
        base_confidence = sum(score_factors) / len(score_factors)

        # Apply mock service penalty (rule-based is less confident than AI)
        mock_penalty = 0.15
        final_confidence = max(0.0, base_confidence - mock_penalty)

        return round(final_confidence, 2)

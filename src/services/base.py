"""Base classes for summarization services."""

from abc import ABC, abstractmethod
from typing import Any

from src.models.transcript import MeetingSummary


class SummarizationServiceBase(ABC):
    """Abstract base class for transcript summarization services."""

    @abstractmethod
    async def summarize_transcript(self, meeting_id: str, transcript_text: str) -> MeetingSummary:
        """
        Generate a comprehensive summary from meeting transcript text.

        Args:
            meeting_id: Unique identifier for the meeting
            transcript_text: Raw transcript content to analyze

        Returns:
            MeetingSummary object with extracted information

        Raises:
            ProcessingError: If summarization fails
        """
        pass

    @abstractmethod
    async def extract_action_items(self, transcript_text: str) -> list[dict[str, Any]]:
        """
        Extract action items from transcript text.

        Args:
            transcript_text: Raw transcript content

        Returns:
            List of action item dictionaries with task, assignee, priority, etc.
        """
        pass

    @abstractmethod
    async def extract_decisions(self, transcript_text: str) -> list[dict[str, Any]]:
        """
        Extract decisions from transcript text.

        Args:
            transcript_text: Raw transcript content

        Returns:
            List of decision dictionaries with decision, rationale, impact, etc.
        """
        pass

    @abstractmethod
    async def identify_key_topics(self, transcript_text: str) -> list[str]:
        """
        Identify main topics discussed in the meeting.

        Args:
            transcript_text: Raw transcript content

        Returns:
            List of key topic strings
        """
        pass

    @abstractmethod
    async def extract_participants(self, transcript_text: str) -> list[str]:
        """
        Extract participant names from transcript.

        Args:
            transcript_text: Raw transcript content

        Returns:
            List of participant names
        """
        pass

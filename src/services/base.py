"""Base classes for summarization services."""

from abc import ABC, abstractmethod
from typing import Any

from src.models.transcript import MeetingSummary


class SummarizationServiceBase(ABC):
    """Abstract base class for transcript summarization services."""

    @abstractmethod
    async def summarize_transcript(
        self, meeting_id: str, transcript_text: str
    ) -> MeetingSummary:
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

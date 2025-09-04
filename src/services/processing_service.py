"""Processing service for orchestrating transcript analysis pipeline."""

import time
from typing import Any, Optional

from src.core.exceptions import ProcessingError
from src.core.logging import processing_logger, service_logger
from src.models.transcript import ProcessingStatus, TranscriptStatus

from .base import SummarizationServiceBase
from .summarization_factory import create_summarization_service


class ProcessingService:
    """
    Orchestrates the full transcript processing pipeline.

    This service coordinates:
    1. Loading transcript data from storage
    2. Calling the summarization service
    3. Storing the results
    4. Updating processing status throughout
    5. Error handling and recovery
    """

    def __init__(
        self,
        summarization_service: Optional[SummarizationServiceBase] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize the processing service.

        Args:
            summarization_service: Service to use for AI processing.
            provider: LLM provider to use (ollama, openai, anthropic, mock).
            api_key: API key for cloud providers.
        """
        if summarization_service:
            self.summarization_service = summarization_service
        else:
            self.summarization_service = create_summarization_service(provider, api_key)

        service_logger.info(
            "ProcessingService initialized",
            extra={
                "summarization_service": type(self.summarization_service).__name__,
                "provider": getattr(self.summarization_service, "provider", "local"),
                "has_custom_api_key": bool(api_key),
            },
        )

    async def process_meeting(
        self,
        meeting_id: str,
        meetings_storage: dict[str, dict[str, Any]],
        processing_status_storage: dict[str, ProcessingStatus],
        summaries_storage: dict[str, Any],
    ) -> None:
        """
        Process a meeting transcript through the full AI pipeline.

        Args:
            meeting_id: Unique identifier for the meeting
            meetings_storage: In-memory storage for meeting data
            processing_status_storage: In-memory storage for processing status
            summaries_storage: In-memory storage for generated summaries

        Raises:
            ProcessingError: If any step in the pipeline fails
        """
        start_time = time.time()

        try:
            processing_logger.info(f"Starting processing for meeting: {meeting_id}")

            # Validate meeting exists
            if meeting_id not in meetings_storage:
                raise ProcessingError(
                    meeting_id=meeting_id,
                    stage="validation",
                    details="Meeting not found in storage",
                )

            # Get meeting data
            meeting_data = meetings_storage[meeting_id]

            # Update status to processing
            await self._update_processing_status(
                meeting_id,
                processing_status_storage,
                TranscriptStatus.PROCESSING,
                progress=10,
            )

            # Extract transcript text
            transcript_text = await self._extract_transcript_text(
                meeting_id, meeting_data
            )

            # Update progress
            await self._update_processing_status(
                meeting_id,
                processing_status_storage,
                TranscriptStatus.PROCESSING,
                progress=30,
            )

            # Process through AI service
            processing_logger.log_processing_start(
                meeting_id=meeting_id,
                processing_type="ai_summarization",
                text_length=len(transcript_text),
            )

            # Call summarization service
            summary = await self.summarization_service.summarize_transcript(
                meeting_id=meeting_id, transcript_text=transcript_text
            )

            # Update progress
            await self._update_processing_status(
                meeting_id,
                processing_status_storage,
                TranscriptStatus.PROCESSING,
                progress=80,
            )

            # Store the summary
            summaries_storage[meeting_id] = summary

            # Mark as completed
            await self._update_processing_status(
                meeting_id,
                processing_status_storage,
                TranscriptStatus.COMPLETED,
                progress=100,
            )

            processing_time = time.time() - start_time

            processing_logger.log_processing_complete(
                meeting_id=meeting_id,
                processing_type="full_pipeline",
                duration_seconds=processing_time,
                summary_confidence=summary.confidence_score,
                action_items_count=len(summary.action_items),
                decisions_count=len(summary.decisions),
            )

            service_logger.info(
                f"Processing completed successfully for meeting: {meeting_id}",
                processing_time_seconds=round(processing_time, 2),
                action_items_count=len(summary.action_items),
                decisions_count=len(summary.decisions),
                confidence_score=round(summary.confidence_score, 2),
            )

        except ProcessingError as e:
            # Re-raise ProcessingError as-is
            await self._handle_processing_error(
                meeting_id, processing_status_storage, str(e)
            )
            raise

        except Exception as e:
            # Wrap other exceptions in ProcessingError
            error_message = f"Unexpected error during processing: {str(e)}"
            await self._handle_processing_error(
                meeting_id, processing_status_storage, error_message
            )

            raise ProcessingError(
                meeting_id=meeting_id,
                stage="processing",
                details=error_message,
                original_error=e,
            ) from e

    async def _extract_transcript_text(
        self, meeting_id: str, meeting_data: dict[str, Any]
    ) -> str:
        """
        Extract transcript text from meeting data.

        Args:
            meeting_id: Meeting identifier for error context
            meeting_data: Raw meeting data from storage

        Returns:
            Clean transcript text ready for analysis

        Raises:
            ProcessingError: If no valid transcript text is found
        """
        try:
            # Try to get raw text first
            if meeting_data.get("raw_text"):
                return meeting_data["raw_text"]

            # If no raw text, check if we need to transcribe audio
            if meeting_data.get("audio_url"):
                # For now, mock service doesn't handle audio transcription
                # In a real implementation, this would call a transcription service
                raise ProcessingError(
                    meeting_id=meeting_id,
                    stage="transcription",
                    details="Audio transcription not implemented in mock service",
                )

            # No valid input found
            raise ProcessingError(
                meeting_id=meeting_id,
                stage="input_validation",
                details="No transcript text or audio file found",
            )

        except ProcessingError:
            raise
        except Exception as e:
            raise ProcessingError(
                meeting_id=meeting_id,
                stage="text_extraction",
                details=f"Failed to extract transcript text: {str(e)}",
                original_error=e,
            ) from e

    async def _update_processing_status(
        self,
        meeting_id: str,
        processing_status_storage: dict[str, ProcessingStatus],
        status: TranscriptStatus,
        progress: int = None,
    ) -> None:
        """
        Update processing status in storage.

        Args:
            meeting_id: Meeting identifier
            processing_status_storage: Status storage dictionary
            status: New processing status
            progress: Progress percentage (0-100)
        """
        try:
            if meeting_id in processing_status_storage:
                processing_status = processing_status_storage[meeting_id]
                processing_status.status = status
                if progress is not None:
                    processing_status.progress_percentage = progress
                processing_status.mark_updated()
            else:
                # Create new status if it doesn't exist
                processing_status = ProcessingStatus(
                    meeting_id=meeting_id,
                    status=status,
                    progress_percentage=progress or 0,
                )
                processing_status_storage[meeting_id] = processing_status

            service_logger.debug(
                f"Updated processing status for meeting: {meeting_id}",
                status=status.value,
                progress=progress,
            )

        except Exception as e:
            service_logger.error(
                f"Failed to update processing status for meeting: {meeting_id}",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Don't raise - status update failure shouldn't stop processing

    async def _handle_processing_error(
        self,
        meeting_id: str,
        processing_status_storage: dict[str, ProcessingStatus],
        error_message: str,
    ) -> None:
        """
        Handle processing error by updating status and logging.

        Args:
            meeting_id: Meeting identifier
            processing_status_storage: Status storage dictionary
            error_message: Error description
        """
        try:
            if meeting_id in processing_status_storage:
                processing_status = processing_status_storage[meeting_id]
                processing_status.mark_failed(error_message)

            processing_logger.log_processing_error(
                meeting_id=meeting_id,
                processing_type="full_pipeline",
                error=error_message,
            )

            service_logger.error(
                f"Processing failed for meeting: {meeting_id}",
                error_message=error_message,
            )

        except Exception as e:
            service_logger.error(
                f"Failed to handle processing error for meeting: {meeting_id}",
                original_error=error_message,
                handling_error=str(e),
            )


# Convenience function for getting the appropriate processing service
def get_processing_service(
    provider: Optional[str] = None, api_key: Optional[str] = None
) -> ProcessingService:
    """
    Factory function to get the appropriate processing service.

    Args:
        provider: LLM provider to use (ollama, openai, anthropic, mock)
        api_key: API key for cloud providers

    Returns:
        Configured ProcessingService instance
    """
    return ProcessingService(provider=provider, api_key=api_key)


# Background task processing for async operations
async def process_meeting_background(
    meeting_id: str,
    meetings_storage: dict[str, dict[str, Any]],
    processing_status_storage: dict[str, ProcessingStatus],
    summaries_storage: dict[str, Any],
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
) -> None:
    """
    Background task wrapper for processing meetings.

    This function is designed to be called as a background task
    so that the API can return immediately while processing continues.

    Args:
        meeting_id: Meeting to process
        meetings_storage: Meeting data storage
        processing_status_storage: Processing status storage
        summaries_storage: Summary results storage
        provider: LLM provider to use (ollama, openai, anthropic, mock)
        api_key: API key for cloud providers
    """
    processing_service = get_processing_service(provider, api_key)

    try:
        await processing_service.process_meeting(
            meeting_id=meeting_id,
            meetings_storage=meetings_storage,
            processing_status_storage=processing_status_storage,
            summaries_storage=summaries_storage,
        )

        service_logger.info(
            f"Background processing completed for meeting: {meeting_id}"
        )

    except Exception as e:
        service_logger.error(
            f"Background processing failed for meeting: {meeting_id}",
            error=str(e),
            error_type=type(e).__name__,
        )
        # Error handling is already done in process_meeting, just log here

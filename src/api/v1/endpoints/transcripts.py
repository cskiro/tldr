"""Transcript upload and processing endpoints."""

import os
from datetime import datetime
from typing import Any

import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from pydantic import BaseModel, ValidationError

from src.core.exceptions import (
    DuplicateMeetingError,
    FileTooLargeError,
    MeetingNotFoundError,
    ProcessingError,
    UnsupportedFormatError,
)
from src.core.exceptions import ValidationError as CustomValidationError
from src.core.logging import api_logger, processing_logger
from src.models.base import APIResponse
from src.models.transcript import (
    MeetingType,
    ProcessingStatus,
    TranscriptInput,
    TranscriptStatus,
)
from src.services.processing_service import process_meeting_background

router = APIRouter()

# Configuration constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
SUPPORTED_AUDIO_FORMATS = [
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/wave",
    "audio/m4a",
    "audio/mp4",
    "audio/ogg",
    "video/mp4",
]
UPLOAD_DIR = "uploads"

# In-memory storage for demo purposes
# TODO: Replace with actual database
meetings_storage: dict[str, dict[str, Any]] = {}
processing_status_storage: dict[str, ProcessingStatus] = {}
summaries_storage: dict[str, Any] = {}  # Store generated summaries


class ProcessingRequest(BaseModel):
    """Request model for transcript processing."""

    meeting_id: str
    options: dict[str, Any] | None = None
    provider: str | None = None
    api_key: str | None = None


async def validate_audio_file(file: UploadFile) -> None:
    """
    Validate uploaded audio file.

    Args:
        file: Uploaded file object

    Raises:
        FileTooLargeError: If file exceeds size limit
        UnsupportedFormatError: If file format is not supported
    """
    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise FileTooLargeError(actual_size=file.size, max_size=MAX_FILE_SIZE)

    # Check content type
    if file.content_type not in SUPPORTED_AUDIO_FORMATS:
        raise UnsupportedFormatError(
            format_type=file.content_type or "unknown",
            supported_formats=SUPPORTED_AUDIO_FORMATS,
        )


async def save_uploaded_file(file: UploadFile, meeting_id: str) -> str:
    """
    Save uploaded file to disk.

    Args:
        file: Uploaded file object
        meeting_id: Meeting identifier for filename

    Returns:
        Path to saved file

    Raises:
        ProcessingError: If file save fails
    """
    try:
        # Ensure upload directory exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # Generate safe filename with validated extension
        original_filename = file.filename or "audio.mp3"

        # Extract and validate file extension securely
        file_extension = os.path.splitext(original_filename)[1].lower()

        # Whitelist allowed extensions to prevent path injection
        allowed_extensions = {".mp3", ".mp4", ".wav", ".m4a", ".ogg"}
        if file_extension not in allowed_extensions:
            file_extension = ".mp3"  # Default to safe extension

        # Create safe filename using only validated components
        safe_filename = (
            f"{meeting_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
        )

        # Ensure the filename is safe and normalize the path
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        file_path = os.path.normpath(file_path)

        # Verify the final path is within the upload directory (prevent directory traversal)
        if not file_path.startswith(os.path.normpath(UPLOAD_DIR)):
            raise ProcessingError(
                meeting_id=meeting_id,
                stage="file_upload",
                details="Invalid file path detected",
                original_error=None,
            )

        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        api_logger.info(
            f"File saved successfully: {safe_filename}",
            meeting_id=meeting_id,
            file_path=file_path,
            file_size=len(content),
        )

        return file_path

    except Exception as e:
        raise ProcessingError(
            meeting_id=meeting_id,
            stage="file_upload",
            details=f"Failed to save uploaded file: {str(e)}",
            original_error=e,
        ) from e


@router.post("/upload", response_model=APIResponse)
async def upload_transcript(
    # Form fields for multipart upload
    meeting_id: str = Form(..., description="Unique meeting identifier"),
    participants: str = Form(..., description="JSON string of participant names"),
    duration_minutes: int = Form(..., description="Meeting duration in minutes"),
    meeting_type: str = Form(..., description="Type of meeting"),
    raw_text: str | None = Form(None, description="Raw transcript text"),
    metadata: str | None = Form(None, description="JSON string of additional metadata"),
    # Optional audio file
    audio_file: UploadFile | None = File(None, description="Audio file to transcribe"),
):
    """
    Upload a meeting transcript or audio file for processing.

    This endpoint accepts either:
    1. Raw transcript text directly
    2. Audio file for transcription
    3. Both text and audio file

    The transcript data is validated and stored for later processing.
    """
    try:
        api_logger.info(f"Upload request received for meeting: {meeting_id}")

        # Check for duplicate meeting
        if meeting_id in meetings_storage:
            raise DuplicateMeetingError(meeting_id=meeting_id)

        # Parse participants (assuming comma-separated string for form data)
        try:
            if participants.startswith("[") and participants.endswith("]"):
                # Handle JSON array string
                import json

                participant_list = json.loads(participants)
            else:
                # Handle comma-separated string
                participant_list = [
                    name.strip() for name in participants.split(",") if name.strip()
                ]
        except (json.JSONDecodeError, AttributeError):
            participant_list = [participants] if participants else []

        # Parse metadata if provided
        metadata_dict = {}
        if metadata:
            try:
                import json

                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                api_logger.warning(
                    f"Invalid metadata JSON for meeting {meeting_id}: {metadata}"
                )

        # Handle audio file if provided
        audio_url = None
        if audio_file:
            await validate_audio_file(audio_file)
            file_path = await save_uploaded_file(audio_file, meeting_id)
            audio_url = file_path

        # Validate that we have either text or audio
        if not raw_text and not audio_url:
            raise CustomValidationError(
                field_errors={
                    "content": "Either raw_text or audio_file must be provided"
                }
            )

        # Create transcript input model
        # Convert meeting_type string to enum
        try:
            meeting_type_enum = MeetingType(meeting_type.lower())
        except ValueError:
            # If invalid meeting type, default to 'general'
            meeting_type_enum = MeetingType.OTHER

        transcript_data = {
            "meeting_id": meeting_id,
            "raw_text": raw_text,
            "audio_url": audio_url,
            "participants": participant_list,
            "duration_minutes": duration_minutes,
            "meeting_type": meeting_type_enum,
            "metadata": metadata_dict,
        }

        # Validate with Pydantic model
        try:
            transcript = TranscriptInput(**transcript_data)
        except ValidationError as e:
            # Convert Pydantic validation errors to our custom format
            field_errors = {}
            for error in e.errors():
                field_name = ".".join(str(loc) for loc in error["loc"])
                field_errors[field_name] = error["msg"]
            raise CustomValidationError(field_errors=field_errors) from None

        # Store transcript data
        meetings_storage[meeting_id] = transcript.model_dump()

        # Create initial processing status
        processing_status = ProcessingStatus(
            meeting_id=meeting_id, status=TranscriptStatus.UPLOADED
        )

        # Debug log to check the status type
        api_logger.info(
            f"Created processing status with type: {type(processing_status.status)}"
        )
        api_logger.info(f"Processing status value: {processing_status.status}")
        processing_status_storage[meeting_id] = processing_status

        api_logger.info(
            f"Transcript uploaded successfully: {meeting_id}",
            meeting_id=meeting_id,
            has_audio=audio_url is not None,
            has_text=raw_text is not None,
            participant_count=len(participant_list),
            duration_minutes=duration_minutes,
        )

        # Return success response
        return APIResponse.success_response(
            message="Transcript uploaded successfully",
            data={
                "meeting_id": meeting_id,
                "status": processing_status.status,  # Remove .value since it's a str enum
                "has_audio": audio_url is not None,
                "has_text": raw_text is not None,
                "participants": transcript.participants,
                "duration_minutes": transcript.duration_minutes,
                "created_at": processing_status.created_at.isoformat(),
            },
        )

    except (
        DuplicateMeetingError,
        FileTooLargeError,
        UnsupportedFormatError,
        CustomValidationError,
        ProcessingError,
    ) as e:
        # Re-raise known exceptions to be handled by global handler
        raise e

    except Exception as e:
        api_logger.error(
            f"Unexpected error during upload: {meeting_id}",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise ProcessingError(
            meeting_id=meeting_id,
            stage="upload",
            details=f"Unexpected error during upload: {str(e)}",
            original_error=e,
        ) from e


@router.post("/process", response_model=APIResponse)
async def process_transcript(
    request: ProcessingRequest, background_tasks: BackgroundTasks
):
    """
    Start processing a previously uploaded transcript.

    This endpoint triggers the AI processing pipeline which includes:
    1. Transcription (if audio file was provided)
    2. Text analysis and summarization
    3. Action item extraction
    4. Decision identification
    5. Key topic analysis
    """
    meeting_id = request.meeting_id

    try:
        processing_logger.info(f"Processing request received for meeting: {meeting_id}")

        # Check if meeting exists
        if meeting_id not in meetings_storage:
            raise MeetingNotFoundError(meeting_id=meeting_id)

        # Get current processing status
        if meeting_id not in processing_status_storage:
            # Create status if it doesn't exist (shouldn't happen in normal flow)
            processing_status = ProcessingStatus(
                meeting_id=meeting_id, status=TranscriptStatus.UPLOADED
            )
            processing_status_storage[meeting_id] = processing_status
        else:
            processing_status = processing_status_storage[meeting_id]

        # Check if already processing or completed
        if processing_status.status == TranscriptStatus.PROCESSING:
            raise ProcessingError(
                meeting_id=meeting_id,
                stage="process_start",
                details="Meeting is already being processed",
            )

        if processing_status.status == TranscriptStatus.COMPLETED:
            return APIResponse.success_response(
                message="Meeting already processed",
                data={
                    "meeting_id": meeting_id,
                    "status": processing_status.status,
                    "progress_percentage": processing_status.progress_percentage,
                    "completed_at": (
                        processing_status.updated_at.isoformat()
                        if processing_status.updated_at
                        else None
                    ),
                },
            )

        # Start processing
        estimated_seconds = 120  # Default estimate
        meeting_data = meetings_storage[meeting_id]

        # Adjust estimate based on content
        if meeting_data.get("raw_text"):
            # Estimate based on text length
            text_length = len(meeting_data["raw_text"])
            estimated_seconds = max(30, min(300, text_length // 1000 * 10))
        elif meeting_data.get("audio_url"):
            # Estimate based on duration (transcription + processing)
            duration_minutes = meeting_data.get("duration_minutes", 30)
            estimated_seconds = max(60, duration_minutes * 2)

        # Update processing status
        processing_status.mark_processing(estimated_seconds=estimated_seconds)
        processing_status_storage[meeting_id] = processing_status

        # Start actual async processing task in background
        background_tasks.add_task(
            process_meeting_background,
            meeting_id=meeting_id,
            meetings_storage=meetings_storage,
            processing_status_storage=processing_status_storage,
            summaries_storage=summaries_storage,
            provider=request.provider,
            api_key=request.api_key,
        )

        processing_logger.log_processing_start(
            meeting_id=meeting_id,
            processing_type="transcript_analysis",
            estimated_seconds=estimated_seconds,
            options=request.options,
        )

        # Return processing started response
        return APIResponse.success_response(
            message="Processing started",
            data={
                "meeting_id": meeting_id,
                "status": processing_status.status,
                "progress_percentage": processing_status.progress_percentage,
                "estimated_completion": (
                    processing_status.estimated_completion.isoformat()
                    if processing_status.estimated_completion
                    else None
                ),
                "processing_options": request.options,
                "started_at": (
                    processing_status.updated_at.isoformat()
                    if processing_status.updated_at
                    else None
                ),
            },
        )

    except (MeetingNotFoundError, ProcessingError) as e:
        # Re-raise known exceptions
        raise e

    except Exception as e:
        processing_logger.error(
            f"Unexpected error during processing start: {meeting_id}",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise ProcessingError(
            meeting_id=meeting_id,
            stage="process_start",
            details=f"Unexpected error starting processing: {str(e)}",
            original_error=e,
        ) from e


@router.get("/{meeting_id}/status", response_model=APIResponse)
async def get_processing_status(meeting_id: str):
    """
    Get the current processing status of a meeting transcript.

    Returns detailed information about the processing progress,
    including current stage, percentage complete, and any errors.
    """
    try:
        api_logger.info(f"Status check requested for meeting: {meeting_id}")

        # Check if meeting exists
        if meeting_id not in meetings_storage:
            raise MeetingNotFoundError(meeting_id=meeting_id)

        # Get processing status
        if meeting_id not in processing_status_storage:
            # Create default status if missing
            processing_status = ProcessingStatus(
                meeting_id=meeting_id, status=TranscriptStatus.UPLOADED
            )
            processing_status_storage[meeting_id] = processing_status
        else:
            processing_status = processing_status_storage[meeting_id]

        # Prepare status response
        status_data = {
            "meeting_id": meeting_id,
            "status": processing_status.status,
            "progress_percentage": processing_status.progress_percentage,
            "created_at": processing_status.created_at.isoformat(),
            "updated_at": (
                processing_status.updated_at.isoformat()
                if processing_status.updated_at
                else None
            ),
        }

        # Add optional fields based on status
        if processing_status.estimated_completion:
            status_data["estimated_completion"] = (
                processing_status.estimated_completion.isoformat()
            )

        if processing_status.error_message:
            status_data["error_message"] = processing_status.error_message

        return APIResponse.success_response(
            message="Status retrieved successfully", data=status_data
        )

    except MeetingNotFoundError as e:
        raise e

    except Exception as e:
        api_logger.error(
            f"Unexpected error getting status: {meeting_id}",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise ProcessingError(
            meeting_id=meeting_id,
            stage="status_check",
            details=f"Unexpected error checking status: {str(e)}",
            original_error=e,
        ) from e

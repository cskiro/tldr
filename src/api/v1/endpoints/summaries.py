"""Summary retrieval and export endpoints."""

import zipfile
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from src.core.exceptions import MeetingNotFoundError, ProcessingError, ValidationError
from src.core.logging import api_logger
from src.models.action_item import ActionItem, ActionItemPriority, ActionItemStatus
from src.models.base import APIResponse, PaginatedResponse
from src.models.decision import Decision, DecisionImpact, DecisionStatus
from src.models.transcript import MeetingSummary, TranscriptStatus

router = APIRouter()

# In-memory storage for demo purposes
# TODO: Replace with actual database
summaries_storage: dict[str, MeetingSummary] = {}

# Import from transcripts module for status checking
from src.api.v1.endpoints.transcripts import meetings_storage, processing_status_storage


class ExportRequest(BaseModel):
    """Request model for summary export."""
    meeting_id: str = Field(..., description="Meeting ID to export")
    format: str = Field(..., description="Export format: json, markdown, or pdf")
    options: dict[str, Any] | None = Field(None, description="Export formatting options")


class BulkExportRequest(BaseModel):
    """Request model for bulk summary export."""
    meeting_ids: list[str] = Field(..., max_items=100, description="Meeting IDs to export")
    format: str = Field(..., description="Export format: json, markdown, or pdf")
    options: dict[str, Any] | None = Field(None, description="Export formatting options")


def create_sample_summary(meeting_id: str) -> MeetingSummary:
    """
    Create a sample summary for demonstration purposes.
    
    TODO: Replace with actual AI-generated summary
    """
    return MeetingSummary(
        meeting_id=meeting_id,
        summary="Team discussed quarterly planning and project timelines. Key decisions were made about technology stack and resource allocation.",
        key_topics=["Quarterly Planning", "Technology Stack", "Resource Allocation", "Timeline Review"],
        participants=["Alice Johnson", "Bob Smith", "Carol Davis"],
        action_items=[
            ActionItem(
                task="Complete budget analysis for Q1 projects",
                assignee="Alice Johnson",
                status=ActionItemStatus.PENDING,
                priority=ActionItemPriority.HIGH,
                due_date=datetime.now(UTC).replace(day=15, hour=17, minute=0, second=0),
                context="Required for next week's board presentation"
            ),
            ActionItem(
                task="Set up development environment for React project",
                assignee="Bob Smith",
                status=ActionItemStatus.IN_PROGRESS,
                priority=ActionItemPriority.MEDIUM,
                context="Using latest React 18 with TypeScript configuration"
            ),
            ActionItem(
                task="Schedule follow-up meeting with design team",
                assignee="Carol Davis",
                status=ActionItemStatus.COMPLETED,
                priority=ActionItemPriority.LOW,
                completed_at=datetime.now(UTC),
                completion_notes="Meeting scheduled for next Tuesday at 2 PM"
            )
        ],
        decisions=[
            Decision(
                decision="Use React 18 with TypeScript for the new frontend project",
                made_by="Carol Davis (Tech Lead)",
                rationale="Better team expertise and improved type safety for maintainability",
                impact=DecisionImpact.HIGH,
                status=DecisionStatus.APPROVED,
                confidence_level=0.9,
                affected_teams=["Frontend", "QA"],
                alternatives_considered=["Vue.js", "Angular"],
                tags=["technology", "frontend", "framework"]
            ),
            Decision(
                decision="Increase sprint duration from 2 to 3 weeks",
                made_by="Alice Johnson (Project Manager)",
                rationale="Allow more time for thorough testing and reduce sprint planning overhead",
                impact=DecisionImpact.MEDIUM,
                status=DecisionStatus.APPROVED,
                confidence_level=0.7,
                affected_teams=["Development", "QA"],
                tags=["process", "agile", "sprint"]
            )
        ],
        confidence_score=0.89,
        processing_time_seconds=23.5,
        sentiment="positive",
        next_steps=[
            "Review budget proposals by end of week",
            "Start React project setup immediately",
            "Schedule design team collaboration session"
        ]
    )


def format_summary_as_markdown(summary: MeetingSummary, options: dict[str, Any] = None) -> str:
    """
    Format a meeting summary as Markdown.
    
    Args:
        summary: Meeting summary to format
        options: Formatting options
        
    Returns:
        Markdown-formatted summary
    """
    options = options or {}
    include_timestamps = options.get("include_timestamps", True)
    group_by_participant = options.get("group_by_participant", False)
    include_sentiment = options.get("include_sentiment", True)

    # Header
    md_lines = [
        "# Meeting Summary",
        "",
        f"**Meeting ID:** {summary.meeting_id}",
        f"**Date:** {summary.created_at.strftime('%Y-%m-%d')}",
        f"**Time:** {summary.created_at.strftime('%H:%M UTC')}",
        f"**Participants:** {', '.join(summary.participants)}",
        "",
    ]

    # Executive Summary
    md_lines.extend([
        "## Executive Summary",
        "",
        summary.summary,
        "",
    ])

    # Key Topics
    md_lines.extend([
        "## Key Topics Discussed",
        "",
    ])

    for topic in summary.key_topics:
        md_lines.append(f"- {topic}")

    md_lines.append("")

    # Decisions Made
    if summary.decisions:
        md_lines.extend([
            "## Decisions Made",
            "",
            "| Decision | Made By | Rationale | Impact | Status |",
            "|----------|---------|-----------|---------|---------|",
        ])

        for decision in summary.decisions:
            impact = decision.impact.title()
            status = decision.status.title()
            md_lines.append(
                f"| {decision.decision} | {decision.made_by} | {decision.rationale} | {impact} | {status} |"
            )

        md_lines.append("")

    # Action Items
    if summary.action_items:
        md_lines.extend([
            "## Action Items",
            "",
            "| Task | Assignee | Due Date | Priority | Status | Context |",
            "|------|----------|----------|----------|---------|---------|",
        ])

        for item in summary.action_items:
            due_date = item.due_date.strftime('%Y-%m-%d') if item.due_date else "Not set"
            priority = item.priority.title()
            status = item.status.replace('_', ' ').title()
            context = item.context or "N/A"

            md_lines.append(
                f"| {item.task} | {item.assignee} | {due_date} | {priority} | {status} | {context} |"
            )

        md_lines.append("")

    # Next Steps
    if summary.next_steps:
        md_lines.extend([
            "## Next Steps",
            "",
        ])

        for step in summary.next_steps:
            md_lines.append(f"- {step}")

        md_lines.append("")

    # Additional Info
    md_lines.extend([
        "## Additional Information",
        "",
        f"**Completion Rate:** {summary.completion_percentage:.1f}%",
        f"**Processing Time:** {summary.processing_time_seconds:.1f} seconds",
        f"**Confidence Score:** {summary.confidence_score:.2f}",
    ])

    if include_sentiment and summary.sentiment:
        md_lines.append(f"**Meeting Sentiment:** {summary.sentiment.title()}")

    if include_timestamps:
        md_lines.extend([
            "",
            f"*Generated on {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}*",
        ])

    return "\n".join(md_lines)


@router.get("/{meeting_id}", response_model=APIResponse)
async def get_summary(
    meeting_id: str,
    action_status: str | None = Query(None, description="Filter action items by status"),
    include_completed: bool = Query(True, description="Include completed action items")
):
    """
    Retrieve a completed meeting summary.
    
    Returns the processed summary including action items, decisions,
    and key topics. If processing is still in progress, returns
    the current processing status instead.
    """
    try:
        api_logger.info(f"Summary retrieval requested for meeting: {meeting_id}")

        # Check if meeting exists
        if meeting_id not in meetings_storage:
            raise MeetingNotFoundError(meeting_id=meeting_id)

        # Check processing status
        processing_status = processing_status_storage.get(meeting_id)
        if not processing_status:
            raise MeetingNotFoundError(meeting_id=meeting_id)

        # If still processing, return status instead of summary
        if processing_status.status == TranscriptStatus.PROCESSING:
            return JSONResponse(
                status_code=202,
                content=APIResponse.success_response(
                    message="Processing in progress",
                    data={
                        "meeting_id": meeting_id,
                        "status": processing_status.status,
                        "progress_percentage": processing_status.progress_percentage,
                        "estimated_completion": processing_status.estimated_completion.isoformat() if processing_status.estimated_completion else None
                    }
                ).model_dump()
            )

        # If processing failed, return error info
        if processing_status.status == TranscriptStatus.FAILED:
            raise ProcessingError(
                meeting_id=meeting_id,
                stage="summary_generation",
                details=processing_status.error_message or "Processing failed"
            )

        # Get or create summary (for demo, create if doesn't exist)
        if meeting_id not in summaries_storage:
            # TODO: Get actual summary from database
            # For demo, create a sample summary
            summaries_storage[meeting_id] = create_sample_summary(meeting_id)

        summary = summaries_storage[meeting_id]

        # Apply filters if requested
        filtered_summary = summary.model_copy()

        if action_status or not include_completed:
            filtered_items = []
            for item in summary.action_items:
                # Filter by status if specified
                if action_status and item.status != action_status.lower():
                    continue

                # Filter completed items if requested
                if not include_completed and item.status == ActionItemStatus.COMPLETED:
                    continue

                filtered_items.append(item)

            filtered_summary.action_items = filtered_items

        api_logger.info(
            f"Summary retrieved successfully: {meeting_id}",
            action_item_count=len(filtered_summary.action_items),
            decision_count=len(filtered_summary.decisions),
            confidence_score=summary.confidence_score
        )

        return APIResponse.success_response(
            message="Summary retrieved successfully",
            data=filtered_summary.model_dump()
        )

    except (MeetingNotFoundError, ProcessingError) as e:
        raise e

    except Exception as e:
        api_logger.error(
            f"Unexpected error retrieving summary: {meeting_id}",
            error=str(e),
            error_type=type(e).__name__
        )
        raise ProcessingError(
            meeting_id=meeting_id,
            stage="summary_retrieval",
            details=f"Unexpected error retrieving summary: {str(e)}",
            original_error=e
        )


@router.get("", response_model=PaginatedResponse)
async def list_summaries(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    start_date: str | None = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date filter (YYYY-MM-DD)"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc or desc")
):
    """
    List meeting summaries with pagination and filtering.
    
    Supports filtering by date range and sorting by various fields.
    Returns paginated results with total count information.
    """
    try:
        api_logger.info("Summary list requested", page=page, size=size)

        # For demo, create some sample summaries if none exist
        if not summaries_storage:
            for i in range(1, 26):  # Create 25 sample summaries
                sample_id = f"sample_meeting_{i:03d}"
                summaries_storage[sample_id] = create_sample_summary(sample_id)

        # Get all summaries
        all_summaries = list(summaries_storage.values())

        # Apply date filters if provided
        filtered_summaries = all_summaries

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date).replace(tzinfo=UTC)
                filtered_summaries = [s for s in filtered_summaries if s.created_at >= start_dt]
            except ValueError:
                raise ValidationError({"start_date": "Invalid date format. Use YYYY-MM-DD"})

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=UTC)
                filtered_summaries = [s for s in filtered_summaries if s.created_at <= end_dt]
            except ValueError:
                raise ValidationError({"end_date": "Invalid date format. Use YYYY-MM-DD"})

        # Sort summaries
        reverse_order = sort_order.lower() == "desc"

        if sort_by == "created_at":
            filtered_summaries.sort(key=lambda x: x.created_at, reverse=reverse_order)
        elif sort_by == "meeting_id":
            filtered_summaries.sort(key=lambda x: x.meeting_id, reverse=reverse_order)
        elif sort_by == "confidence_score":
            filtered_summaries.sort(key=lambda x: x.confidence_score, reverse=reverse_order)

        # Paginate
        total = len(filtered_summaries)
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        page_summaries = filtered_summaries[start_idx:end_idx]

        # Convert to dict format for response
        summary_items = [summary.model_dump() for summary in page_summaries]

        return PaginatedResponse.create(
            items=summary_items,
            total=total,
            page=page,
            size=size
        )

    except ValidationError as e:
        raise e

    except Exception as e:
        api_logger.error(
            "Unexpected error listing summaries",
            error=str(e),
            error_type=type(e).__name__
        )
        raise ProcessingError(
            meeting_id="",
            stage="summary_list",
            details=f"Unexpected error listing summaries: {str(e)}",
            original_error=e
        )


@router.post("/export", response_model=None)
async def export_summary(request: ExportRequest):
    """
    Export a meeting summary in the specified format.
    
    Supported formats:
    - json: Returns the summary as JSON
    - markdown: Returns the summary formatted as Markdown
    - pdf: Returns the summary as a PDF file (TODO: implement)
    """
    meeting_id = request.meeting_id
    export_format = request.format.lower()

    try:
        api_logger.info(f"Export requested: {meeting_id} as {export_format}")

        # Validate format
        if export_format not in ["json", "markdown", "pdf"]:
            raise ValidationError({"format": "Unsupported format. Use: json, markdown, or pdf"})

        # Check if meeting/summary exists
        if meeting_id not in meetings_storage:
            raise MeetingNotFoundError(meeting_id=meeting_id)

        # Get or create summary
        if meeting_id not in summaries_storage:
            summaries_storage[meeting_id] = create_sample_summary(meeting_id)

        summary = summaries_storage[meeting_id]

        # Export based on format
        if export_format == "json":
            content = summary.model_dump_json(indent=2)
            media_type = "application/json"
            filename = f"meeting_summary_{meeting_id}.json"

            return Response(
                content=content,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )

        elif export_format == "markdown":
            content = format_summary_as_markdown(summary, request.options)
            media_type = "text/markdown"
            filename = f"meeting_summary_{meeting_id}.md"

            return Response(
                content=content,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )

        elif export_format == "pdf":
            # TODO: Implement PDF export using reportlab or similar
            raise ValidationError({"format": "PDF export not yet implemented"})

    except (MeetingNotFoundError, ValidationError) as e:
        raise e

    except Exception as e:
        api_logger.error(
            f"Unexpected error exporting summary: {meeting_id}",
            format=export_format,
            error=str(e),
            error_type=type(e).__name__
        )
        raise ProcessingError(
            meeting_id=meeting_id,
            stage="summary_export",
            details=f"Unexpected error exporting summary: {str(e)}",
            original_error=e
        )


@router.post("/bulk-export", response_model=None)
async def bulk_export_summaries(request: BulkExportRequest):
    """
    Export multiple meeting summaries as a ZIP archive.
    
    Creates individual files for each summary in the requested format
    and packages them into a downloadable ZIP file.
    """
    export_format = request.format.lower()
    meeting_ids = request.meeting_ids

    try:
        api_logger.info(f"Bulk export requested: {len(meeting_ids)} meetings as {export_format}")

        # Validate format
        if export_format not in ["json", "markdown", "pdf"]:
            raise ValidationError({"format": "Unsupported format. Use: json, markdown, or pdf"})

        # Validate meeting count
        if len(meeting_ids) > 100:
            raise ValidationError({"meeting_ids": "Maximum 100 meetings allowed for bulk export"})

        # Create temporary ZIP file
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            exported_count = 0

            for meeting_id in meeting_ids:
                try:
                    # Skip if meeting doesn't exist
                    if meeting_id not in meetings_storage:
                        api_logger.warning(f"Meeting not found in bulk export: {meeting_id}")
                        continue

                    # Get or create summary
                    if meeting_id not in summaries_storage:
                        summaries_storage[meeting_id] = create_sample_summary(meeting_id)

                    summary = summaries_storage[meeting_id]

                    # Generate content based on format
                    if export_format == "json":
                        content = summary.model_dump_json(indent=2)
                        filename = f"{meeting_id}.json"
                    elif export_format == "markdown":
                        content = format_summary_as_markdown(summary, request.options)
                        filename = f"{meeting_id}.md"
                    elif export_format == "pdf":
                        # TODO: Implement PDF export
                        api_logger.warning(f"PDF export not implemented, skipping: {meeting_id}")
                        continue

                    # Add to ZIP
                    zip_file.writestr(filename, content)
                    exported_count += 1

                except Exception as e:
                    api_logger.warning(
                        f"Failed to export meeting in bulk: {meeting_id}",
                        error=str(e)
                    )
                    continue

        # Prepare response
        zip_buffer.seek(0)
        zip_content = zip_buffer.getvalue()

        if exported_count == 0:
            raise ValidationError({"meeting_ids": "No valid meetings found for export"})

        filename = f"bulk_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

        return Response(
            content=zip_content,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except ValidationError as e:
        raise e

    except Exception as e:
        api_logger.error(
            "Unexpected error in bulk export",
            meeting_count=len(meeting_ids),
            format=export_format,
            error=str(e),
            error_type=type(e).__name__
        )
        raise ProcessingError(
            meeting_id="bulk",
            stage="bulk_export",
            details=f"Unexpected error in bulk export: {str(e)}",
            original_error=e
        )

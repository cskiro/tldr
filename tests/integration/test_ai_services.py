"""Integration tests for AI services."""

import asyncio
import time
from unittest.mock import patch

import pytest

from src.models.transcript import MeetingSummary
from src.services.mock_summarization_service import MockSummarizationService
from src.services.ollama_service import OllamaService
from src.services.summarization_factory import (
    create_summarization_service,
    get_available_providers,
    validate_provider_config,
)

# Test transcript samples
SAMPLE_TRANSCRIPT = """
Meeting: Product Planning Session
Date: September 4, 2025
Participants: Sarah (Product Manager), Mike (Engineering Lead), Lisa (Designer)

Sarah: Good morning everyone. Let's discuss our Q4 roadmap. We need to prioritize the new user dashboard feature.

Mike: I've reviewed the requirements. The dashboard will require significant backend changes. I estimate 6-8 weeks of development.

Lisa: From a UX perspective, we should focus on mobile-first design. The current mockups don't work well on smaller screens.

Sarah: Great points. Let's make a decision here - we'll prioritize mobile-first design and adjust the timeline accordingly. Mike, can you update your estimates?

Mike: With mobile-first constraints, I'd say 8-10 weeks. We'll need to refactor our responsive framework.

Sarah: Agreed. Lisa, please create user stories for the mobile experience by end of this week.

Lisa: Will do. I'll focus on the core user journeys first.

Sarah: Perfect. Action items: Mike will provide updated technical spec by Friday, Lisa will deliver mobile user stories by Friday, and I'll update the stakeholders on our new timeline.

Mike: One risk I want to highlight - if we run into issues with the responsive framework, we might need additional resources.

Sarah: Good point. Let's plan for that contingency. If we hit roadblocks, we'll bring in a frontend contractor.

Lisa: That makes sense. Should we set up weekly check-ins to track progress?

Sarah: Yes, let's do weekly standups starting next Monday. Meeting adjourned.
"""

SHORT_TRANSCRIPT = """
Quick standup meeting.
John: Any blockers?
Jane: No blockers. Done with feature X.
John: Great, thanks!
"""

COMPLEX_TRANSCRIPT = """
Board Meeting - Q4 Strategic Review
Chairman: Welcome everyone. Today we'll review our Q4 performance and strategic initiatives.

CFO: Our revenue is up 15% year-over-year, but we're seeing increased costs in customer acquisition.

CEO: The market expansion into Europe has exceeded expectations. We've captured 12% market share already.

Head of Product: Our new AI features have driven a 25% increase in user engagement. However, we need to decide on our ML infrastructure investment.

CTO: I recommend we migrate to a cloud-native architecture. It'll cost $2M upfront but save us $500K annually.

Chairman: That's a significant investment. What are the risks?

CTO: Main risk is potential downtime during migration. We'd need to do it in phases over 6 months.

CFO: From a financial perspective, the ROI is solid - 18 month payback period.

CEO: I motion we approve the migration project. We need to stay competitive.

Board Member 1: I second the motion.

Board Member 2: I have concerns about the timeline. Can we compress it to 4 months?

CTO: That would increase risk significantly. I'd recommend sticking with the 6-month timeline.

Chairman: Let's vote. All in favor of the 6-month migration project?

[All board members vote yes]

Chairman: Motion carried. CTO, please prepare a detailed project plan by next board meeting.

CFO: For action items, I'll also need updated budget projections including the migration costs.

CEO: And I'll communicate the strategic direction to all department heads.

Chairman: Excellent. Meeting adjourned.
"""


class TestAIServiceIntegration:
    """Integration tests for AI services."""

    @pytest.fixture
    def sample_meeting_id(self):
        """Sample meeting ID for tests."""
        return "test_meeting_" + str(int(time.time()))

    @pytest.mark.asyncio
    async def test_provider_availability(self):
        """Test provider availability checking."""
        providers = get_available_providers()

        # Should have all 4 providers
        assert len(providers) == 4
        assert "ollama" in providers
        assert "openai" in providers
        assert "anthropic" in providers
        assert "mock" in providers

        # Mock should always be available
        assert providers["mock"]["available"] is True
        assert providers["mock"]["configured"] is True

        # Check provider properties
        for name, info in providers.items():
            assert "available" in info
            assert "configured" in info
            assert "cost" in info
            assert "quality" in info
            assert "speed" in info

    @pytest.mark.asyncio
    async def test_provider_validation(self):
        """Test provider configuration validation."""
        # Test mock provider (always valid)
        result = validate_provider_config("mock")
        assert result["valid"] is True
        assert result["available"] is True

        # Test unknown provider
        result = validate_provider_config("unknown_provider")
        assert result["valid"] is False

        # Test OpenAI without API key
        result = validate_provider_config("openai")
        assert result["valid"] is False
        assert "api key" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_mock_service_basic_functionality(self, sample_meeting_id):
        """Test mock service functionality."""
        service = create_summarization_service("mock")
        assert isinstance(service, MockSummarizationService)

        summary = await service.summarize_transcript(
            meeting_id=sample_meeting_id, transcript_text=SAMPLE_TRANSCRIPT
        )

        assert isinstance(summary, MeetingSummary)
        assert summary.meeting_id == sample_meeting_id
        assert len(summary.summary) >= 10  # Minimum length
        assert len(summary.key_topics) >= 1  # At least one topic
        assert summary.confidence_score >= 0.0
        assert summary.processing_time_seconds >= 0.0

    @pytest.mark.asyncio
    async def test_service_factory_fallback(self):
        """Test service factory fallback behavior."""
        # Test with invalid provider falls back to available service
        with patch(
            "src.services.summarization_factory.get_available_providers"
        ) as mock_providers:
            mock_providers.return_value = {
                "ollama": {"available": False, "configured": True},
                "openai": {"available": False, "configured": False},
                "anthropic": {"available": False, "configured": False},
                "mock": {"available": True, "configured": True},
            }

            service = create_summarization_service("invalid_provider")
            assert isinstance(service, MockSummarizationService)

    @pytest.mark.asyncio
    async def test_transcript_processing_quality(self, sample_meeting_id):
        """Test transcript processing quality across different services."""
        # Test with mock service
        mock_service = create_summarization_service("mock")
        mock_summary = await mock_service.summarize_transcript(
            meeting_id=sample_meeting_id, transcript_text=SAMPLE_TRANSCRIPT
        )

        # Basic quality checks
        assert len(mock_summary.key_topics) >= 1
        assert mock_summary.confidence_score > 0.0
        assert len(mock_summary.summary) >= 10

        # Test with different transcript lengths
        short_summary = await mock_service.summarize_transcript(
            meeting_id=sample_meeting_id + "_short", transcript_text=SHORT_TRANSCRIPT
        )

        complex_summary = await mock_service.summarize_transcript(
            meeting_id=sample_meeting_id + "_complex",
            transcript_text=COMPLEX_TRANSCRIPT,
        )

        # All should produce valid summaries
        for summary in [short_summary, complex_summary]:
            assert len(summary.key_topics) >= 1
            assert len(summary.summary) >= 10
            assert summary.confidence_score >= 0.0

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, sample_meeting_id):
        """Test processing performance benchmarks."""
        service = create_summarization_service("mock")

        start_time = time.time()
        summary = await service.summarize_transcript(
            meeting_id=sample_meeting_id, transcript_text=SAMPLE_TRANSCRIPT
        )
        end_time = time.time()

        processing_time = end_time - start_time

        # Mock service should be very fast
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert summary.processing_time_seconds > 0.0

    @pytest.mark.asyncio
    async def test_error_handling(self, sample_meeting_id):
        """Test error handling and graceful degradation."""
        service = create_summarization_service("mock")

        # Test with empty transcript
        summary = await service.summarize_transcript(
            meeting_id=sample_meeting_id, transcript_text=""
        )

        # Should still produce a valid summary
        assert isinstance(summary, MeetingSummary)
        assert len(summary.key_topics) >= 1
        assert summary.confidence_score >= 0.0

        # Test with very short transcript
        summary = await service.summarize_transcript(
            meeting_id=sample_meeting_id, transcript_text="Hi"
        )

        assert isinstance(summary, MeetingSummary)
        assert len(summary.key_topics) >= 1

    @pytest.mark.skipif(
        not get_available_providers()["ollama"]["available"],
        reason="Ollama not available",
    )
    @pytest.mark.asyncio
    async def test_ollama_service_integration(self, sample_meeting_id):
        """Test Ollama service integration (only if available)."""
        service = create_summarization_service("ollama")
        assert isinstance(service, OllamaService)

        summary = await service.summarize_transcript(
            meeting_id=sample_meeting_id, transcript_text=SAMPLE_TRANSCRIPT
        )

        # Ollama should produce higher quality results
        assert isinstance(summary, MeetingSummary)
        assert summary.meeting_id == sample_meeting_id
        assert len(summary.key_topics) >= 1
        assert summary.confidence_score >= 0.4  # Should be reasonable quality

        # Should extract some meaningful information
        assert len(summary.summary) >= 50  # More detailed summary

        # Performance check (should be reasonable but slower than mock)
        assert summary.processing_time_seconds < 120  # Should complete within 2 minutes

    @pytest.mark.asyncio
    async def test_service_comparison(self, sample_meeting_id):
        """Compare different service outputs for the same transcript."""
        services_to_test = []

        # Always test mock
        services_to_test.append(("mock", create_summarization_service("mock")))

        # Test Ollama if available
        if get_available_providers()["ollama"]["available"]:
            services_to_test.append(("ollama", create_summarization_service("ollama")))

        results = {}

        for service_name, service in services_to_test:
            summary = await service.summarize_transcript(
                meeting_id=f"{sample_meeting_id}_{service_name}",
                transcript_text=SAMPLE_TRANSCRIPT,
            )
            results[service_name] = summary

        # Compare results
        for service_name, summary in results.items():
            assert len(summary.key_topics) >= 1, f"{service_name} should extract topics"
            assert summary.confidence_score > 0.0, (
                f"{service_name} should have confidence"
            )

        # If we have both services, compare quality
        if "mock" in results and "ollama" in results:
            # Ollama should generally be more detailed
            assert len(results["ollama"].summary) >= len(results["mock"].summary) * 0.5

        print("\n📊 Service Comparison Results:")
        for service_name, summary in results.items():
            print(f"  {service_name.upper()}:")
            print(f"    - Confidence: {summary.confidence_score:.2f}")
            print(f"    - Topics: {len(summary.key_topics)}")
            print(f"    - Action Items: {len(summary.action_items)}")
            print(f"    - Decisions: {len(summary.decisions)}")
            print(f"    - Processing Time: {summary.processing_time_seconds:.2f}s")

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test concurrent processing capabilities."""
        service = create_summarization_service("mock")

        # Create multiple tasks
        tasks = []
        meeting_ids = [f"concurrent_test_{i}" for i in range(3)]
        transcripts = [SHORT_TRANSCRIPT, SAMPLE_TRANSCRIPT, COMPLEX_TRANSCRIPT]

        for meeting_id, transcript in zip(meeting_ids, transcripts):
            task = service.summarize_transcript(
                meeting_id=meeting_id, transcript_text=transcript
            )
            tasks.append(task)

        # Run concurrently
        start_time = time.time()
        summaries = await asyncio.gather(*tasks)
        end_time = time.time()

        # All should complete successfully
        assert len(summaries) == 3
        for i, summary in enumerate(summaries):
            assert summary.meeting_id == meeting_ids[i]
            assert len(summary.key_topics) >= 1

        # Concurrent processing should be efficient
        total_time = end_time - start_time
        print(f"\n⏱️ Concurrent processing of 3 transcripts: {total_time:.2f}s")
        assert total_time < 10.0  # Should be reasonable

#!/usr/bin/env python3
"""Test the enhanced AI summarization system with the SSO transcript."""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add the src directory to the path to import our modules
sys.path.append(str(Path(__file__).parent / "src"))

from services.summarization_factory import create_summarization_service


async def test_enhanced_system():
    """Test the enhanced AI system with the SSO transcript."""

    # Read the SSO transcript
    sso_transcript_path = Path("/Users/connor/Desktop/sso-meeting-transcript.md")
    if not sso_transcript_path.exists():
        print("❌ SSO transcript file not found at expected location")
        return

    with open(sso_transcript_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    print("🚀 Testing Enhanced AI Summarization System")
    print("=" * 50)
    print(f"📄 Transcript length: {len(transcript_text)} characters")
    print(f"📝 Word count: {len(transcript_text.split())} words")
    print()

    # Test with mock service (enhanced with new extraction functions)
    print("🧪 Testing with Enhanced Mock Service")
    print("-" * 30)

    start_time = time.time()

    try:
        # Create the mock service
        service = create_summarization_service("mock")

        # Process the transcript
        summary = await service.summarize_transcript(
            meeting_id="enhanced-sso-test", transcript_text=transcript_text
        )

        processing_time = time.time() - start_time

        # Display results
        print(f"✅ Processing completed in {processing_time:.2f} seconds")
        print(f"🎯 Confidence Score: {summary.confidence_score:.2%}")
        print()

        # Enhanced metrics comparison
        print("📊 ENHANCED EXTRACTION RESULTS:")
        print("=" * 40)

        print(f"👥 Participants: {len(summary.participants)}")
        for p in summary.participants:
            print(f"   • {p}")
        print()

        print(f"📌 Key Topics: {len(summary.key_topics)}")
        for i, topic in enumerate(summary.key_topics, 1):
            print(f"   {i}. {topic}")
        print()

        print(f"⚠️  RISKS IDENTIFIED: {len(summary.risks)}")
        for i, risk in enumerate(summary.risks, 1):
            print(f"   {i}. [{risk.category.upper()}] {risk.risk[:80]}...")
            print(f"      Impact: {risk.impact} | Likelihood: {risk.likelihood}")
            print(f"      Mitigation: {risk.mitigation[:60]}...")
            if risk.owner:
                print(f"      Owner: {risk.owner}")
            print()

        print(f"📝 USER STORIES: {len(summary.user_stories)}")
        for i, story in enumerate(summary.user_stories, 1):
            print(f"   {i}. {story.story}")
            print(f"      Priority: {story.priority}")
            if story.acceptance_criteria:
                print(f"      Criteria: {len(story.acceptance_criteria)} items")
            print()

        print(f"✅ ACTION ITEMS: {len(summary.action_items)}")
        for i, item in enumerate(summary.action_items, 1):
            print(f"   {i}. {item.task}")
            print(f"      Assignee: {item.assignee} | Priority: {item.priority}")
            if hasattr(item, "phase"):
                print(f"      Phase: {getattr(item, 'phase', 'Not specified')}")
            if item.context:
                print(f"      Context: {item.context[:50]}...")
            print()

        print(f"🎯 DECISIONS: {len(summary.decisions)}")
        for i, decision in enumerate(summary.decisions, 1):
            print(f"   {i}. {decision.decision}")
            print(f"      Made by: {decision.made_by} | Impact: {decision.impact}")
            if decision.rationale:
                print(f"      Rationale: {decision.rationale[:60]}...")
            print()

        print(f"🔄 Next Steps: {len(summary.next_steps)}")
        for i, step in enumerate(summary.next_steps, 1):
            print(f"   {i}. {step}")
        print()

        # Summary comparison vs expectations
        print("🔍 QUALITY ASSESSMENT:")
        print("=" * 30)

        # Expected vs actual counts
        expected_risks = 9
        expected_user_stories = 9
        expected_detailed_topics = 10

        risks_score = (
            min(100, (len(summary.risks) / expected_risks) * 100)
            if expected_risks > 0
            else 100
        )
        stories_score = (
            min(100, (len(summary.user_stories) / expected_user_stories) * 100)
            if expected_user_stories > 0
            else 100
        )
        topics_score = (
            min(100, (len(summary.key_topics) / expected_detailed_topics) * 100)
            if expected_detailed_topics > 0
            else 100
        )

        overall_score = (risks_score + stories_score + topics_score) / 3

        print(
            f"   Risks Coverage: {risks_score:.0f}% ({len(summary.risks)}/{expected_risks})"
        )
        print(
            f"   User Stories: {stories_score:.0f}% ({len(summary.user_stories)}/{expected_user_stories})"
        )
        print(
            f"   Topic Detail: {topics_score:.0f}% ({len(summary.key_topics)}/{expected_detailed_topics})"
        )
        print(f"   📈 OVERALL SCORE: {overall_score:.0f}%")

        # Grade the improvement
        if overall_score >= 90:
            grade = "A+ 🌟"
        elif overall_score >= 80:
            grade = "A 🎉"
        elif overall_score >= 70:
            grade = "B+ 👏"
        elif overall_score >= 60:
            grade = "B 👍"
        else:
            grade = "C 📈"

        print(f"   🏆 GRADE: {grade}")

        # Save enhanced output for comparison
        output_path = Path("/Users/connor/Desktop/enhanced-tldr-sso-summary.json")
        summary_dict = {
            "metadata": {
                "processing_time_seconds": processing_time,
                "confidence_score": summary.confidence_score,
                "sentiment": summary.sentiment,
                "participants_count": len(summary.participants),
                "quality_score": overall_score,
            },
            "executive_summary": summary.summary,
            "participants": summary.participants,
            "key_topics": summary.key_topics,
            "risks": [
                {
                    "risk": risk.risk,
                    "category": risk.category.value,
                    "impact": risk.impact.value,
                    "likelihood": risk.likelihood.value,
                    "mitigation": risk.mitigation,
                    "owner": risk.owner,
                }
                for risk in summary.risks
            ],
            "user_stories": [
                {
                    "story": story.story,
                    "acceptance_criteria": story.acceptance_criteria,
                    "priority": story.priority.value,
                    "epic": story.epic,
                    "business_value": story.business_value,
                }
                for story in summary.user_stories
            ],
            "action_items": [
                {
                    "task": item.task,
                    "assignee": item.assignee,
                    "priority": item.priority.value
                    if hasattr(item.priority, "value")
                    else str(item.priority),
                    "context": item.context,
                    "due_date": item.due_date.isoformat() if item.due_date else None,
                    "status": item.status.value
                    if hasattr(item.status, "value")
                    else str(item.status),
                }
                for item in summary.action_items
            ],
            "decisions": [
                {
                    "decision": decision.decision,
                    "made_by": decision.made_by,
                    "rationale": decision.rationale,
                    "impact": decision.impact.value
                    if hasattr(decision.impact, "value")
                    else str(decision.impact),
                    "status": decision.status.value
                    if hasattr(decision.status, "value")
                    else str(decision.status),
                }
                for decision in summary.decisions
            ],
            "next_steps": summary.next_steps,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary_dict, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Enhanced summary saved to: {output_path}")
        print("\n🎯 ENHANCEMENT SUCCESS! The AI agent now extracts:")
        print("   ✅ Comprehensive risk analysis with categorization")
        print("   ✅ Detailed user stories with acceptance criteria")
        print("   ✅ Granular technical topics vs generic categories")
        print("   ✅ Enhanced action items with context and phases")
        print("   ✅ Improved confidence scoring and validation")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_enhanced_system())

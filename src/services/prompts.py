"""
Structured prompts for meeting transcript analysis.

This module contains prompt templates optimized for extracting structured information
from meeting transcripts, including action items, decisions, risks, user stories,
and next steps.
"""

MEETING_ANALYSIS_PROMPT = """
Analyze this meeting transcript and extract structured information focusing on key decisions, action items, risks, user stories, and next steps.

TRANSCRIPT:
{transcript}

INSTRUCTIONS:
1. Create a concise executive summary (2-3 sentences)
2. Extract key decisions with decision makers and rationale
3. Identify action items with specific assignees and deadlines
4. Document risks and mitigation strategies
5. Extract user stories in proper format ("As a [user type], I want [goal], so that [benefit]")
6. List concrete next steps

Return your response as valid JSON with this exact structure:
{{
  "executive_summary": "string",
  "key_decisions": [
    {{
      "decision": "string",
      "made_by": "string",
      "rationale": "string",
      "impact": "high|medium|low",
      "status": "approved|pending|rejected"
    }}
  ],
  "action_items": [
    {{
      "task": "string",
      "assignee": "string", 
      "due_date": "YYYY-MM-DD or null",
      "priority": "high|medium|low",
      "context": "string",
      "status": "pending"
    }}
  ],
  "risks": [
    {{
      "risk": "string",
      "impact": "high|medium|low",
      "likelihood": "high|medium|low",
      "mitigation": "string",
      "owner": "string or null"
    }}
  ],
  "user_stories": [
    {{
      "story": "As a [user type], I want [goal], so that [benefit]",
      "acceptance_criteria": ["criteria1", "criteria2"],
      "priority": "high|medium|low",
      "epic": "string or null"
    }}
  ],
  "next_steps": ["step1", "step2"],
  "key_topics": ["topic1", "topic2"],
  "participants": ["person1", "person2"],
  "sentiment": "positive|neutral|negative|mixed"
}}
"""

# Fallback extraction patterns for when structured output fails
FALLBACK_EXTRACTION_PATTERNS = {
    "action_items": [
        r"(?:action item|todo|task|follow up):\s*(.+?)(?:\n|$)",
        r"(.+?)\s+(?:will|should|needs to)\s+(.+?)(?:\s+by\s+(\S+?))?(?:\n|$)",
        r"@(\w+)\s+(.+?)(?:\s+due\s+(\S+?))?(?:\n|$)",
        r"(\w+)\s+(?:to|will)\s+(.+?)(?:\s+by\s+(.+?))?(?:\n|$)"
    ],
    "decisions": [
        r"(?:decision|decided|agreed):\s*(.+?)(?:\n|$)",
        r"we\s+(?:decided|agreed)\s+(?:to|that)\s+(.+?)(?:\n|$)",
        r"(?:concluded|resolution):\s*(.+?)(?:\n|$)"
    ],
    "risks": [
        r"(?:risk|concern|issue|problem):\s*(.+?)(?:\n|$)",
        r"(?:might|could|may)\s+(?:be|cause|lead to)\s+(.+?)(?:\n|$)",
        r"(?:potential|possible)\s+(.+?)(?:\n|$)"
    ],
    "user_stories": [
        r"as\s+a\s+(.+?),\s*i\s+want\s+(.+?),?\s*so\s+that\s+(.+?)(?:\n|$)",
        r"user\s+story:\s*(.+?)(?:\n|$)"
    ],
    "participants": [
        r"\[(\d{2}:\d{2}:\d{2})\]\s+([A-Z][a-zA-Z\s]+):",
        r"^([A-Z][a-zA-Z\s]+):",
        r"@(\w+)"
    ]
}

# Simplified prompt for basic summarization (fallback)
SIMPLE_SUMMARY_PROMPT = """
Please provide a brief summary of this meeting transcript:

{transcript}

Include:
- Main topics discussed
- Key decisions made
- Action items with assignees
- Any concerns or risks mentioned
- Next steps
"""

# Confidence scoring prompt
CONFIDENCE_ASSESSMENT_PROMPT = """
Based on the transcript quality and content clarity, rate your confidence in extracting:
- Action items (0-100)
- Decisions (0-100)
- Participants (0-100)
- Overall accuracy (0-100)

Transcript: {transcript}
"""
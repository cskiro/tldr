"""
Structured prompts for meeting transcript analysis.

This module contains prompt templates optimized for extracting structured information
from meeting transcripts, including action items, decisions, risks, user stories,
and next steps.
"""

MEETING_ANALYSIS_PROMPT_V2 = """
You are an expert meeting analyst tasked with extracting comprehensive, actionable intelligence from meeting transcripts. Your goal is to provide a thorough analysis that stakeholders can use for project planning, risk management, and execution.

TRANSCRIPT:
{transcript}

CRITICAL REQUIREMENTS:
- Extract MINIMUM 5 risks with detailed impact/likelihood/mitigation strategies
- Identify MINIMUM 5 user stories in proper format with acceptance criteria
- Provide detailed action items with context, phases, and specific deadlines
- Generate 8+ granular technical topics (not generic categories)
- Include comprehensive decision rationale and business impact
- Ensure ALL extracted information is directly supported by transcript content

DETAILED ANALYSIS INSTRUCTIONS:

1. EXECUTIVE SUMMARY (2-3 sentences)
   - Capture the meeting's core purpose and key outcomes
   - Highlight most critical decisions and next steps
   - Include timeline and scope if discussed

2. KEY DECISIONS (Extract ALL decisions, not just major ones)
   - Look for: "decided", "agreed", "concluded", "approved", "rejected"
   - Include decision maker AND their reasoning
   - Assess business/technical impact (high/medium/low)
   - Note any conditions or dependencies
   
3. ACTION ITEMS (Be extremely detailed)
   - Identify specific tasks with clear ownership
   - Extract context: WHY this task is needed
   - Determine phase: immediate (week 1), development (weeks 2-7), testing/launch (weeks 8+)
   - Look for deadlines, timelines, dependencies
   - Include priority based on discussion urgency

4. RISKS (CRITICAL - identify comprehensive risk landscape)
   Technical Risks: complexity, timeline, integration challenges, scalability
   Security Risks: vulnerabilities, compliance, authentication, data protection
   Business Risks: customer impact, market timing, resource constraints, competition
   - For each risk: assess likelihood AND impact
   - Identify mitigation strategies mentioned or implied
   - Assign risk owners where discussed

5. USER STORIES (Extract from discussion context)
   - Look for user needs, customer requirements, persona discussions
   - Convert discussions into proper "As a [user], I want [goal], so that [benefit]" format
   - Include acceptance criteria based on requirements mentioned
   - Prioritize based on business value discussed

6. TECHNICAL TOPICS (Be granular and specific)
   - Break down broad topics into specific discussions
   - Instead of "Authentication" → "SAML configuration", "OIDC token handling", "Session management"
   - Include implementation details, technology choices, architecture decisions

7. NEXT STEPS (Organized by timeline)
   - Immediate actions (next 1-2 weeks)
   - Short-term milestones (next month)
   - Long-term objectives (2+ months)

EXAMPLES OF QUALITY EXPECTATIONS:

POOR Risk Example:
{{"risk": "Technical complexity", "impact": "medium", "likelihood": "medium", "mitigation": "careful planning"}}

EXCELLENT Risk Example:
{{"risk": "Dual protocol implementation (SAML + OIDC) may exceed 8-week timeline due to session management complexity and API middleware updates across all endpoints", "impact": "high", "likelihood": "medium", "mitigation": "Implement feature flags for gradual rollout, consider OIDC-first approach with SAML as phase 2, allocate additional senior developer resources", "owner": "Marcus Rodriguez", "category": "technical"}}

POOR Action Item:
{{"task": "Design completion", "assignee": "Lisa Thompson", "priority": "high"}}

EXCELLENT Action Item:
{{"task": "Complete UX designs for login flows, account linking interface, and admin dashboard", "assignee": "Lisa Thompson", "due_date": "2025-09-11", "priority": "high", "context": "Designs needed before development can begin, must include mobile-first approach and fallback mechanisms", "phase": "immediate", "dependencies": ["Security requirements from David"]}}

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
      "context": "string - WHY this task is needed",
      "phase": "immediate|development|testing|launch",
      "dependencies": ["list of dependencies or empty array"],
      "status": "pending"
    }}
  ],
  "risks": [
    {{
      "risk": "string - detailed description",
      "impact": "high|medium|low",
      "likelihood": "high|medium|low",
      "mitigation": "string - specific mitigation strategy",
      "owner": "string or null",
      "category": "technical|security|business"
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

# Original prompt (kept for backward compatibility)
MEETING_ANALYSIS_PROMPT = MEETING_ANALYSIS_PROMPT_V2

# Specialized risk extraction prompt for deep analysis
RISK_EXTRACTION_PROMPT = """
You are a risk management expert analyzing a meeting transcript. Identify ALL potential risks mentioned or implied in the discussion, categorizing them comprehensively.

TRANSCRIPT:
{transcript}

RISK CATEGORIES TO ANALYZE:

1. TECHNICAL RISKS
   - Implementation complexity and timeline risks
   - Integration challenges and compatibility issues
   - Scalability and performance concerns  
   - Technical debt and maintenance overhead
   - Skills gaps and learning curves

2. SECURITY RISKS
   - Vulnerabilities and attack vectors
   - Compliance and regulatory risks
   - Data protection and privacy concerns
   - Authentication and authorization weaknesses
   - Audit and monitoring gaps

3. BUSINESS RISKS
   - Customer satisfaction and adoption risks
   - Market timing and competitive threats
   - Resource constraints and budget overruns
   - Timeline delays and scope creep
   - Stakeholder alignment issues

For each risk, provide:
- Detailed description of the risk scenario
- Likelihood assessment (high/medium/low) with justification
- Impact assessment (high/medium/low) with consequences
- Specific mitigation strategies mentioned or recommended
- Risk owner if discussed

Return MINIMUM 5 risks as JSON array:
[
  {{
    "risk": "detailed risk description",
    "category": "technical|security|business",
    "likelihood": "high|medium|low",
    "likelihood_reason": "why this likelihood",
    "impact": "high|medium|low", 
    "impact_consequence": "what happens if this occurs",
    "mitigation": "specific mitigation strategy",
    "owner": "person responsible or null"
  }}
]
"""

# Specialized user story extraction prompt
USER_STORY_EXTRACTION_PROMPT = """
You are a product analyst extracting user stories from meeting discussions. Convert requirements, user needs, and feature discussions into properly formatted user stories.

TRANSCRIPT:
{transcript}

INSTRUCTIONS:
1. Look for discussions about user needs, customer requirements, and feature benefits
2. Convert each requirement into proper user story format
3. Extract acceptance criteria from detailed requirements mentioned
4. Prioritize based on business value and urgency discussed

USER STORY FORMAT: "As a [user type], I want [goal], so that [benefit]"

Return MINIMUM 5 user stories as JSON array:
[
  {{
    "story": "As a [specific user type], I want [specific goal], so that [specific benefit]",
    "acceptance_criteria": ["measurable criteria 1", "measurable criteria 2"],
    "priority": "high|medium|low",
    "business_value": "description of business impact",
    "epic": "larger feature group or null",
    "source_discussion": "brief quote from transcript"
  }}
]
"""

# Fallback extraction patterns for when structured output fails
FALLBACK_EXTRACTION_PATTERNS = {
    "action_items": [
        r"(?:action item|todo|task|follow up):\s*(.+?)(?:\n|$)",
        r"(.+?)\s+(?:will|should|needs to)\s+(.+?)(?:\s+by\s+(\S+?))?(?:\n|$)",
        r"@(\w+)\s+(.+?)(?:\s+due\s+(\S+?))?(?:\n|$)",
        r"(\w+)\s+(?:to|will)\s+(.+?)(?:\s+by\s+(.+?))?(?:\n|$)",
    ],
    "decisions": [
        r"(?:decision|decided|agreed):\s*(.+?)(?:\n|$)",
        r"we\s+(?:decided|agreed)\s+(?:to|that)\s+(.+?)(?:\n|$)",
        r"(?:concluded|resolution):\s*(.+?)(?:\n|$)",
    ],
    "risks": [
        r"(?:risk|concern|issue|problem):\s*(.+?)(?:\n|$)",
        r"(?:might|could|may)\s+(?:be|cause|lead to)\s+(.+?)(?:\n|$)",
        r"(?:potential|possible)\s+(.+?)(?:\n|$)",
    ],
    "user_stories": [
        r"as\s+a\s+(.+?),\s*i\s+want\s+(.+?),?\s*so\s+that\s+(.+?)(?:\n|$)",
        r"user\s+story:\s*(.+?)(?:\n|$)",
    ],
    "participants": [
        r"\[(\d{2}:\d{2}:\d{2})\]\s+([A-Z][a-zA-Z\s]+):",
        r"^([A-Z][a-zA-Z\s]+):",
        r"@(\w+)",
    ],
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

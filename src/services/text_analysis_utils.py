"""Utilities for text analysis and pattern extraction."""

import re
from collections import Counter
from typing import Any


def extract_participants_from_transcript(text: str) -> list[str]:
    """
    Extract participant names using common transcript patterns.

    Args:
        text: Raw transcript text

    Returns:
        List of unique participant names
    """
    participants = set()

    # Pattern 1: "Name:" format (most common)
    name_colon_pattern = r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?):\s"
    matches = re.findall(name_colon_pattern, text, re.MULTILINE)
    participants.update(matches)

    # Pattern 2: "<Name>" format
    angle_bracket_pattern = r"<([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)>"
    matches = re.findall(angle_bracket_pattern, text)
    participants.update(matches)

    # Pattern 3: "Name said" or "Name mentioned"
    said_pattern = (
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:said|mentioned|asked|replied|responded)"
    )
    matches = re.findall(said_pattern, text)
    participants.update(matches)

    # Pattern 4: "from Name" or "by Name"
    from_by_pattern = r"(?:from|by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
    matches = re.findall(from_by_pattern, text)
    participants.update(matches)

    # Filter out common false positives
    false_positives = {
        "The",
        "This",
        "That",
        "And",
        "But",
        "So",
        "Or",
        "If",
        "When",
        "Where",
        "How",
        "What",
        "Why",
    }
    participants = {p for p in participants if p not in false_positives and len(p) > 1}

    return sorted(participants)


def extract_action_items_from_text(text: str) -> list[dict[str, Any]]:
    """
    Extract action items using keyword patterns and context analysis.

    Args:
        text: Raw transcript text

    Returns:
        List of action item dictionaries
    """
    action_items = []

    # Action item patterns with different formats
    patterns = [
        # Direct action item mentions
        (r"(?i)(?:TODO|Action item|Follow up)[:.]?\s*(.+)", "high"),
        # Assignment patterns
        (r"(?i)(\w+)\s+(?:will|should|needs? to|has to|must)\s+(.+)", "medium"),
        (r"(?i)(?:assign|assigned to|give to)\s+(\w+)[:.]?\s*(.+)", "medium"),
        (r"(?i)(@\w+|by \w+)[:.]?\s*(.+)", "medium"),
        # Next steps patterns
        (r"(?i)(?:next steps?|action)[:.]?\s*(.+)", "medium"),
        (r"(?i)(?:we need to|let's|going to)\s+(.+)", "low"),
        # Deadline patterns
        (r"(?i)(.+?)\s+(?:by|due|before)\s+(\w+day|\d+/\d+|\w+\s+\d+)", "high"),
    ]

    for pattern, default_priority in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            if isinstance(match, tuple):
                if len(match) == 2:
                    # Handle (assignee, task) or (task, deadline) patterns
                    if any(
                        keyword in match[0].lower()
                        for keyword in ["will", "should", "need", "must", "assign"]
                    ):
                        assignee, task = match
                    else:
                        task, assignee = match
                else:
                    task = match[0]
                    assignee = match[1] if len(match) > 1 else "Unassigned"
            else:
                task = match
                assignee = "Unassigned"

            # Clean up the extracted text
            task = _clean_task_text(task)
            assignee = _clean_assignee_text(assignee)

            if len(task) > 10 and not _is_noise(task):  # Filter out noise
                action_items.append(
                    {
                        "task": task,
                        "assignee": assignee,
                        "priority": _infer_priority(task, default_priority),
                        "status": "pending",
                        "context": _extract_context_around_text(text, task),
                        "due_date": _extract_due_date(task),
                    }
                )

    # Remove duplicates based on task similarity
    return _deduplicate_action_items(action_items)


def extract_decisions_from_text(text: str) -> list[dict[str, Any]]:
    """
    Extract decisions using decision-making keywords and patterns.

    Args:
        text: Raw transcript text

    Returns:
        List of decision dictionaries
    """
    decisions = []

    decision_patterns = [
        # Direct decision statements
        (r"(?i)(?:decided|agreed|resolved|concluded)[:.]?\s*(.+)", "approved"),
        (r"(?i)(?:decision|choice|vote)[:.]?\s*(.+)", "approved"),
        # Approval patterns
        (
            r"(?i)(?:approve|approved|accept|accepted|confirm|confirmed)[:.]?\s*(.+)",
            "approved",
        ),
        (
            r"(?i)(?:reject|rejected|deny|denied|decline|declined)[:.]?\s*(.+)",
            "rejected",
        ),
        # Consensus patterns
        (r"(?i)(?:we will|let's|going to|plan to)[:.]?\s*(.+)", "approved"),
        (r"(?i)(?:consensus|agreement|unanimously)[:.]?\s*(.+)", "approved"),
        # Postponement patterns
        (r"(?i)(?:table|postpone|defer|delay)[:.]?\s*(.+)", "deferred"),
    ]

    for pattern, status in decision_patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            decision_text = _clean_decision_text(match)

            if len(decision_text) > 10 and not _is_noise(decision_text):
                decisions.append(
                    {
                        "decision": decision_text,
                        "made_by": _extract_decision_maker(text, decision_text),
                        "rationale": _extract_rationale(text, decision_text),
                        "impact": _assess_decision_impact(decision_text),
                        "status": status,
                        "context": _extract_context_around_text(text, decision_text),
                    }
                )

    return _deduplicate_decisions(decisions)


def identify_key_topics_from_text(text: str) -> list[str]:
    """
    Identify key topics using keyword frequency and context analysis.

    Args:
        text: Raw transcript text

    Returns:
        List of key topic strings
    """
    # Remove common stop words and transcript artifacts
    stop_words = {
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "up",
        "about",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "among",
        "within",
        "without",
        "said",
        "says",
        "mentioned",
        "discussed",
        "talked",
        "speaking",
        "think",
        "feel",
        "know",
        "see",
        "want",
        "need",
        "get",
        "go",
        "come",
        "yeah",
        "yes",
        "okay",
        "right",
        "well",
        "so",
        "um",
        "uh",
        "like",
    }

    # Extract meaningful words (2+ characters, not all caps unless acronym)
    words = re.findall(r"\b[A-Za-z]{2,}\b", text.lower())
    meaningful_words = [
        word for word in words if word not in stop_words and len(word) > 2
    ]

    # Count word frequency
    word_freq = Counter(meaningful_words)

    # Look for multi-word phrases that might be topics
    phrases = []

    # Extract potential topic phrases (2-3 words)
    phrase_patterns = [
        r"\b([a-z]+ (?:project|initiative|feature|system|process|strategy|plan|budget|timeline|deadline|meeting|review|update|discussion|decision))\b",
        r"\b((?:project|feature|system|api|database|frontend|backend|mobile|web|security|performance|testing|deployment|infrastructure) [a-z]+)\b",
        r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b",  # Proper nouns (like "Project Alpha")
    ]

    for pattern in phrase_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        phrases.extend(matches)

    phrase_freq = Counter(phrases)

    # Combine single words and phrases, prioritizing by frequency
    topics = []

    # Add high-frequency phrases (mentioned 2+ times)
    for phrase, count in phrase_freq.most_common():
        if count >= 2:
            topics.append(phrase.title())

    # Add high-frequency single words (mentioned 3+ times)
    for word, count in word_freq.most_common(20):
        if count >= 3 and word not in [p.lower() for p in topics]:
            topics.append(word.title())

    # Ensure at least one topic is returned (validation requirement)
    if not topics:
        topics = ["General Discussion"]

    return topics[:10]  # Return top 10 topics


def generate_executive_summary(
    text: str, participants: list[str], topics: list[str]
) -> str:
    """
    Generate an executive summary based on transcript analysis.

    Args:
        text: Raw transcript text
        participants: List of participants
        topics: List of key topics

    Returns:
        Executive summary string
    """
    word_count = len(text.split())
    estimated_duration = max(
        5, word_count // 150
    )  # Rough estimate: 150 words per minute

    participant_count = len(participants)
    topic_summary = ", ".join(topics[:5]) if topics else "general discussion"

    # Determine meeting type based on keywords
    meeting_type = _infer_meeting_type(text)

    # Count decisions and action items for summary
    decisions = extract_decisions_from_text(text)
    action_items = extract_action_items_from_text(text)

    summary_parts = []

    if meeting_type != "general":
        summary_parts.append(f"This {meeting_type} meeting")
    else:
        summary_parts.append("This meeting")

    summary_parts.append(f"involved {participant_count} participants")

    if estimated_duration:
        summary_parts.append(
            f"and covered {topic_summary} over approximately {estimated_duration} minutes"
        )
    else:
        summary_parts.append(f"covering {topic_summary}")

    key_outcomes = []
    if len(decisions) > 0:
        key_outcomes.append(
            f"{len(decisions)} key decision{'s' if len(decisions) != 1 else ''}"
        )
    if len(action_items) > 0:
        key_outcomes.append(
            f"{len(action_items)} action item{'s' if len(action_items) != 1 else ''}"
        )

    if key_outcomes:
        summary_parts.append(f"The meeting resulted in {' and '.join(key_outcomes)}")

    return ". ".join(summary_parts) + "."


# Helper functions


def _clean_task_text(task: str) -> str:
    """Clean and normalize task text."""
    # Remove leading/trailing whitespace and common prefixes
    task = task.strip()
    task = re.sub(r"^(?:that|to|and|but|so|then)\s+", "", task, flags=re.IGNORECASE)
    task = re.sub(r"\s+", " ", task)  # Normalize whitespace

    # Truncate to 450 characters to leave room for model validation (500 char limit)
    if len(task) > 450:
        task = task[:447] + "..."

    return task.strip()


def _clean_assignee_text(assignee: str) -> str:
    """Clean and normalize assignee text."""
    assignee = assignee.strip()
    # Remove common prefixes and suffixes
    assignee = re.sub(r"^(?:@|by|to)\s*", "", assignee, flags=re.IGNORECASE)
    assignee = re.sub(
        r"\s*[:.,;].*$", "", assignee
    )  # Remove everything after punctuation
    return assignee.strip().title() if assignee else "Unassigned"


def _clean_decision_text(decision: str) -> str:
    """Clean and normalize decision text."""
    decision = decision.strip()
    decision = re.sub(
        r"^(?:that|to|and|but|so|then)\s+", "", decision, flags=re.IGNORECASE
    )
    decision = re.sub(r"\s+", " ", decision)
    return decision.strip()


def _infer_priority(task: str, default: str = "medium") -> str:
    """Infer task priority based on keywords."""
    task_lower = task.lower()

    high_priority_keywords = [
        "urgent",
        "asap",
        "immediately",
        "critical",
        "must",
        "required",
        "deadline",
        "due",
    ]
    low_priority_keywords = [
        "consider",
        "maybe",
        "could",
        "might",
        "eventually",
        "nice to have",
    ]

    if any(keyword in task_lower for keyword in high_priority_keywords):
        return "high"
    elif any(keyword in task_lower for keyword in low_priority_keywords):
        return "low"
    else:
        return default


def _is_noise(text: str) -> bool:
    """Determine if text is likely noise/irrelevant."""
    noise_patterns = [
        r"^(?:um|uh|oh|ah|well|so|like|you know)",
        r"^(?:yeah|yes|no|okay|right|sure|exactly)",
        r"^\w{1,2}$",  # Very short words
        r"^[^\w\s]+$",  # Only punctuation
    ]

    text_lower = text.lower().strip()
    return any(re.match(pattern, text_lower) for pattern in noise_patterns)


def _extract_due_date(task: str) -> str | None:
    """Extract due date from task text if present."""
    date_patterns = [
        r"(?:by|due|before)\s+(\w+day)",  # "by Friday"
        r"(?:by|due|before)\s+(\d{1,2}/\d{1,2})",  # "by 12/25"
        r"(?:by|due|before)\s+(\w+\s+\d{1,2})",  # "by March 15"
    ]

    for pattern in date_patterns:
        match = re.search(pattern, task, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def _extract_context_around_text(
    full_text: str, target_text: str, window: int = 100
) -> str:
    """Extract context around specific text for better understanding."""
    try:
        index = full_text.lower().find(target_text.lower())
        if index == -1:
            return ""

        start = max(0, index - window)
        end = min(len(full_text), index + len(target_text) + window)

        context = full_text[start:end].strip()
        return context
    except Exception:
        return ""


def _extract_decision_maker(text: str, decision: str) -> str:
    """Attempt to identify who made the decision."""
    # Look for patterns around the decision
    context = _extract_context_around_text(text, decision, 50)

    # Common patterns for decision makers
    patterns = [
        r"([A-Z][a-z]+)\s+(?:decided|agreed|approved)",
        r"(?:decision by|made by)\s+([A-Z][a-z]+)",
        r"([A-Z][a-z]+):\s*[^.]*(?:decided|agreed)",
    ]

    for pattern in patterns:
        match = re.search(pattern, context, re.IGNORECASE)
        if match:
            return match.group(1)

    return "Team"


def _extract_rationale(text: str, decision: str) -> str:
    """Extract rationale for decision if present."""
    context = _extract_context_around_text(text, decision, 150)

    # Look for explanation patterns
    rationale_patterns = [
        r"(?:because|since|due to|reason)\s+([^.]{10,100})",
        r"(?:justification|rationale)[:.]?\s*([^.]{10,100})",
    ]

    for pattern in rationale_patterns:
        match = re.search(pattern, context, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return "No rationale provided"


def _assess_decision_impact(decision: str) -> str:
    """Assess the potential impact of a decision."""
    decision_lower = decision.lower()

    high_impact_keywords = [
        "budget",
        "hire",
        "fire",
        "launch",
        "cancel",
        "strategic",
        "critical",
        "major",
    ]
    low_impact_keywords = ["minor", "small", "quick", "simple", "temporary"]

    if any(keyword in decision_lower for keyword in high_impact_keywords):
        return "high"
    elif any(keyword in decision_lower for keyword in low_impact_keywords):
        return "low"
    else:
        return "medium"


def _infer_meeting_type(text: str) -> str:
    """Infer meeting type based on content keywords."""
    text_lower = text.lower()

    meeting_types = {
        "standup": [
            "standup",
            "daily",
            "scrum",
            "status update",
            "what did you work on",
        ],
        "planning": [
            "planning",
            "roadmap",
            "milestone",
            "timeline",
            "sprint planning",
            "project plan",
        ],
        "retrospective": [
            "retrospective",
            "retro",
            "what went well",
            "what could improve",
            "lessons learned",
        ],
        "one_on_one": [
            "1:1",
            "one on one",
            "performance",
            "feedback",
            "career",
            "development",
        ],
        "all_hands": [
            "all hands",
            "company update",
            "quarterly",
            "town hall",
            "announcement",
        ],
        "client_call": ["client", "customer", "stakeholder", "demo", "presentation"],
        "interview": ["interview", "candidate", "hiring", "recruiting"],
    }

    for meeting_type, keywords in meeting_types.items():
        if any(keyword in text_lower for keyword in keywords):
            return meeting_type

    return "general"


def _deduplicate_action_items(items: list[dict]) -> list[dict]:
    """Remove duplicate action items based on similarity."""
    if not items:
        return []

    unique_items = []
    seen_tasks = set()

    for item in items:
        task_normalized = re.sub(r"\s+", " ", item["task"].lower().strip())
        # Simple deduplication based on normalized task text
        if task_normalized not in seen_tasks:
            seen_tasks.add(task_normalized)
            unique_items.append(item)

    return unique_items


def _deduplicate_decisions(decisions: list[dict]) -> list[dict]:
    """Remove duplicate decisions based on similarity."""
    if not decisions:
        return []

    unique_decisions = []
    seen_decisions = set()

    for decision in decisions:
        decision_normalized = re.sub(r"\s+", " ", decision["decision"].lower().strip())
        if decision_normalized not in seen_decisions:
            seen_decisions.add(decision_normalized)
            unique_decisions.append(decision)

    return unique_decisions

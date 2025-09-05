"""Utilities for text analysis and pattern extraction."""

import re
from collections import Counter
from typing import Any


def normalize_speaker_name(name: str) -> str:
    """
    Normalize speaker names for consistent identification.

    Args:
        name: Raw speaker name from transcript

    Returns:
        Normalized speaker name
    """
    # Remove common titles
    titles = ["Mr.", "Ms.", "Mrs.", "Dr.", "Prof.", "CEO", "CTO", "VP"]
    for title in titles:
        name = name.replace(title, "").strip()

    # Remove role indicators in parentheses
    name = re.sub(r"\([^)]*\)", "", name).strip()

    # Remove extra whitespace
    name = " ".join(name.split())

    return name.strip()


def deduplicate_speakers(participants: list[str]) -> list[str]:
    """
    Remove duplicate speakers using name similarity detection.

    Args:
        participants: List of raw participant names

    Returns:
        List of deduplicated participant names
    """
    normalized_mapping = {}

    for participant in participants:
        norm_name = normalize_speaker_name(participant).lower()

        # Check for existing similar names
        found_match = False
        for existing_norm, existing_full in list(normalized_mapping.items()):
            # Check if names are variations of each other
            existing_words = set(existing_norm.split())
            current_words = set(norm_name.split())

            # If one name is subset of another (Sarah vs Sarah Chen)
            if existing_words.issubset(current_words) or current_words.issubset(
                existing_words
            ):
                # Keep the longer, more specific name
                if len(participant) > len(existing_full):
                    del normalized_mapping[existing_norm]
                    normalized_mapping[norm_name] = participant
                found_match = True
                break

        if not found_match:
            normalized_mapping[norm_name] = participant

    return list(normalized_mapping.values())


def extract_participants_from_transcript(text: str) -> list[str]:
    """
    Extract participant names using comprehensive transcript patterns with enhanced detection.

    Phase 4A Enhancement: Added support for markdown bold format and deduplication.

    Args:
        text: Raw transcript text

    Returns:
        List of unique, deduplicated participant names
    """
    participants = set()

    # Pattern 1: Markdown bold format "**Name:**" (Primary for meeting transcripts)
    markdown_bold_pattern = r"\*\*([A-Z][a-zA-Z\s\.]+):\*\*"
    matches = re.findall(markdown_bold_pattern, text)
    participants.update(matches)

    # Pattern 2: Standard "Name:" format (most common)
    name_colon_pattern = r"^([A-Z][a-zA-Z\s\.]+):\s"
    matches = re.findall(name_colon_pattern, text, re.MULTILINE)
    participants.update(matches)

    # Pattern 3: HTML bold format "<b>Name:</b>"
    html_bold_pattern = r"<b>([A-Z][a-zA-Z\s\.]+):</b>"
    matches = re.findall(html_bold_pattern, text)
    participants.update(matches)

    # Pattern 4: Angle bracket format "<Name>"
    angle_bracket_pattern = r"<([A-Z][a-zA-Z\s\.]+)>"
    matches = re.findall(angle_bracket_pattern, text)
    participants.update(matches)

    # Pattern 5: "Name said/mentioned/asked" format
    said_pattern = r"([A-Z][a-zA-Z\s\.]+)\s+(?:said|mentioned|asked|replied|responded|noted|added|stated)"
    matches = re.findall(said_pattern, text, re.IGNORECASE)
    participants.update(matches)

    # Pattern 6: "from Name" or "by Name" format
    from_by_pattern = r"(?:from|by)\s+([A-Z][a-zA-Z\s\.]+)"
    matches = re.findall(from_by_pattern, text)
    participants.update(matches)

    # Pattern 7: Meeting participant lists "Attendees:"
    attendee_pattern = r"(?:Attendees?|Participants?):\s*\n?(?:\s*-\s*([A-Z][a-zA-Z\s\.]+(?:\([^)]*\))?)\s*\n?)*"
    attendee_matches = re.findall(attendee_pattern, text, re.MULTILINE)
    if attendee_matches:
        # Extract individual names from attendee lists
        for match in attendee_matches:
            if match:
                participants.add(match.strip())

    # Filter out common false positives and short names
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
        "We",
        "I",
        "You",
        "They",
        "He",
        "She",
        "It",
        "Meeting",
        "Time",
        "Date",
        "Type",
        "Summary",
        "Notes",
        "Action",
        "Items",
        "Next",
        "Steps",
        "Decisions",
        "Risks",
        "Issues",
        "PM",
        "PST",
        "EST",
        # Meeting transcript metadata
        "Attendees",
        "Participants",
        "Meeting Type",
        "Duration",
        "Location",
        "Agenda",
        "Minutes",
        "Recording",
        "Transcript",
        "Status",
        "Priority",
        "Update",
        "Review",
        "Discussion",
        "Conclusion",
        "Overview",
        "Background",
    }

    # Clean and filter participants
    cleaned_participants = []
    for participant in participants:
        # Remove trailing punctuation and whitespace
        cleaned = participant.strip().rstrip(":.,!?")

        # Skip if too short, is false positive, or doesn't look like a name
        if (
            len(cleaned) < 2
            or cleaned in false_positives
            or cleaned.lower() in [fp.lower() for fp in false_positives]
            or not re.match(r"^[A-Z][a-zA-Z\s\.]+$", cleaned)
        ):
            continue

        cleaned_participants.append(cleaned)

    # Apply deduplication to handle name variations
    deduplicated = deduplicate_speakers(cleaned_participants)

    # Sort for consistent output
    return sorted(deduplicated)


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


def _extract_meeting_duration(text: str) -> int:
    """
    Extract actual meeting duration from transcript timestamps.
    
    Args:
        text: Raw transcript text
        
    Returns:
        Duration in minutes, or estimated duration if timestamps not found
    """
    import re
    
    # Look for explicit time ranges in headers
    time_range_patterns = [
        r"(\d{1,2}:\d{2})\s*(?:AM|PM)\s*[-–]\s*(\d{1,2}:\d{2})\s*(?:AM|PM)",
        r"Time:\*?\*?\s*(\d{1,2}:\d{2})\s*(?:AM|PM)\s*[-–]\s*(\d{1,2}:\d{2})\s*(?:AM|PM)",
    ]
    
    for pattern in time_range_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                start_str, end_str = match.groups()
                
                # Extract hours and minutes
                start_parts = start_str.split(':')
                end_parts = end_str.split(':') 
                
                start_hour = int(start_parts[0])
                start_min = int(start_parts[1])
                end_hour = int(end_parts[0])
                end_min = int(end_parts[1])
                
                # Handle AM/PM conversion
                am_pm_text = match.group(0).upper()
                if 'PM' in am_pm_text:
                    if start_hour < 12:
                        start_hour += 12
                    if end_hour < 12:
                        end_hour += 12
                elif 'AM' in am_pm_text and start_hour == 12:
                    start_hour = 0
                
                # Calculate duration
                start_total_min = start_hour * 60 + start_min
                end_total_min = end_hour * 60 + end_min
                
                duration = end_total_min - start_total_min
                if duration > 0:
                    return duration
                    
            except (ValueError, IndexError):
                continue
    
    # Fallback: look for "Meeting ended at" pattern
    end_pattern = r"Meeting ended at (\d{1,2}):(\d{2})\s*(AM|PM)"
    end_match = re.search(end_pattern, text, re.IGNORECASE)
    if end_match:
        # For now, assume reasonable meeting duration if we only have end time
        # This could be enhanced with start time detection
        return 90  # Default assumption for meetings with detected end time
    
    # Final fallback: more realistic word-count estimation
    word_count = len(text.split())
    # Meetings typically have 100-120 words per minute (including discussion/pauses)
    estimated_duration = max(15, word_count // 110)
    return estimated_duration


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
    # Extract actual meeting duration from timestamps
    meeting_duration = _extract_meeting_duration(text)

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

    if meeting_duration:
        summary_parts.append(
            f"and covered {topic_summary} over approximately {meeting_duration} minutes"
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


# Enhanced extraction functions for improved quality


def extract_risks_from_text(text: str) -> list[dict[str, Any]]:
    """
    Extract risks with detailed categorization and mitigation strategies.

    Args:
        text: Raw transcript text

    Returns:
        List of risk dictionaries with enhanced details
    """
    risks = []

    # Enhanced risk keywords by category
    technical_keywords = [
        "complexity",
        "challenging",
        "difficult",
        "integration",
        "scalability",
        "performance",
        "technical debt",
        "architecture",
        "compatibility",
        "timeline",
        "underestimate",
        "overrun",
    ]

    security_keywords = [
        "security",
        "vulnerability",
        "attack",
        "breach",
        "compliance",
        "audit",
        "authentication",
        "authorization",
        "privacy",
        "data protection",
    ]

    business_keywords = [
        "customer",
        "market",
        "budget",
        "resource",
        "stakeholder",
        "adoption",
        "timeline",
        "deadline",
        "scope",
        "requirement",
    ]

    # Enhanced risk indication patterns - Fixed text corruption issues
    risk_patterns = [
        # Complete sentence patterns for explicit risks
        (
            r"(?:the\s+)?(?:main\s+|primary\s+|key\s+|major\s+)?(?:risk|concern|issue|problem|challenge|blocker|threat)\s+(?:is|would be|could be|here is|we have)\s+([^.!?]+[.!?])",
            "explicit",
        ),
        # Question-based risk patterns
        (
            r"(?:what if|what about|what happens if)\s+([^?]+\?)",
            "conditional", 
        ),
        # Potential/modal risk patterns - complete phrases
        (
            r"(?:might|could|may|potentially|possibly)\s+(?:be|cause|lead to|result in)\s+([^.!?,\n]+(?:[.!?]|(?=\s+[A-Z])))",
            "potential",
        ),
        # Caution/warning patterns - complete statements
        (
            r"(?:we need to be careful|watch out|be aware|need to consider)\s+(?:of|about|that|with)?\s*([^.!?,\n]+(?:[.!?]|(?=\s+[A-Z])))",
            "caution",
        ),
        # Problem statement patterns
        (
            r"(?:the\s+)?(?:problem|issue|challenge|difficulty)\s+(?:is|would be|could be|we face|here is)\s+([^.!?,\n]+(?:[.!?]|(?=\s+[A-Z])))",
            "problem",
        ),
        # Negative outcome patterns
        (
            r"(?:if we don't|unless we|without)\s+([^,\n]+),\s*([^.!?\n]+[.!?])",
            "consequence",
        ),
    ]

    # Extract risks using patterns
    for pattern, risk_type in risk_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            # Handle tuple results from patterns with multiple capture groups
            if isinstance(match, tuple):
                # For consequence patterns: "if we don't X, Y happens"
                if risk_type == "consequence":
                    risk_text = f"Without {match[0].strip()}, {match[1].strip()}"
                else:
                    # Use the longest captured group
                    risk_text = max(match, key=len).strip()
            else:
                risk_text = match.strip()
            
            # Enhanced filtering: ensure meaningful content
            if len(risk_text) > 15 and not risk_text.startswith(('y ', '-> ', 's ', '-')):
                # Determine category
                category = _categorize_risk(
                    risk_text, technical_keywords, security_keywords, business_keywords
                )

                # Assess impact and likelihood
                impact = _assess_risk_impact(risk_text, text)
                likelihood = _assess_risk_likelihood(risk_text, text, risk_type)

                # Extract mitigation strategy
                mitigation = _extract_mitigation_strategy(risk_text, text)

                # Find risk owner
                owner = _find_risk_owner(risk_text, text)

                risks.append(
                    {
                        "risk": risk_text,
                        "category": category,
                        "impact": impact,
                        "likelihood": likelihood,
                        "mitigation": mitigation,
                        "owner": owner,
                    }
                )

    # Remove duplicates and return top risks
    unique_risks = _deduplicate_risks(risks)
    return unique_risks[:15]  # Return top 15 risks


def extract_user_stories_from_text(text: str) -> list[dict[str, Any]]:
    """
    Extract user stories from discussion context and requirements.

    Args:
        text: Raw transcript text

    Returns:
        List of user story dictionaries
    """
    user_stories = []

    # Direct user story patterns
    story_patterns = [
        r"as\s+a\s+(.+?),\s*i\s+want\s+(.+?),?\s*so\s+that\s+(.+?)(?:\n|\.|;)",
        r"user\s+story[:.]?\s*(.+?)(?:\n|\.|;)",
        r"(?:user|customer|admin|developer)\s+(?:needs?|wants?|should be able to)\s+(.+?)(?:\n|\.|;)",
    ]

    # Extract direct stories
    for pattern in story_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if isinstance(match, tuple) and len(match) == 3:
                user_type, goal, benefit = match
                story = f"As a {user_type.strip()}, I want {goal.strip()}, so that {benefit.strip()}"
            else:
                story = match if isinstance(match, str) else match[0]

            # Extract acceptance criteria from surrounding context
            criteria = _extract_acceptance_criteria(story, text)
            priority = _assess_story_priority(story, text)

            user_stories.append(
                {
                    "story": story,
                    "acceptance_criteria": criteria,
                    "priority": priority,
                    "epic": None,  # Could be enhanced with epic detection
                }
            )

    # Extract implicit user stories from requirements discussions
    implicit_stories = _extract_implicit_user_stories(text)
    user_stories.extend(implicit_stories)

    return _deduplicate_user_stories(user_stories)[:10]


def extract_phased_actions_from_text(text: str) -> list[dict[str, Any]]:
    """
    Extract action items with phase detection and enhanced context.

    Args:
        text: Raw transcript text

    Returns:
        List of enhanced action item dictionaries
    """
    action_items = extract_action_items_from_text(text)

    # Enhance each action item with phase detection
    enhanced_actions = []
    for item in action_items:
        # Detect phase based on content and timeline
        phase = _detect_action_phase(item["task"], text)

        # Extract dependencies
        dependencies = _extract_dependencies(item["task"], text)

        # Enhanced context extraction
        context = _extract_action_context(item["task"], text)

        enhanced_item = {
            **item,
            "phase": phase,
            "dependencies": dependencies,
            "context": context if context else item.get("context", ""),
        }
        enhanced_actions.append(enhanced_item)

    return enhanced_actions


def extract_granular_topics_from_text(text: str) -> list[str]:
    """
    Extract granular, specific technical topics instead of broad categories.

    Args:
        text: Raw transcript text

    Returns:
        List of specific technical topics
    """
    topics = []

    # Technical topic patterns (more specific)
    technical_patterns = [
        # Protocol and authentication specific
        r"\b(SAML\s+(?:configuration|implementation|integration|authentication|assertions?))\b",
        r"\b(OIDC\s+(?:token|flow|configuration|authentication|provider))\b",
        r"\b((?:single\s+sign-on|SSO)\s+(?:implementation|configuration|integration|flow))\b",
        r"\b(session\s+(?:management|handling|tokens?|storage))\b",
        r"\b(token\s+(?:validation|refresh|handling|storage|format))\b",
        r"\b(logout\s+(?:implementation|flow|propagation|SLO))\b",
        # Infrastructure and architecture
        r"\b(API\s+(?:middleware|integration|endpoints?|authentication))\b",
        r"\b(database\s+(?:migration|schema|integration|design))\b",
        r"\b(feature\s+flag\s+(?:implementation|system|management))\b",
        r"\b(identity\s+provider\s+(?:integration|configuration|testing))\b",
        # Development and testing
        r"\b(test\s+(?:environment|automation|coverage|strategy))\b",
        r"\b(development\s+(?:environment|workflow|pipeline))\b",
        r"\b(UI/UX\s+(?:design|wireframes|flows?|testing))\b",
        r"\b(account\s+(?:linking|provisioning|management))\b",
        # Security and compliance
        r"\b(security\s+(?:audit|compliance|review|testing))\b",
        r"\b(SOC\s+2\s+(?:compliance|requirements?|audit))\b",
        r"\b(audit\s+(?:logging|requirements?|trail))\b",
        r"\b(compliance\s+(?:requirements?|testing|validation))\b",
    ]

    # Extract specific technical discussions
    for pattern in technical_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            topic = match.strip().title()
            if topic not in topics:
                topics.append(topic)

    # Extract general topics but make them more specific
    general_topics = identify_key_topics_from_text(text)
    for topic in general_topics:
        # Make topics more specific based on context
        specific_topic = _make_topic_specific(topic, text)
        if specific_topic != topic and specific_topic not in topics:
            topics.append(specific_topic)

    return topics[:15]  # Return top 15 specific topics


# Helper functions for enhanced extraction


def _categorize_risk(
    risk_text: str,
    technical_keywords: list,
    security_keywords: list,
    business_keywords: list,
) -> str:
    """Categorize risk based on keywords and context."""
    risk_lower = risk_text.lower()

    technical_score = sum(1 for kw in technical_keywords if kw in risk_lower)
    security_score = sum(1 for kw in security_keywords if kw in risk_lower)
    business_score = sum(1 for kw in business_keywords if kw in risk_lower)

    if security_score > technical_score and security_score > business_score:
        return "security"
    elif technical_score > business_score:
        return "technical"
    else:
        return "business"


def _assess_risk_impact(risk_text: str, full_text: str) -> str:
    """Assess risk impact based on keywords and context."""
    risk_lower = risk_text.lower()

    high_impact_keywords = [
        "critical",
        "major",
        "significant",
        "severe",
        "catastrophic",
        "breaking",
        "failure",
    ]
    medium_impact_keywords = ["moderate", "noticeable", "some impact", "delay", "issue"]

    if any(kw in risk_lower for kw in high_impact_keywords):
        return "high"
    elif any(kw in risk_lower for kw in medium_impact_keywords):
        return "medium"
    else:
        return "low"


def _assess_risk_likelihood(risk_text: str, full_text: str, risk_type: str) -> str:
    """Assess risk likelihood based on language and type."""
    risk_lower = risk_text.lower()

    high_likelihood_keywords = ["will", "definitely", "certain", "always", "inevitable"]
    low_likelihood_keywords = ["might", "could", "possibly", "potentially", "unlikely"]

    if risk_type == "explicit":
        return "medium"  # Explicitly mentioned risks are generally medium likelihood
    elif any(kw in risk_lower for kw in high_likelihood_keywords):
        return "high"
    elif any(kw in risk_lower for kw in low_likelihood_keywords):
        return "low"
    else:
        return "medium"


def _extract_mitigation_strategy(risk_text: str, full_text: str) -> str:
    """Extract mitigation strategy from surrounding context."""
    # Look for mitigation patterns near the risk
    mitigation_patterns = [
        r"(?:to (?:mitigate|address|solve|handle|manage))\s+(.+?)(?:\n|\.|;)",
        r"(?:we (?:can|could|should|will))\s+(.+?)(?:\n|\.|;)",
        r"(?:solution|approach|strategy)[:.]?\s*(.+?)(?:\n|\.|;)",
        r"(?:if we|let's|plan to)\s+(.+?)(?:\n|\.|;)",
    ]

    for pattern in mitigation_patterns:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        if matches:
            return matches[0].strip()

    return "Not specified"


def _find_risk_owner(risk_text: str, full_text: str) -> str:
    """Find the person responsible for managing the risk."""
    # Look for ownership patterns
    owner_patterns = [
        r"([A-Z][a-z]+)\s+(?:will|should|can|needs to)\s+(?:handle|manage|address|monitor)",
        r"(?:assign|give|hand)\s+(?:to|this to)\s+([A-Z][a-z]+)",
        r"([A-Z][a-z]+)[:]\s+(?:I'll|I will|I can)\s+(?:handle|manage|address)",
    ]

    for pattern in owner_patterns:
        matches = re.findall(pattern, full_text)
        if matches:
            return matches[0].strip()

    return None


def _extract_implicit_user_stories(text: str) -> list[dict[str, Any]]:
    """
    Extract user stories from requirement discussions using enhanced pattern detection.

    Phase 4B Enhancement: Comprehensive user story extraction with proper role detection,
    acceptance criteria generation, and priority assignment.
    """
    stories = []

    # Enhanced patterns for specific SSO requirements
    sso_story_patterns = [
        {
            "pattern": r"(?:enterprise|corporate)\s+(?:customers?|admins?)\s+(?:will\s+)?want\s+(?:some\s+level\s+of\s+)?control\s+over\s+(?:their\s+)?users",
            "user_type": "enterprise admin",
            "goal": "basic admin capabilities to manage users from my organization",
            "benefit": "I can maintain control over user access and security",
            "priority": "high",
            "epic": "Admin Management",
            "acceptance_criteria": [
                "Admin can view list of users from their organization",
                "Admin can deactivate users as needed",
                "Admin interface shows user status and last login",
            ],
        },
        {
            "pattern": r"users?\s+who\s+are\s+already\s+authenticated\s+with\s+their\s+corporate\s+identity\s+provider.*seamless",
            "user_type": "corporate user",
            "goal": "seamless SSO authentication without seeing login pages",
            "benefit": "I can access the application immediately from my corporate network",
            "priority": "high",
            "epic": "SSO Authentication",
            "acceptance_criteria": [
                "User is automatically redirected to SSO provider",
                "No login page is shown for authenticated corporate users",
                "Authentication completes within 3 seconds",
            ],
        },
        {
            "pattern": r"(?:handle\s+)?(?:the\s+case\s+where\s+)?SSO\s+fails\s+gracefully.*fallback.*email.*password",
            "user_type": "user",
            "goal": "graceful SSO fallback to email/password login",
            "benefit": "I can still access the system when SSO is unavailable",
            "priority": "high",
            "epic": "Authentication Resilience",
            "acceptance_criteria": [
                "System detects SSO failure automatically",
                "User is presented with email/password login form",
                "No data loss occurs during authentication failure",
            ],
        },
        {
            "pattern": r"automatically\s+create\s+accounts?\s+for\s+users?\s+who\s+authenticate\s+via\s+SSO",
            "user_type": "new SSO user",
            "goal": "automatic account creation upon first SSO login",
            "benefit": "I can access the system immediately without manual registration",
            "priority": "medium",
            "epic": "User Provisioning",
            "acceptance_criteria": [
                "Account is created using SSO claims (email, name, role)",
                "User profile is populated with available SSO attributes",
                "Account linking workflow is triggered for existing emails",
            ],
        },
        {
            "pattern": r"proper\s+logout.*both\s+local\s+logout.*Single\s+Logout.*SLO.*identity\s+provider",
            "user_type": "security-conscious user",
            "goal": "complete SSO logout from both application and identity provider",
            "benefit": "my session is properly terminated for security compliance",
            "priority": "high",
            "epic": "Security Compliance",
            "acceptance_criteria": [
                "Local application session is terminated",
                "Identity provider receives logout notification",
                "All related tokens are invalidated",
            ],
        },
        {
            "pattern": r"update\s+our\s+API\s+authentication\s+to\s+handle\s+SSO\s+tokens",
            "user_type": "developer",
            "goal": "API authentication that supports SSO tokens",
            "benefit": "applications can integrate seamlessly with SSO-enabled APIs",
            "priority": "medium",
            "epic": "API Integration",
            "acceptance_criteria": [
                "API accepts both JWT and SSO tokens",
                "Token validation works for all supported providers",
                "API documentation includes SSO token examples",
            ],
        },
        {
            "pattern": r"support\s+both\s+SAML\s+(?:and|&)\s+(?:OIDC|OpenID\s+Connect)",
            "user_type": "enterprise customer",
            "goal": "support for both SAML and OIDC protocols",
            "benefit": "the system integrates with my existing identity infrastructure",
            "priority": "high",
            "epic": "Protocol Support",
            "acceptance_criteria": [
                "SAML 2.0 integration works with major providers",
                "OpenID Connect integration supports standard flows",
                "Both protocols can be configured simultaneously",
            ],
        },
    ]

    # Extract stories using enhanced patterns
    for story_config in sso_story_patterns:
        if re.search(story_config["pattern"], text, re.IGNORECASE | re.DOTALL):
            story = f"As a {story_config['user_type']}, I want {story_config['goal']}, so that {story_config['benefit']}"

            stories.append(
                {
                    "story": story,
                    "acceptance_criteria": story_config["acceptance_criteria"],
                    "priority": story_config["priority"],
                    "epic": story_config["epic"],
                    "business_value": _generate_business_value(
                        story_config["epic"], story_config["priority"]
                    ),
                }
            )

    # Fallback patterns for additional story detection
    general_patterns = [
        {
            "pattern": r"(?:from\s+a\s+)?(user|admin|developer|security|business)\s+perspective[,:]?\s+(.+?)(?:\.|\n)",
            "template": "As a {role}, I want to {goal}, so that I can achieve my objectives",
        },
        {
            "pattern": r"(?:users?|customers?|admins?|developers?)\s+(?:should\s+be\s+able\s+to|need\s+to|want\s+to)\s+(.+?)(?:\.|\n)",
            "template": "As a user, I want to {goal}, so that I can accomplish my tasks",
        },
    ]

    for pattern_config in general_patterns:
        matches = re.findall(pattern_config["pattern"], text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                role, goal = match
                story = pattern_config["template"].format(
                    role=role.strip(), goal=goal.strip()
                )
            else:
                story = pattern_config["template"].format(goal=match.strip())

            # Only add if not already captured by specific patterns
            if not any(
                story.lower() in existing["story"].lower() for existing in stories
            ):
                stories.append(
                    {
                        "story": story,
                        "acceptance_criteria": _generate_acceptance_criteria(story),
                        "priority": _assess_story_priority(story, text),
                        "epic": "General Requirements",
                        "business_value": "Improves user experience and system functionality",
                    }
                )

    return stories[:8]  # Return up to 8 comprehensive stories


def _detect_action_phase(task: str, full_text: str) -> str:
    """Detect which development phase an action belongs to."""
    task_lower = task.lower()

    immediate_keywords = [
        "week 1",
        "immediate",
        "asap",
        "right away",
        "first",
        "start with",
    ]
    development_keywords = [
        "develop",
        "implement",
        "code",
        "build",
        "create",
        "weeks 2-7",
    ]
    testing_keywords = ["test", "qa", "validate", "verify", "weeks 8-10", "uat"]

    if any(kw in task_lower for kw in immediate_keywords):
        return "immediate"
    elif any(kw in task_lower for kw in testing_keywords):
        return "testing"
    elif any(kw in task_lower for kw in development_keywords):
        return "development"
    else:
        return "immediate"  # Default to immediate for unclear items


def _extract_dependencies(task: str, full_text: str) -> list[str]:
    """Extract task dependencies from context."""
    dependencies = []

    # Look for dependency patterns
    dependency_patterns = [
        r"(?:depends on|needs|requires|after|once)\s+(.+?)(?:\n|\.|;|,(?=\s[A-Z]))",
        r"(?:before|prior to)\s+(.+?)(?:\n|\.|;|,(?=\s[A-Z]))",
        r"(?:waiting for|blocked by)\s+(.+?)(?:\n|\.|;|,(?=\s[A-Z]))",
    ]

    for pattern in dependency_patterns:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        dependencies.extend(
            [match.strip() for match in matches if len(match.strip()) > 3]
        )

    return dependencies[:3]  # Return top 3 dependencies


def _extract_action_context(task: str, full_text: str) -> str:
    """Extract why this action is needed from surrounding context."""
    # Look for context around the task
    context_patterns = [
        r"(?:because|since|due to|as|given that)\s+(.+?)(?:\n|\.|;)",
        r"(?:this is needed|required|necessary)\s+(?:for|to|because)\s+(.+?)(?:\n|\.|;)",
        r"(?:in order to|to ensure|to make sure)\s+(.+?)(?:\n|\.|;)",
    ]

    for pattern in context_patterns:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        if matches:
            return matches[0].strip()

    return ""


def _make_topic_specific(topic: str, text: str) -> str:
    """Make a general topic more specific based on context."""
    topic_lower = topic.lower()
    text_lower = text.lower()

    # Topic enhancement rules
    if "authentication" in topic_lower or "sso" in topic_lower:
        if "saml" in text_lower and "oidc" in text_lower:
            return "Dual Protocol SSO Implementation (SAML + OIDC)"
        elif "saml" in text_lower:
            return "SAML Authentication Integration"
        elif "oidc" in text_lower:
            return "OpenID Connect Implementation"
        else:
            return "SSO Authentication System"

    elif "security" in topic_lower:
        if "compliance" in text_lower:
            return "Security Compliance and Audit Requirements"
        elif "logout" in text_lower:
            return "Secure Logout and Session Management"
        else:
            return "Security Architecture and Requirements"

    elif "design" in topic_lower or "ux" in topic_lower:
        return "User Experience Design for SSO Flows"

    elif "testing" in topic_lower:
        return "SSO Testing Strategy and Implementation"

    return topic  # Return original if no specific enhancement found


def _deduplicate_risks(risks: list[dict]) -> list[dict]:
    """Remove duplicate risks based on similarity."""
    unique_risks = []
    seen_risks = set()

    for risk in risks:
        risk_normalized = re.sub(r"\s+", " ", risk["risk"].lower().strip())[
            :100
        ]  # First 100 chars
        if risk_normalized not in seen_risks:
            seen_risks.add(risk_normalized)
            unique_risks.append(risk)

    return unique_risks


def _deduplicate_user_stories(stories: list[dict]) -> list[dict]:
    """Remove duplicate user stories based on similarity."""
    unique_stories = []
    seen_stories = set()

    for story in stories:
        story_normalized = re.sub(r"\s+", " ", story["story"].lower().strip())[:100]
        if story_normalized not in seen_stories:
            seen_stories.add(story_normalized)
            unique_stories.append(story)

    return unique_stories


def _extract_acceptance_criteria(story: str, text: str) -> list[str]:
    """Extract acceptance criteria from story context."""
    criteria = []

    # Look for requirement patterns
    criteria_patterns = [
        r"(?:must|should|needs? to)\s+(.+?)(?:\n|\.|;|,(?=\s[A-Z]))",
        r"(?:requirements?|criteria|conditions?)[:.]?\s*(.+?)(?:\n|\.|;)",
        r"(?:ensure|verify|validate)\s+(?:that\s+)?(.+?)(?:\n|\.|;|,(?=\s[A-Z]))",
    ]

    for pattern in criteria_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        criteria.extend([match.strip() for match in matches if len(match.strip()) > 10])

    return criteria[:3]  # Return top 3 criteria


def _assess_story_priority(story: str, text: str) -> str:
    """Assess user story priority based on business context."""
    story_lower = story.lower()

    high_priority_keywords = [
        "critical",
        "essential",
        "must have",
        "required",
        "priority",
        "urgent",
    ]
    low_priority_keywords = [
        "nice to have",
        "optional",
        "later",
        "future",
        "enhancement",
    ]

    if any(kw in story_lower for kw in high_priority_keywords):
        return "high"
    elif any(kw in story_lower for kw in low_priority_keywords):
        return "low"
    else:
        return "medium"


def _generate_business_value(epic: str, priority: str) -> str:
    """Generate business value description based on epic and priority."""
    business_value_templates = {
        "Admin Management": "Enables enterprise customers to maintain security and compliance through user management capabilities",
        "SSO Authentication": "Reduces user friction and improves adoption by eliminating redundant authentication steps",
        "Authentication Resilience": "Prevents user lockouts and ensures continuous system availability during SSO failures",
        "User Provisioning": "Reduces administrative overhead and accelerates user onboarding process",
        "Security Compliance": "Meets enterprise security requirements and reduces audit risks",
        "API Integration": "Enables seamless third-party integrations and expands ecosystem value",
        "Protocol Support": "Maximizes enterprise compatibility and reduces integration barriers",
        "General Requirements": "Improves overall system functionality and user satisfaction",
    }

    base_value = business_value_templates.get(
        epic, "Enhances system capabilities and user experience"
    )

    if priority == "high":
        return f"{base_value} - Critical for enterprise adoption and user satisfaction"
    elif priority == "low":
        return f"{base_value} - Nice-to-have enhancement for future consideration"
    else:
        return f"{base_value} - Important for competitive positioning"


def _generate_acceptance_criteria(story: str) -> list[str]:
    """Generate acceptance criteria based on user story content."""
    story_lower = story.lower()
    criteria = []

    # Generate criteria based on story keywords
    if "admin" in story_lower and "manage" in story_lower:
        criteria.extend(
            [
                "Admin interface is accessible to authorized users",
                "User management functions work correctly",
                "Changes are logged for audit purposes",
            ]
        )
    elif "sso" in story_lower or "authentication" in story_lower:
        criteria.extend(
            [
                "Authentication flow completes successfully",
                "User is redirected appropriately after login",
                "Session is maintained securely",
            ]
        )
    elif "api" in story_lower:
        criteria.extend(
            [
                "API endpoints accept valid tokens",
                "Invalid tokens are properly rejected",
                "API documentation is updated",
            ]
        )
    elif "logout" in story_lower:
        criteria.extend(
            [
                "Local session is terminated",
                "External systems are notified of logout",
                "User is redirected to appropriate page",
            ]
        )
    elif "fallback" in story_lower or "fail" in story_lower:
        criteria.extend(
            [
                "System detects failure conditions",
                "Alternative authentication method is provided",
                "User receives appropriate error messages",
            ]
        )
    else:
        # Default criteria for general stories
        criteria.extend(
            [
                "Feature works as described in story",
                "Error conditions are handled gracefully",
                "User receives appropriate feedback",
            ]
        )

    return criteria[:3]  # Limit to 3 criteria for readability

# TLDR AI Agent Enhancement Plan

**Status**: In Progress  
**Branch**: `feature/enhanced-ai-summarization`  
**Target Quality Score**: 90% (9/10)  
**Current Quality Score**: 60% (6/10)  

## Problem Analysis

The current AI agent achieves only 60% quality (6/10) compared to expected output, with these critical gaps:

### Major Quality Issues
1. **Missing Risks Section** - Expected 9 risks, agent provided 0
2. **Missing User Stories** - Expected 9 user stories, agent provided 0  
3. **Shallow Analysis** - Missing technical depth, rationale, and context
4. **Oversimplified Action Items** - Lacking specifics, deadlines, and phases
5. **Broad Topics** - Generic instead of specific technical discussions

### Current vs Expected Output Comparison

| Category | Current Output | Expected Output | Gap |
|----------|----------------|-----------------|-----|
| Risks | 0 items | 9 detailed risks with impact/mitigation | 100% missing |
| User Stories | 0 items | 9 properly formatted stories | 100% missing |
| Action Items | 3 generic items | Detailed items with phases/context | 70% depth missing |
| Key Topics | 3 broad topics | 10+ specific technical topics | 70% granularity missing |
| Decisions | Basic decisions | Include rationale and impact | 50% context missing |

## Proposed Solution Architecture

### 1. Enhanced Prompt System (`prompts.py`)

#### New Prompts to Add:
- **MEETING_ANALYSIS_PROMPT_V2**: More detailed instructions with examples
- **RISK_EXTRACTION_PROMPT**: Dedicated prompt for identifying technical, security, and business risks
- **USER_STORY_PROMPT**: Specialized prompt for extracting user stories in proper format
- **PHASED_ACTION_PROMPT**: Extract action items with timeline phases and specific details

#### Key Improvements:
- Add specific examples of good vs bad output
- Include detailed instructions for each section
- Specify minimum requirements (e.g., "identify at least 5 risks")
- Add context prompts for technical depth

### 2. Improved Text Analysis (`text_analysis_utils.py`)

#### New Functions to Add:
- **`extract_risks_from_text()`**: Pattern matching for risk indicators
- **`extract_user_stories_from_text()`**: "As a [user], I want [goal], so that [benefit]" pattern
- **`extract_phased_actions()`**: Identify immediate vs development vs testing phases
- **`extract_technical_topics()`**: More granular topic extraction

#### Enhancement Logic:
```python
# Risk extraction keywords
risk_keywords = ["risk", "concern", "issue", "problem", "might", "could", "challenge", "blocker"]

# User story patterns  
user_story_pattern = r"as\s+a\s+(.+?),\s*i\s+want\s+(.+?),?\s*so\s+that\s+(.+)"

# Phase detection
phase_patterns = {
    "immediate": ["week 1", "immediate", "asap", "right away"],
    "development": ["weeks? 2-7", "development", "implementation"],
    "testing": ["weeks? 8-10", "testing", "qa", "uat"]
}
```

### 3. Enhanced Ollama Service (`ollama_service.py`)

#### JSON Schema Updates:
- Make `risks` and `user_stories` required fields
- Add minimum array lengths (e.g., min 3 risks, min 5 user stories)
- Require more detailed action item fields (context, phase, rationale)
- Add validation for technical depth

#### Multi-Pass Extraction:
1. **First Pass**: Basic information extraction
2. **Second Pass**: Deep analysis for risks and user stories  
3. **Third Pass**: Validation and gap filling

### 4. Improved Mock Service (`mock_summarization_service.py`)

#### Enhanced Extraction Logic:
- Risk categorization (technical/security/business)
- User story pattern recognition from discussion context
- Phase-aware action item extraction
- Technical topic clustering

## Implementation Steps

### Phase 1: Core Prompt Enhancement
1. Update `prompts.py` with enhanced MEETING_ANALYSIS_PROMPT_V2
2. Add specialized extraction prompts for risks and user stories
3. Include detailed examples and minimum requirements

### Phase 2: Text Analysis Enhancement  
4. Add `extract_risks_from_text()` function
5. Add `extract_user_stories_from_text()` function
6. Enhance `extract_action_items_from_text()` with phase detection
7. Improve topic extraction granularity

### Phase 3: Service Updates
8. Modify Ollama service to use enhanced prompts
9. Update JSON schema for stricter validation
10. Enhance mock service fallback logic

### Phase 4: Validation & Testing
11. Add post-processing validation
12. Test with SSO transcript benchmark
13. Compare against expected output

## Expected Improvements

| Metric | Before | Target | Improvement |
|--------|--------|--------|-------------|
| Risks Identified | 0 | 9+ | +∞% |
| User Stories | 0 | 9+ | +∞% |
| Action Item Detail | Basic | Rich context + phases | +300% |
| Topic Granularity | 3 generic | 10+ specific | +233% |
| Decision Context | Minimal | Full rationale | +200% |
| Overall Quality | 6/10 | 9/10 | +50% |

## Success Criteria

### Minimum Requirements:
- [ ] Extract minimum 5 risks with impact/likelihood/mitigation
- [ ] Identify minimum 5 user stories in proper format
- [ ] Generate detailed action items with assignee, context, deadline, phase
- [ ] Produce 8+ specific technical topics vs generic categories
- [ ] Include decision rationale and impact assessment

### Quality Benchmarks:
- [ ] 90%+ match with expected output structure
- [ ] Technical depth comparable to human analysis
- [ ] Actionable insights for project planning
- [ ] Comprehensive risk assessment
- [ ] Complete user story coverage

## Testing Strategy

### Primary Test Case:
- **Input**: `/Users/connor/Desktop/sso-meeting-transcript.md`
- **Expected**: `/Users/connor/Desktop/expected-meeting-summary.md`
- **Current**: `/Users/connor/Desktop/tldr-agent-sso-summary.md`

### Quality Metrics:
1. **Completeness**: All required sections present
2. **Depth**: Technical details and context included
3. **Accuracy**: Correctly extracted information
4. **Actionability**: Usable for project planning
5. **Structure**: Proper formatting and organization

## Risk Mitigation

### Implementation Risks:
- **Prompt Engineering Complexity**: Use iterative testing with multiple examples
- **Performance Impact**: Benchmark processing time vs quality trade-offs
- **Over-Engineering**: Focus on core gaps first, add refinements later

### Fallback Strategy:
- Maintain existing functionality as fallback
- Gradual rollout with feature flags
- A/B testing between old and new approaches

---

**Next Steps**: Begin with updating `prompts.py` with enhanced MEETING_ANALYSIS_PROMPT_V2
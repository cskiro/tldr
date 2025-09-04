# Phase 3: MVP Implementation Plan - AI Services

**Date**: September 4, 2025  
**Status**: Ready to implement  
**Objective**: Minimum viable path to test Teams transcript → AI summary pipeline

## Critical Path Overview

This plan focuses on the minimum implementation needed to process a real Teams meeting transcript and generate accurate, valuable summaries with action items and next steps.

## Current State Analysis

### ✅ What's Already Complete
- **Complete API endpoints** with routing, validation, and error handling
- **Comprehensive models** for transcripts, summaries, action items, decisions
- **In-memory storage** for testing (no database needed initially)
- **Middleware stack** with logging, exceptions, CORS, security headers
- **93 test cases** with 94.5% coverage following TDD principles

### ❌ Critical Missing Pieces
- **Actual AI processing services** (currently using mock data)
- **Connection between upload → processing → summary** (endpoints exist but don't process)
- **OpenAI integration** for summarization and extraction

## Implementation Plan (1-2 Days)

### Phase 1: Create AI Service Layer (Day 1)

#### 1.1 Summarization Service (`src/services/summarization_service.py`)
```python
class SummarizationService:
    """AI-powered transcript summarization using OpenAI GPT-4"""
    
    def summarize_transcript(self, text: str) -> MeetingSummary
    def extract_action_items(self, text: str) -> List[ActionItem]
    def extract_decisions(self, text: str) -> List[Decision] 
    def identify_topics(self, text: str) -> List[str]
```

**Features:**
- OpenAI GPT-4 integration with structured prompts
- JSON-formatted responses for reliable parsing
- Error handling and retry logic
- Mock mode for testing without API calls
- Token usage monitoring and cost optimization

#### 1.2 Processing Service (`src/services/processing_service.py`)
```python
class ProcessingService:
    """Orchestrates the full processing pipeline"""
    
    def process_meeting(self, meeting_id: str) -> None
    def update_status(self, meeting_id: str, status: TranscriptStatus) -> None
    def handle_processing_error(self, meeting_id: str, error: Exception) -> None
```

**Pipeline:**
1. Load transcript from storage
2. Call summarization service with transcript text
3. Parse and validate AI response
4. Store structured summary in summaries_storage
5. Update processing status to COMPLETED
6. Handle errors gracefully with detailed logging

#### 1.3 Configuration Updates
- Add `openai>=1.0.0` to requirements.txt
- Add OPENAI_API_KEY to environment configuration
- Configure model selection (gpt-4, gpt-3.5-turbo fallback)
- Add cost monitoring and rate limiting

### Phase 2: Connect Services to Endpoints (Day 1-2)

#### 2.1 Wire Processing Service
- **Update** `/api/v1/transcripts/process` endpoint
- Replace "TODO: Start actual async processing task" with real implementation
- Use asyncio background tasks for async processing
- Update `processing_status_storage` during processing stages
- Add processing queue for handling multiple requests

#### 2.2 Connect Summary Retrieval
- **Replace** `create_sample_summary()` in summaries.py
- Store processed summaries in `summaries_storage` dict
- Enable summary export in JSON, Markdown, and PDF formats
- Add summary statistics and analytics

#### 2.3 Simple Web UI (Optional but helpful)
- Basic HTML form at `/test` endpoint
- Text area to paste Teams transcript
- Display processing status with real-time updates
- Show formatted summary results with action items

### Phase 3: Test with Real Teams Transcript (Day 2)

#### 3.1 Test Upload Flow
1. **POST** Teams transcript text to `/api/v1/transcripts/upload`
2. **POST** trigger processing via `/api/v1/transcripts/process`
3. **GET** monitor status via `/api/v1/transcripts/{meeting_id}/status`
4. **GET** retrieve summary via `/api/v1/summaries/{meeting_id}`

#### 3.2 Validate Output Quality
- Check action item extraction accuracy (assignees, deadlines)
- Verify decision capture with rationale and decision makers
- Review summary completeness and relevance
- Test export formats (JSON, Markdown, PDF)

## Technical Implementation Details

### OpenAI Prompt Template
```
You are an expert meeting analyst. Analyze this meeting transcript and extract structured information.

TRANSCRIPT:
{transcript_text}

INSTRUCTIONS:
1. Create a concise executive summary (2-3 sentences)
2. Extract action items with assignees and deadlines
3. Identify key decisions with rationale and decision makers
4. List main topics discussed
5. Suggest next steps

Return your response as valid JSON with this exact structure:
{
  "summary": "string",
  "key_topics": ["topic1", "topic2"],
  "action_items": [
    {
      "task": "string",
      "assignee": "string", 
      "due_date": "YYYY-MM-DD or null",
      "priority": "high|medium|low",
      "context": "string"
    }
  ],
  "decisions": [
    {
      "decision": "string",
      "made_by": "string",
      "rationale": "string", 
      "impact": "high|medium|low",
      "status": "approved"
    }
  ],
  "next_steps": ["step1", "step2"],
  "sentiment": "positive|neutral|negative"
}
```

### Processing Pipeline Architecture
```
Teams Transcript Input
        ↓
   Validate & Store
        ↓
   Queue Processing
        ↓
   OpenAI Analysis
        ↓ 
   Parse JSON Response
        ↓
   Store Summary
        ↓
   Update Status
        ↓
   Return Results
```

### Error Handling Strategy
- **OpenAI API failures**: Retry with exponential backoff
- **Parsing errors**: Log details and return structured error
- **Rate limits**: Queue processing and respect limits
- **Cost limits**: Monitor token usage and stop if exceeded
- **Malformed input**: Validate transcript before processing

## What We're Skipping (Not Critical for MVP)

### ❌ Database Integration
- **Current**: In-memory storage (`meetings_storage`, `summaries_storage`)
- **Later**: PostgreSQL with persistence and concurrent access
- **Why skip**: Testing doesn't require persistence

### ❌ Audio Transcription 
- **Current**: Teams provides text transcripts directly
- **Later**: AssemblyAI/Whisper for audio file processing
- **Why skip**: Manual text input is sufficient for validation

### ❌ User Authentication
- **Current**: Single user testing environment
- **Later**: JWT auth and user management
- **Why skip**: Focus on AI quality first

### ❌ Teams API Integration
- **Current**: Manual copy-paste of transcript text
- **Later**: Microsoft Graph API for automatic fetching
- **Why skip**: Manual testing is faster for iteration

### ❌ Production Deployment
- **Current**: Local development server
- **Later**: Docker + Kubernetes + monitoring
- **Why skip**: Validate AI accuracy before scaling

## Success Criteria

### ✓ Functional Requirements
- Can paste Teams transcript text into system
- Processes transcript through OpenAI GPT-4
- Generates accurate summary with key information
- Extracts actionable items with assignees
- Identifies decisions with proper context
- Returns structured, useful output

### ✓ Quality Requirements  
- Action item extraction >85% accuracy
- Decision identification >90% accuracy
- Summary completeness rated >4/5
- Processing time <30 seconds for typical meeting
- Error handling prevents system crashes

### ✓ Technical Requirements
- All existing tests continue to pass
- New services integrate cleanly with endpoints
- Logging provides clear debugging information
- OpenAI costs remain under $1 per meeting

## Implementation Timeline

### Day 1 (Morning)
- Create summarization_service.py with OpenAI integration
- Create processing_service.py with pipeline orchestration
- Add OpenAI configuration and environment setup

### Day 1 (Afternoon)
- Wire processing service to transcript endpoints
- Update summary retrieval to use real data
- Add comprehensive error handling

### Day 2 (Morning)
- Test with sample Teams transcript
- Refine prompts based on output quality
- Add simple web UI for easier testing

### Day 2 (Afternoon)  
- Validate accuracy with multiple transcript types
- Document findings and improvement areas
- Prepare for production deployment planning

## Files to Create/Modify

### New Files
- `src/services/__init__.py`
- `src/services/summarization_service.py`
- `src/services/processing_service.py`
- `src/templates/test.html` (simple UI)

### Modified Files
- `requirements.txt` (add openai)
- `src/core/config.py` (add OpenAI settings)
- `src/api/v1/endpoints/transcripts.py` (wire processing)
- `src/api/v1/endpoints/summaries.py` (connect real data)
- `src/main.py` (add test UI endpoint)

### Test Files
- `tests/unit/services/test_summarization_service.py`
- `tests/unit/services/test_processing_service.py`
- `tests/integration/test_full_pipeline.py`

## Risk Mitigation

### OpenAI API Reliability
- Implement retry logic with exponential backoff
- Add fallback to GPT-3.5-turbo if GPT-4 fails
- Cache responses to avoid reprocessing

### Cost Control
- Monitor token usage per request
- Set daily/monthly spending limits
- Use shorter prompts for initial testing

### Quality Assurance
- Test with diverse meeting types (standup, planning, retrospective)
- Validate against human-generated summaries
- Iterate on prompts based on accuracy metrics

## Expected Outcomes

After completion, you will have a fully functional MVP that can:
1. Accept Teams meeting transcripts via API
2. Process them through advanced AI summarization
3. Generate accurate, actionable summaries
4. Export results in multiple formats
5. Provide real-time processing status

This foundation will validate the AI approach and inform decisions about database integration, authentication, and production deployment.
# Phase 3B: Hybrid AI Services Implementation Plan

**Date**: September 4, 2025  
**Status**: Approved for implementation  
**Objective**: Implement flexible AI summarization supporting both local LLMs (Ollama) and customer-owned API keys

## Overview

Implement a flexible AI summarization service supporting both local LLMs (via Ollama) and customer-owned API keys for OpenAI/Anthropic, enabling meeting transcript processing without requiring upfront API costs.

## Research Summary

### Local LLM Options (Ollama)
- **Ollama 0.5+** supports structured outputs with JSON schema validation
- **Llama 3.2:3b** optimized for on-device summarization tasks (TLDR9 score: 19.0)
- **Structured Output**: Native Pydantic schema support via `format` parameter
- **Performance**: Processing time varies by hardware (30s-2min for typical meeting)
- **Quality**: ~60-70% of GPT-4 performance for meeting analysis

### LangChain Integration
- `.with_structured_output()` method for consistent schema-based extraction
- Support for Ollama, OpenAI, Anthropic providers through unified interface
- Map-reduce approaches for long documents
- Built-in retry logic and error handling

### API Key Management Best Practices
- Environment variables for secure storage
- Customer-owned keys for multi-tenant SaaS
- Principle of least privilege with scoped access
- Regular key rotation (90-day cycles)
- Real-time monitoring and usage tracking

## Implementation Plan

### Phase 1: Ollama Integration (Day 1 Morning)

#### 1.1 Install and Configure Ollama
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Llama 3.2 model
ollama pull llama3.2:3b

# Verify installation
ollama list

# Start Ollama server (default port 11434)
ollama serve
```

#### 1.2 Create Ollama Service (`src/services/ollama_service.py`)
```python
class OllamaService(SummarizationServiceBase):
    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.model = "llama3.2:3b"
    
    async def summarize_transcript(self, meeting_id: str, transcript_text: str) -> MeetingSummary:
        # Implement structured output using Pydantic schemas
        # Use format parameter for JSON schema validation
        # Include retry logic for malformed responses
```

#### 1.3 Update Dependencies
Add to requirements.txt:
```
ollama>=0.3.0
langchain-ollama>=0.1.0
```

### Phase 2: Customer API Key Support (Day 1 Afternoon)

#### 2.1 Create LLM Provider Service (`src/services/llm_provider_service.py`)
```python
class LLMProviderService(SummarizationServiceBase):
    """Supports OpenAI, Anthropic, and other providers with customer keys"""
    
    def __init__(self, provider: str, api_key: str = None):
        self.provider = provider
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        self.client = self._initialize_client()
    
    def _initialize_client(self):
        if self.provider == "openai":
            return OpenAI(api_key=self.api_key)
        elif self.provider == "anthropic":
            return Anthropic(api_key=self.api_key)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
```

#### 2.2 Update Configuration (`src/core/config.py`)
```python
class Settings(BaseSettings):
    # LLM Provider Configuration
    llm_provider: str = "ollama"  # ollama, openai, anthropic, or mock
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    
    # Processing Configuration
    max_tokens: int = 4000
    temperature: float = 0.1
    enable_structured_output: bool = True
```

#### 2.3 Create Service Factory (`src/services/summarization_factory.py`)
```python
def create_summarization_service(provider: str = None, api_key: str = None) -> SummarizationServiceBase:
    provider = provider or settings.llm_provider
    
    if provider == "ollama":
        return OllamaService()
    elif provider == "openai" and (api_key or settings.openai_api_key):
        return LLMProviderService("openai", api_key or settings.openai_api_key)
    elif provider == "anthropic" and (api_key or settings.anthropic_api_key):
        return LLMProviderService("anthropic", api_key or settings.anthropic_api_key)
    else:
        service_logger.warning(f"Falling back to mock service - provider: {provider}")
        return MockSummarizationService()
```

### Phase 3: Structured Output Implementation (Day 2 Morning)

#### 3.1 Define Extraction Prompts (`src/services/prompts.py`)
```python
MEETING_ANALYSIS_PROMPT = """
Analyze this meeting transcript and extract structured information focusing on key decisions, action items, risks, user stories, and next steps.

TRANSCRIPT:
{transcript}

INSTRUCTIONS:
1. Create a concise executive summary (2-3 sentences)
2. Extract key decisions with decision makers and rationale
3. Identify action items with specific assignees and deadlines
4. Document risks and mitigation strategies
5. Extract user stories in proper format
6. List concrete next steps

Return your response as valid JSON with this exact structure:
{
  "executive_summary": "string",
  "key_decisions": [
    {
      "decision": "string",
      "made_by": "string",
      "rationale": "string",
      "impact": "high|medium|low",
      "status": "approved|pending|rejected"
    }
  ],
  "action_items": [
    {
      "task": "string",
      "assignee": "string", 
      "due_date": "YYYY-MM-DD or null",
      "priority": "high|medium|low",
      "context": "string",
      "status": "pending"
    }
  ],
  "risks": [
    {
      "risk": "string",
      "impact": "high|medium|low",
      "likelihood": "high|medium|low",
      "mitigation": "string",
      "owner": "string or null"
    }
  ],
  "user_stories": [
    {
      "story": "As a [user type], I want [goal], so that [benefit]",
      "acceptance_criteria": ["criteria1", "criteria2"],
      "priority": "high|medium|low",
      "epic": "string or null"
    }
  ],
  "next_steps": ["step1", "step2"],
  "key_topics": ["topic1", "topic2"],
  "participants": ["person1", "person2"],
  "sentiment": "positive|neutral|negative|mixed"
}
"""

FALLBACK_EXTRACTION_PATTERNS = {
    "action_items": [
        r"(?:action item|todo|task|follow up):\s*(.+?)(?:\n|$)",
        r"(.+?)\s+(?:will|should|needs to)\s+(.+?)(?:\s+by\s+(\S+?))?(?:\n|$)",
        r"@(\w+)\s+(.+?)(?:\s+due\s+(\S+?))?(?:\n|$)"
    ],
    "decisions": [
        r"(?:decision|decided|agreed):\s*(.+?)(?:\n|$)",
        r"we\s+(?:decided|agreed)\s+(?:to|that)\s+(.+?)(?:\n|$)"
    ],
    "risks": [
        r"(?:risk|concern|issue|problem):\s*(.+?)(?:\n|$)",
        r"(?:might|could|may)\s+(?:be|cause|lead to)\s+(.+?)(?:\n|$)"
    ]
}
```

#### 3.2 Implement Structured Output with Ollama
```python
class OllamaService(SummarizationServiceBase):
    async def _extract_with_structured_output(self, transcript: str) -> dict:
        """Use Ollama's structured output feature with Pydantic schema"""
        schema = MeetingSummary.model_json_schema()
        
        response = await self.client.chat(
            messages=[{
                'role': 'user', 
                'content': MEETING_ANALYSIS_PROMPT.format(transcript=transcript)
            }],
            model=self.model,
            format=schema,  # Ollama structured output
            options={
                'temperature': settings.temperature,
                'num_predict': settings.max_tokens
            }
        )
        
        try:
            return json.loads(response['message']['content'])
        except json.JSONDecodeError as e:
            service_logger.error(f"Failed to parse JSON: {e}")
            return await self._extract_with_fallback(transcript)
    
    async def _extract_with_fallback(self, transcript: str) -> dict:
        """Fallback to regex extraction if structured output fails"""
        # Implement regex-based extraction using FALLBACK_EXTRACTION_PATTERNS
        pass
```

#### 3.3 Create Response Parsers and Validators
```python
class ResponseParser:
    @staticmethod
    def validate_and_clean(raw_response: dict) -> dict:
        """Validate response against schema and clean data"""
        # Ensure all required fields exist
        # Clean and normalize data
        # Handle partial responses gracefully
        pass
    
    @staticmethod
    def extract_with_confidence(raw_response: dict) -> tuple[dict, float]:
        """Return extracted data with confidence score"""
        # Calculate confidence based on completeness and structure
        pass
```

### Phase 4: Wire Services to Endpoints (Day 2 Afternoon)

#### 4.1 Update Processing Service
```python
# src/services/processing_service.py
async def process_meeting_background(meeting_id: str, provider: str = None, api_key: str = None):
    """Process meeting with configurable LLM provider"""
    try:
        processing_status_storage[meeting_id] = ProcessingStatus(
            meeting_id=meeting_id,
            status=TranscriptStatus.PROCESSING,
            progress=10,
            message="Initializing AI service..."
        )
        
        # Create appropriate service
        service = create_summarization_service(provider, api_key)
        
        # Load transcript
        meeting_data = meetings_storage.get(meeting_id)
        if not meeting_data:
            raise MeetingNotFoundError(f"Meeting {meeting_id} not found")
        
        processing_status_storage[meeting_id].progress = 25
        processing_status_storage[meeting_id].message = "Analyzing transcript..."
        
        # Generate summary
        summary = await service.summarize_transcript(meeting_id, meeting_data["raw_text"])
        
        # Store result
        summaries_storage[meeting_id] = summary.model_dump()
        
        processing_status_storage[meeting_id] = ProcessingStatus(
            meeting_id=meeting_id,
            status=TranscriptStatus.COMPLETED,
            progress=100,
            message="Analysis complete"
        )
        
    except Exception as e:
        processing_logger.error(f"Processing failed for {meeting_id}: {str(e)}")
        processing_status_storage[meeting_id] = ProcessingStatus(
            meeting_id=meeting_id,
            status=TranscriptStatus.FAILED,
            progress=0,
            message=f"Processing failed: {str(e)}"
        )
```

#### 4.2 Add Provider Configuration Endpoint
```python
# src/api/v1/endpoints/config.py
@router.post("/provider")
async def configure_llm_provider(
    provider: str = Form(...),
    api_key: Optional[str] = Form(None)
) -> APIResponse:
    """Configure LLM provider for current session"""
    
    if provider not in ["ollama", "openai", "anthropic", "mock"]:
        raise ValidationError(f"Unsupported provider: {provider}")
    
    # For demo purposes, store in memory
    # In production, this would be user-specific and encrypted
    session_config["llm_provider"] = provider
    if api_key:
        session_config["api_key"] = api_key
    
    return APIResponse(
        success=True,
        message=f"LLM provider set to {provider}",
        data={"provider": provider, "has_api_key": bool(api_key)}
    )
```

#### 4.3 Update Transcript Processing Endpoint
```python
# Update existing /api/v1/transcripts/process endpoint
@router.post("/process")
async def process_transcript(
    meeting_id: str = Form(...),
    provider: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> APIResponse:
    """Process transcript with specified or configured provider"""
    
    # Use provider from request or session config
    provider = provider or session_config.get("llm_provider", "ollama")
    api_key = api_key or session_config.get("api_key")
    
    # Start background processing
    background_tasks.add_task(process_meeting_background, meeting_id, provider, api_key)
    
    return APIResponse(
        success=True,
        message=f"Processing started with {provider} provider",
        data={
            "meeting_id": meeting_id,
            "provider": provider,
            "status_url": f"/api/v1/transcripts/{meeting_id}/status"
        }
    )
```

### Phase 5: Testing & Validation (Day 3)

#### 5.1 Create Test Transcripts
```python
# tests/fixtures/sample_transcripts.py
TEAMS_MEETING_TRANSCRIPT = """
[2025-09-04 10:00:00] John Smith: Good morning everyone. Let's start our sprint planning meeting.

[10:01:00] Sarah Johnson: Thanks John. I've prepared the user stories for this sprint.

[10:02:00] Mike Chen: Before we dive in, we need to address the database performance issue from last sprint.

[10:03:00] Sarah Johnson: Good point Mike. That's a high priority item. Can you take ownership of that?

[10:03:30] Mike Chen: Yes, I'll investigate and have a solution by Friday.

[10:04:00] John Smith: Perfect. Sarah, what user stories do we have?

[10:05:00] Sarah Johnson: We have three main stories: 
1. As a user, I want to export meeting summaries to PDF, so that I can share them with stakeholders
2. As an admin, I want to configure API rate limits, so that we don't exceed our quotas
3. As a developer, I want better error logging, so that debugging is easier

[10:07:00] Mike Chen: The PDF export might be complex. What's the timeline?

[10:08:00] Sarah Johnson: I was thinking end of sprint, but we could push to next sprint if needed.

[10:09:00] John Smith: Let's decide - we'll aim for end of sprint but be flexible. The API rate limiting is critical though.

[10:10:00] Sarah Johnson: Agreed. I'll prioritize the rate limiting story as high priority.

[10:11:00] John Smith: Great. Any risks we should be aware of?

[10:12:00] Mike Chen: The main risk is if the database issue is more complex than expected. It could impact our velocity.

[10:13:00] John Smith: Good catch. What's our mitigation plan?

[10:14:00] Mike Chen: I'll do a quick investigation today and update the team by EOD. If it's complex, we might need to bring in the DBA team.

[10:15:00] Sarah Johnson: Sounds good. Next steps are: Mike investigates DB issue, I'll refine the user stories, and John will update stakeholders.

[10:16:00] John Smith: Perfect. Meeting adjourned. Thanks everyone!
"""

EXPECTED_EXTRACTION = {
    "action_items": [
        {"assignee": "Mike Chen", "task": "investigate database performance issue", "due_date": "2025-09-06"},
        {"assignee": "Sarah Johnson", "task": "refine user stories", "due_date": None},
        {"assignee": "John Smith", "task": "update stakeholders", "due_date": None}
    ],
    "decisions": [
        {"decision": "prioritize API rate limiting as high priority", "made_by": "Sarah Johnson"},
        {"decision": "aim for PDF export by end of sprint but be flexible", "made_by": "John Smith"}
    ],
    "risks": [
        {"risk": "database issue more complex than expected", "impact": "high", "mitigation": "quick investigation and potential DBA involvement"}
    ]
}
```

#### 5.2 Implement Integration Tests
```python
# tests/integration/test_ai_services.py
import pytest
from src.services.summarization_factory import create_summarization_service
from tests.fixtures.sample_transcripts import TEAMS_MEETING_TRANSCRIPT, EXPECTED_EXTRACTION

class TestOllamaIntegration:
    @pytest.mark.asyncio
    async def test_ollama_summarization(self):
        """Test Ollama service with real model"""
        service = create_summarization_service("ollama")
        summary = await service.summarize_transcript("test_meeting", TEAMS_MEETING_TRANSCRIPT)
        
        assert summary.action_items
        assert len(summary.action_items) >= 3
        assert any("database" in item.task.lower() for item in summary.action_items)
        assert summary.decisions
        assert summary.risks

    @pytest.mark.asyncio
    async def test_provider_switching(self):
        """Test switching between providers"""
        mock_service = create_summarization_service("mock")
        assert mock_service.__class__.__name__ == "MockSummarizationService"
        
        ollama_service = create_summarization_service("ollama")
        assert ollama_service.__class__.__name__ == "OllamaService"

    @pytest.mark.asyncio
    async def test_extraction_accuracy(self):
        """Test extraction accuracy against expected results"""
        service = create_summarization_service("ollama")
        summary = await service.summarize_transcript("accuracy_test", TEAMS_MEETING_TRANSCRIPT)
        
        # Check action items accuracy
        extracted_assignees = {item.assignee for item in summary.action_items}
        expected_assignees = {item["assignee"] for item in EXPECTED_EXTRACTION["action_items"]}
        
        accuracy = len(extracted_assignees & expected_assignees) / len(expected_assignees)
        assert accuracy >= 0.7, f"Action item extraction accuracy too low: {accuracy}"

class TestPerformance:
    @pytest.mark.asyncio
    async def test_processing_time(self):
        """Test processing time benchmarks"""
        import time
        
        service = create_summarization_service("ollama")
        start_time = time.time()
        
        await service.summarize_transcript("perf_test", TEAMS_MEETING_TRANSCRIPT)
        
        processing_time = time.time() - start_time
        assert processing_time < 60, f"Processing took too long: {processing_time}s"

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_malformed_json_recovery(self):
        """Test recovery from malformed JSON responses"""
        service = create_summarization_service("ollama")
        
        # This should not crash even with problematic input
        summary = await service.summarize_transcript("error_test", "Invalid transcript content...")
        
        assert summary is not None
        assert hasattr(summary, 'action_items')
```

#### 5.3 Quality Metrics and Monitoring
```python
# src/core/metrics.py
class ExtractionMetrics:
    @staticmethod
    def calculate_extraction_accuracy(extracted: dict, expected: dict) -> dict:
        """Calculate accuracy metrics for extracted data"""
        metrics = {}
        
        for category in ['action_items', 'decisions', 'risks']:
            if category in extracted and category in expected:
                extracted_count = len(extracted[category])
                expected_count = len(expected[category])
                
                # Simple overlap-based accuracy
                if expected_count > 0:
                    accuracy = min(extracted_count / expected_count, 1.0)
                    metrics[f"{category}_accuracy"] = accuracy
        
        return metrics
    
    @staticmethod
    def track_processing_metrics(meeting_id: str, provider: str, 
                               processing_time: float, accuracy: dict):
        """Track metrics for monitoring dashboard"""
        metrics = {
            "meeting_id": meeting_id,
            "provider": provider,
            "processing_time": processing_time,
            "timestamp": datetime.now(UTC),
            **accuracy
        }
        
        # In production, send to metrics store
        processing_logger.info("Processing metrics", extra=metrics)
```

### Phase 6: Simple Test UI (Day 3)

#### 6.1 Create Test Interface (`src/templates/test.html`)
```html
<!DOCTYPE html>
<html>
<head>
    <title>TLDR AI Meeting Summarizer - Test Interface</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        textarea, select, input { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        textarea { height: 200px; font-family: monospace; }
        .results { margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 4px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .status.processing { background: #fff3cd; border: 1px solid #ffeaa7; }
        .status.completed { background: #d4edda; border: 1px solid #c3e6cb; }
        .status.failed { background: #f8d7da; border: 1px solid #f5c6cb; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .extracted-section { margin: 15px 0; padding: 10px; border-left: 4px solid #007bff; background: white; }
    </style>
</head>
<body>
    <h1>🤖 TLDR AI Meeting Summarizer</h1>
    <p>Test interface for processing meeting transcripts with local and cloud AI models.</p>
    
    <form id="analyzeForm">
        <div class="form-group">
            <label for="provider">AI Provider:</label>
            <select id="provider" name="provider">
                <option value="ollama">Ollama (Local)</option>
                <option value="openai">OpenAI (API Key Required)</option>
                <option value="anthropic">Anthropic (API Key Required)</option>
                <option value="mock">Mock Service (Testing)</option>
            </select>
        </div>
        
        <div class="form-group" id="apiKeyGroup" style="display: none;">
            <label for="apiKey">API Key (Optional - uses environment variables if not provided):</label>
            <input type="password" id="apiKey" name="api_key" placeholder="Enter your API key...">
        </div>
        
        <div class="form-group">
            <label for="transcript">Meeting Transcript:</label>
            <textarea id="transcript" name="transcript" placeholder="Paste your Teams/Zoom meeting transcript here..."></textarea>
        </div>
        
        <button type="submit">🚀 Analyze Meeting</button>
    </form>
    
    <div id="status" class="status" style="display: none;"></div>
    
    <div id="results" class="results" style="display: none;">
        <h2>📊 Analysis Results</h2>
        <div id="summary"></div>
        <div id="actionItems"></div>
        <div id="decisions"></div>
        <div id="risks"></div>
        <div id="userStories"></div>
        <div id="nextSteps"></div>
    </div>

    <script>
        // Sample transcript for testing
        const sampleTranscript = `[2025-09-04 10:00:00] John Smith: Good morning everyone. Let's start our sprint planning meeting.
[10:01:00] Sarah Johnson: Thanks John. I've prepared the user stories for this sprint.
[10:02:00] Mike Chen: Before we dive in, we need to address the database performance issue from last sprint.
[10:03:00] Sarah Johnson: Good point Mike. That's a high priority item. Can you take ownership of that?
[10:03:30] Mike Chen: Yes, I'll investigate and have a solution by Friday.
[10:04:00] John Smith: Perfect. Sarah, what user stories do we have?
[10:05:00] Sarah Johnson: We have three main stories: 
1. As a user, I want to export meeting summaries to PDF, so that I can share them with stakeholders
2. As an admin, I want to configure API rate limits, so that we don't exceed our quotas
3. As a developer, I want better error logging, so that debugging is easier
[10:10:00] John Smith: Great. Any risks we should be aware of?
[10:12:00] Mike Chen: The main risk is if the database issue is more complex than expected. It could impact our velocity.
[10:15:00] Sarah Johnson: Next steps are: Mike investigates DB issue, I'll refine the user stories, and John will update stakeholders.`;

        // Load sample transcript on page load
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('transcript').value = sampleTranscript;
        });

        // Show/hide API key field based on provider
        document.getElementById('provider').addEventListener('change', function() {
            const apiKeyGroup = document.getElementById('apiKeyGroup');
            const provider = this.value;
            if (provider === 'openai' || provider === 'anthropic') {
                apiKeyGroup.style.display = 'block';
            } else {
                apiKeyGroup.style.display = 'none';
            }
        });

        // Handle form submission
        document.getElementById('analyzeForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const statusDiv = document.getElementById('status');
            const resultsDiv = document.getElementById('results');
            
            statusDiv.style.display = 'block';
            statusDiv.className = 'status processing';
            statusDiv.innerHTML = '🔄 Processing transcript...';
            resultsDiv.style.display = 'none';
            
            try {
                // Step 1: Upload transcript
                const uploadResponse = await fetch('/api/v1/transcripts/upload', {
                    method: 'POST',
                    body: formData
                });
                const uploadResult = await uploadResponse.json();
                
                if (!uploadResult.success) {
                    throw new Error(uploadResult.message);
                }
                
                const meetingId = uploadResult.data.meeting_id;
                
                // Step 2: Process transcript
                const processFormData = new FormData();
                processFormData.append('meeting_id', meetingId);
                processFormData.append('provider', formData.get('provider'));
                if (formData.get('api_key')) {
                    processFormData.append('api_key', formData.get('api_key'));
                }
                
                const processResponse = await fetch('/api/v1/transcripts/process', {
                    method: 'POST',
                    body: processFormData
                });
                const processResult = await processResponse.json();
                
                if (!processResult.success) {
                    throw new Error(processResult.message);
                }
                
                // Step 3: Poll for completion
                await pollForCompletion(meetingId);
                
            } catch (error) {
                statusDiv.className = 'status failed';
                statusDiv.innerHTML = `❌ Error: ${error.message}`;
            }
        });

        async function pollForCompletion(meetingId) {
            const statusDiv = document.getElementById('status');
            const maxAttempts = 60; // 2 minutes max
            let attempts = 0;
            
            const poll = async () => {
                attempts++;
                
                try {
                    const response = await fetch(`/api/v1/transcripts/${meetingId}/status`);
                    const result = await response.json();
                    
                    if (result.success) {
                        const status = result.data.status;
                        const progress = result.data.progress || 0;
                        
                        statusDiv.innerHTML = `🔄 ${result.data.message} (${progress}%)`;
                        
                        if (status === 'completed') {
                            statusDiv.className = 'status completed';
                            statusDiv.innerHTML = '✅ Processing completed!';
                            await loadResults(meetingId);
                            return;
                        } else if (status === 'failed') {
                            statusDiv.className = 'status failed';
                            statusDiv.innerHTML = `❌ Processing failed: ${result.data.message}`;
                            return;
                        }
                    }
                    
                    if (attempts < maxAttempts) {
                        setTimeout(poll, 2000); // Poll every 2 seconds
                    } else {
                        statusDiv.className = 'status failed';
                        statusDiv.innerHTML = '❌ Processing timeout - please try again';
                    }
                } catch (error) {
                    statusDiv.className = 'status failed';
                    statusDiv.innerHTML = `❌ Error checking status: ${error.message}`;
                }
            };
            
            poll();
        }

        async function loadResults(meetingId) {
            try {
                const response = await fetch(`/api/v1/summaries/${meetingId}`);
                const result = await response.json();
                
                if (result.success) {
                    displayResults(result.data);
                } else {
                    throw new Error(result.message);
                }
            } catch (error) {
                document.getElementById('status').innerHTML = `❌ Error loading results: ${error.message}`;
            }
        }

        function displayResults(summary) {
            const resultsDiv = document.getElementById('results');
            resultsDiv.style.display = 'block';
            
            // Executive Summary
            document.getElementById('summary').innerHTML = `
                <div class="extracted-section">
                    <h3>📋 Executive Summary</h3>
                    <p>${summary.summary || 'No summary available'}</p>
                </div>
            `;
            
            // Action Items
            const actionItemsHtml = summary.action_items?.map(item => `
                <li><strong>${item.assignee}:</strong> ${item.task} 
                    ${item.due_date ? `(Due: ${item.due_date})` : ''}
                    <span style="color: ${item.priority === 'high' ? 'red' : item.priority === 'medium' ? 'orange' : 'green'}">
                        [${item.priority} priority]
                    </span>
                </li>
            `).join('') || '<li>No action items found</li>';
            
            document.getElementById('actionItems').innerHTML = `
                <div class="extracted-section">
                    <h3>✅ Action Items</h3>
                    <ul>${actionItemsHtml}</ul>
                </div>
            `;
            
            // Decisions
            const decisionsHtml = summary.decisions?.map(decision => `
                <li><strong>${decision.decision}</strong> 
                    (Made by: ${decision.made_by}, Impact: ${decision.impact})
                    ${decision.rationale ? `<br><em>Rationale: ${decision.rationale}</em>` : ''}
                </li>
            `).join('') || '<li>No decisions found</li>';
            
            document.getElementById('decisions').innerHTML = `
                <div class="extracted-section">
                    <h3>⚖️ Key Decisions</h3>
                    <ul>${decisionsHtml}</ul>
                </div>
            `;
            
            // Risks
            const risksHtml = summary.risks?.map(risk => `
                <li><strong>${risk.risk}</strong> 
                    <span style="color: ${risk.impact === 'high' ? 'red' : risk.impact === 'medium' ? 'orange' : 'green'}">
                        [${risk.impact} impact]
                    </span>
                    ${risk.mitigation ? `<br><em>Mitigation: ${risk.mitigation}</em>` : ''}
                </li>
            `).join('') || '<li>No risks identified</li>';
            
            document.getElementById('risks').innerHTML = `
                <div class="extracted-section">
                    <h3>⚠️ Risks & Concerns</h3>
                    <ul>${risksHtml}</ul>
                </div>
            `;
            
            // User Stories
            const userStoriesHtml = summary.user_stories?.map(story => `
                <li><strong>${story.story}</strong>
                    <span style="color: ${story.priority === 'high' ? 'red' : story.priority === 'medium' ? 'orange' : 'green'}">
                        [${story.priority} priority]
                    </span>
                    ${story.acceptance_criteria?.length ? `<br><em>Acceptance Criteria: ${story.acceptance_criteria.join(', ')}</em>` : ''}
                </li>
            `).join('') || '<li>No user stories found</li>';
            
            document.getElementById('userStories').innerHTML = `
                <div class="extracted-section">
                    <h3>📖 User Stories</h3>
                    <ul>${userStoriesHtml}</ul>
                </div>
            `;
            
            // Next Steps
            const nextStepsHtml = summary.next_steps?.map(step => `<li>${step}</li>`).join('') || '<li>No next steps defined</li>';
            
            document.getElementById('nextSteps').innerHTML = `
                <div class="extracted-section">
                    <h3>🚀 Next Steps</h3>
                    <ul>${nextStepsHtml}</ul>
                </div>
            `;
        }
    </script>
</body>
</html>
```

#### 6.2 Add Test UI Endpoint (`src/api/v1/endpoints/ui.py`)
```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="src/templates")

@router.get("/test", response_class=HTMLResponse)
async def test_interface(request: Request):
    """Simple test interface for meeting transcript analysis"""
    return templates.TemplateResponse("test.html", {"request": request})
```

## Success Criteria

✅ **Functional Requirements**
- Can process Teams transcript text through Ollama (local, no API costs)
- Supports customer-owned OpenAI/Anthropic keys via environment variables or form input
- Extracts action items with assignees and deadlines
- Identifies key decisions with decision makers and rationale
- Documents risks and mitigation strategies
- Extracts user stories in proper format
- Provides concrete next steps

✅ **Quality Requirements**
- Action item extraction >70% accuracy with Ollama
- Decision identification >80% accuracy
- Processing completes within 60 seconds for typical meeting
- Graceful fallback to mock service if no LLM available
- All existing tests continue to pass (>80% coverage)

✅ **Technical Requirements**
- Clean integration with existing API structure
- Structured JSON responses with validation
- Comprehensive error handling and logging
- Provider switching without service restart
- Simple UI for testing and demonstration

## File Changes Summary

### New Files
- `docs/planning/phase3b-hybrid-ai-services-plan.md` (this document)
- `src/services/ollama_service.py` - Local LLM integration
- `src/services/llm_provider_service.py` - OpenAI/Anthropic support
- `src/services/summarization_factory.py` - Service selection logic
- `src/services/prompts.py` - Structured extraction prompts
- `src/core/metrics.py` - Quality monitoring
- `src/templates/test.html` - Simple test interface
- `src/api/v1/endpoints/config.py` - Provider configuration
- `src/api/v1/endpoints/ui.py` - UI routes
- `tests/integration/test_ai_services.py` - Integration tests
- `tests/fixtures/sample_transcripts.py` - Test data

### Modified Files
- `requirements.txt` - Add ollama, langchain-ollama dependencies
- `src/core/config.py` - Add LLM provider settings
- `src/services/processing_service.py` - Use factory pattern
- `src/api/v1/endpoints/transcripts.py` - Add provider parameters
- `src/main.py` - Include new routes

## Cost and Resource Analysis

### Local Deployment (Ollama)
- **Initial Setup**: 10-30 minutes
- **Model Size**: ~2GB for Llama 3.2:3b
- **Processing Time**: 30-120 seconds per meeting (hardware dependent)
- **Ongoing Costs**: $0 (electricity only)
- **Quality**: 60-70% of GPT-4 performance

### Customer API Keys
- **Setup**: <5 minutes
- **Processing Time**: 5-15 seconds per meeting
- **Cost**: Customer's responsibility (~$0.10-0.50 per meeting)
- **Quality**: 90-95% accuracy (GPT-4, Claude)

### Fallback (Mock Service)
- **Setup**: None required
- **Processing Time**: <1 second
- **Cost**: $0
- **Quality**: Rule-based patterns (40-50% accuracy)

## Risk Mitigation

### Technical Risks
- **Ollama Installation Issues**: Provide Docker alternative
- **Model Download Failures**: Include fallback to smaller model
- **Structured Output Failures**: Implement regex-based fallback
- **API Key Security**: Use secure environment variable handling

### Quality Risks
- **Local Model Accuracy**: Set expectations, provide accuracy metrics
- **Hallucination**: Add confidence scoring and validation
- **Edge Cases**: Comprehensive test coverage with various transcript types

### Operational Risks
- **Performance Variability**: Monitor processing times, provide estimates
- **Resource Usage**: Monitor CPU/memory, implement timeouts
- **User Experience**: Clear status updates and error messages

## Future Enhancements

### Phase 4 Considerations
- **Database Integration**: Replace in-memory storage
- **User Authentication**: Multi-tenant API key management
- **Teams API Integration**: Direct transcript fetching
- **Advanced Models**: Support for specialized meeting analysis models
- **Export Formats**: PDF, Word, Slack integration
- **Analytics Dashboard**: Usage metrics and quality tracking

This plan provides a complete roadmap for implementing a production-ready meeting transcript analysis system that works both offline (with Ollama) and with customer-provided API keys, addressing the core requirement of processing Teams transcripts without upfront AI service costs.
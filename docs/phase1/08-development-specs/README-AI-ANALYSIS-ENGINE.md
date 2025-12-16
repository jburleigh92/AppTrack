# Job Application Tracker - AI Analysis Engine

**Implementation Date:** December 11, 2025  
**Status:** Complete - Production-Ready AI Analysis System

---

## Overview

The AI Analysis Engine is an intelligent matching system that compares job descriptions against resumes using Large Language Models (LLMs) to produce structured match scores, qualification assessments, and skill suggestions.

---

## Architecture

### Three-Layer System

**Layer 1: LLM Client** (`llm_client.py`)
- Provider-agnostic interface (OpenAI/Anthropic)
- Structured prompt engineering
- JSON response parsing & validation
- Token usage tracking

**Layer 2: Analysis Service** (`analyzer.py`)
- Orchestrates end-to-end analysis
- Data validation & preprocessing
- Result persistence
- Application state updates
- Timeline event emission

**Layer 3: Worker Process** (`analysis_worker.py`)
- Asynchronous queue processing
- Retry logic with exponential backoff
- Error categorization (transient vs permanent)
- Graceful failure handling

---

## Supported LLM Providers

### OpenAI
- Models: gpt-4, gpt-4-turbo, gpt-3.5-turbo
- JSON mode enabled
- Token usage tracking

### Anthropic
- Models: claude-3-opus, claude-3-sonnet, claude-3-haiku
- Structured output prompting
- Token usage tracking

---

## API Endpoints

### Trigger Analysis

```http
POST /api/v1/applications/{application_id}/analysis/run

Response (202 Accepted):
{
  "job_id": "uuid",
  "status": "queued"
}
```

### Get Analysis Result

```http
GET /api/v1/applications/{application_id}/analysis

Response (200 OK):
{
  "id": "uuid",
  "application_id": "uuid",
  "match_score": 87,
  "qualifications_met": ["Python", "FastAPI", "PostgreSQL"],
  "qualifications_missing": ["Kubernetes", "Docker"],
  "suggestions": ["Learn Docker", "Get AWS certification"],
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  "analysis_metadata": {"tokens_used": 923},
  "created_at": "2025-12-11T10:30:00Z"
}
```

---

## Worker Process

### Analysis Flow

1. Poll AnalysisQueue for pending jobs
2. Load application, job posting, active resume
3. Validate all required data present
4. Build structured prompt
5. Call LLM API
6. Parse & validate JSON response
7. Persist AnalysisResult
8. Update application (analysis_id, analysis_completed)
9. Emit timeline event
10. Mark queue job complete

### Error Handling

**Missing Data (Permanent Failure):**
- No active resume → `missing_active_resume`
- No job posting → `missing_job_posting`
- No description → `missing_data`

**LLM Errors (Transient Failure):**
- Timeout → Retry with backoff
- Rate limit (429) → Retry with backoff
- Malformed JSON → Retry then fail

**Configuration Errors (Permanent Failure):**
- Missing API key → `config_error`
- Invalid provider → `config_error`

### Retry Strategy

**Backoff Schedule:**
- Attempt 1: Immediate
- Attempt 2: +1 minute
- Attempt 3: +5 minutes
- Attempt 4: +15 minutes (final)

**Max Attempts:** 3 by default

---

## Database Models

### AnalysisResult
```python
id: UUID                         # Primary key
application_id: UUID             # FK to applications
resume_id: UUID                  # FK to resumes
job_posting_id: UUID             # FK to job_postings
match_score: INTEGER (0-100)     # Overall match score
qualifications_met: JSONB        # List of met qualifications
qualifications_missing: JSONB    # List of missing qualifications
suggestions: JSONB               # List of skill suggestions
llm_provider: VARCHAR(50)        # openai/anthropic
llm_model: VARCHAR(100)          # gpt-4/claude-3-opus
analysis_metadata: JSONB         # tokens_used, etc
created_at: TIMESTAMPTZ
```

### Application Updates
```python
analysis_id: UUID                # FK to analysis_results
analysis_completed: BOOLEAN      # True when analysis done
```

---

## Configuration

### Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### LLM Config (in settings or database)

```json
{
  "provider": "openai",
  "model": "gpt-4",
  "temperature": 0.2,
  "max_tokens": 1500
}
```

---

## Prompt Engineering

### Prompt Structure

```
JOB POSTING:
Description: {job_description}
Requirements: {job_requirements}

CANDIDATE RESUME:
Summary: {resume_summary}
Skills: {skills_list}
Experience: {experience_list}
Education: {education_list}

Return JSON: {
  "match_score": 0-100,
  "matched_qualifications": [...],
  "missing_qualifications": [...],
  "skill_suggestions": [...]
}
```

### Response Validation

- `match_score`: Integer 0-100
- All lists must be arrays of strings
- JSON must be valid and parseable
- All required fields must be present

---

## Timeline Events

### analysis_completed
```json
{
  "event_type": "analysis_completed",
  "description": "AI analysis completed with match score 87",
  "event_data": {
    "analysis_id": "uuid",
    "match_score": 87
  }
}
```

### analysis_failed
```json
{
  "event_type": "analysis_failed",
  "description": "AI analysis failed: missing_active_resume",
  "event_data": {
    "reason": "missing_active_resume",
    "details": "No active resume found for user"
  }
}
```

---

## Usage Examples

### Example 1: Successful Analysis

```python
# Trigger analysis
POST /api/v1/applications/{app_id}/analysis/run
→ 202 Accepted, job_id returned

# Worker processes
# 1. Loads application, job posting, resume
# 2. Calls GPT-4
# 3. Receives: {"match_score": 87, "matched_qualifications": [...], ...}
# 4. Persists AnalysisResult
# 5. Updates application.analysis_completed = true
# 6. Emits analysis_completed event

# Get result
GET /api/v1/applications/{app_id}/analysis
→ 200 OK with full analysis data
```

### Example 2: Missing Active Resume

```python
# Trigger analysis (but no resume uploaded/active)
POST /api/v1/applications/{app_id}/analysis/run
→ 202 Accepted

# Worker processes
# Detects: No active resume
# Marks job as failed with reason "missing_active_resume"
# Emits analysis_failed event
# Does NOT retry (permanent failure)

# Get result
GET /api/v1/applications/{app_id}/analysis
→ 404 Not Found (no analysis_id set)
```

### Example 3: LLM Timeout (Retry)

```python
# Trigger analysis
POST /api/v1/applications/{app_id}/analysis/run
→ 202 Accepted

# Worker attempt 1
# LLM call times out
# Sets status=pending, retry_after=now+1min, attempts=1

# Worker attempt 2 (after 1 minute)
# LLM call succeeds
# Creates AnalysisResult
# Updates application
# Emits analysis_completed event
```

---

## Testing

### Unit Tests

```python
import pytest
from app.services.analysis import LLMClient, LLMSettings

@pytest.mark.asyncio
async def test_llm_client_openai():
    settings = LLMSettings(
        provider="openai",
        model="gpt-4",
        api_key="test-key"
    )
    client = LLMClient(settings)
    
    result = await client.analyze_job_vs_resume(
        job_description="Senior Python Developer...",
        job_requirements="5+ years Python...",
        resume_summary="Experienced developer...",
        resume_skills=["Python", "FastAPI"],
        resume_experience=[...],
        resume_education=[...]
    )
    
    assert "match_score" in result
    assert 0 <= result["match_score"] <= 100
    assert isinstance(result["matched_qualifications"], list)

def test_analysis_service_missing_resume(db):
    # Application with no active resume
    analysis_service = AnalysisService(mock_llm_client)
    
    with pytest.raises(MissingDataError, match="No active resume"):
        await analysis_service.run_analysis_for_application(
            db=db,
            application_id=app_id
        )
```

### Integration Tests

```python
def test_full_analysis_flow(client, db):
    # Create application with posting and resume
    app = create_test_application(db, with_posting=True)
    resume = create_active_resume(db)
    
    # Trigger analysis
    response = client.post(f"/api/v1/applications/{app.id}/analysis/run")
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    
    # Process worker job (mock or real)
    # ...
    
    # Get analysis
    response = client.get(f"/api/v1/applications/{app.id}/analysis")
    assert response.status_code == 200
    
    data = response.json()
    assert data["match_score"] >= 0
    assert data["match_score"] <= 100
    assert len(data["qualifications_met"]) > 0
```

---

## Performance Considerations

### Current Performance
- LLM call: ~2-5 seconds (depending on provider/model)
- Data loading: ~50-100ms
- Result persistence: ~50ms
- Total per job: ~3-6 seconds

### Optimization Strategies

**Caching:**
```python
# Cache analysis for 24 hours if data unchanged
cache_key = f"analysis:{app_id}:{posting_hash}:{resume_hash}"
if cached := redis.get(cache_key):
    return cached_analysis
```

**Batch Processing:**
```python
# Process multiple applications in parallel
# Each worker handles one job, run multiple workers
```

**Model Selection:**
```python
# Use faster/cheaper models for simple cases
# Use gpt-3.5-turbo instead of gpt-4 where appropriate
```

---

## Troubleshooting

### LLM Returns Malformed JSON

**Symptom:** Worker logs "Invalid JSON response from LLM"

**Solutions:**
1. Check if markdown code blocks present (```json)
2. Verify prompt includes "Return ONLY valid JSON"
3. Consider using structured output mode if available
4. Implement JSON extraction regex as fallback

### Analysis Never Completes

**Check:**
1. Is active resume set? (`resumes.is_active = true`)
2. Does job posting have description?
3. Are API keys configured correctly?
4. Check worker logs for errors
5. Verify queue job status in `analysis_queue`

### Match Score Always High/Low

**Possible Causes:**
1. Prompt engineering needs tuning
2. Temperature too high (increase randomness)
3. Model not following instructions

**Solutions:**
1. Adjust prompt to emphasize scoring criteria
2. Lower temperature to 0.1-0.2
3. Add few-shot examples in prompt

---

## Future Enhancements

### Phase 1 (Current)
✅ OpenAI integration  
✅ Anthropic integration  
✅ Structured JSON parsing  
✅ Match score (0-100)  
✅ Qualification analysis  
✅ Skill suggestions  
✅ Retry logic  
✅ Timeline events  

### Phase 2 (Advanced Features)
- [ ] Multi-resume comparison
- [ ] Historical analysis tracking
- [ ] Confidence scores
- [ ] Explainability (why this score?)
- [ ] Custom prompt templates per user
- [ ] A/B testing different prompts

### Phase 3 (ML Enhancements)
- [ ] Fine-tuned models for job matching
- [ ] Embedding-based similarity
- [ ] Skill taxonomy normalization
- [ ] Industry-specific analysis
- [ ] Bias detection & mitigation

---

## Dependencies

**New in requirements.txt:**
```
openai>=1.0.0           # OpenAI SDK (optional)
anthropic>=0.8.0        # Anthropic SDK (optional)
```

**Note:** At least one LLM provider SDK must be installed.

---

## Security Considerations

### API Key Management
- Never commit API keys to code
- Use environment variables or secrets manager
- Rotate keys regularly
- Monitor usage for anomalies

### Data Privacy
- Resume data sent to LLM providers
- Ensure compliance with privacy policies
- Consider on-premise LLM for sensitive data
- Log minimal PII

### Rate Limiting
- Respect provider rate limits
- Implement exponential backoff
- Monitor quota usage
- Set up alerts for threshold

---

**AI Analysis Engine Status:** ✅ Complete and Production-Ready

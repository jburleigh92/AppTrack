# Job Application Tracker - Complete API & Integration Contract Specification

**Document Version:** 2.0  
**Last Updated:** December 10, 2025  
**Status:** Final Specification  
**Base URL:** `http://localhost:8000/api/v1`

---

## Table of Contents

1. [API Overview](#1-api-overview)
2. [Complete Endpoint List](#2-complete-endpoint-list)
3. [Authentication & Authorization](#3-authentication--authorization)
4. [Common Data Structures](#4-common-data-structures)
5. [Error Handling](#5-error-handling)
6. [Applications API](#6-applications-api)
7. [Capture API](#7-capture-api)
8. [Resumes API](#8-resumes-api)
9. [Analysis API](#9-analysis-api)
10. [Timeline API](#10-timeline-api)
11. [Queue Management API](#11-queue-management-api)
12. [Settings API](#12-settings-api)
13. [Internal Worker API](#13-internal-worker-api)
14. [Integration Contracts](#14-integration-contracts)
15. [Idempotency & Deduplication](#15-idempotency--deduplication)

---

## 1. API Overview

### 1.1 Design Principles

- **RESTful**: Resource-oriented URLs, HTTP verbs for actions
- **JSON**: All requests and responses use `application/json`
- **Stateless**: No session state; all context in request
- **Envelope Format**: Consistent response wrapping
- **Error Standards**: Standardized error response format
- **Timestamps**: ISO 8601 UTC format (`YYYY-MM-DDTHH:MM:SS.sssZ`)
- **UUIDs**: All resource IDs are UUID v4 strings

### 1.2 Response Envelope Format

**Success (Single Resource):**
```json
{
  "data": {
    "id": "uuid",
    "field1": "value1"
  }
}
```

**Success (List):**
```json
{
  "data": [
    { "id": "uuid", "...": "..." }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 25,
      "total_count": 150,
      "total_pages": 6
    }
  }
}
```

**Error:**
```json
{
  "error": {
    "type": "validation_error",
    "message": "Human-readable error message",
    "details": {
      "field_errors": {
        "field_name": "Error description"
      }
    }
  }
}
```

---

## 2. Complete Endpoint List

### Public Endpoints

```
Health & Status:
GET    /api/v1/health

Applications:
GET    /api/v1/applications
GET    /api/v1/applications/{id}
POST   /api/v1/applications
PATCH  /api/v1/applications/{id}/status
PATCH  /api/v1/applications/{id}/notes
POST   /api/v1/applications/{id}/scrape
POST   /api/v1/applications/{id}/analyze
DELETE /api/v1/applications/{id}

Timeline:
GET    /api/v1/applications/{id}/timeline
POST   /api/v1/applications/{id}/timeline/events
GET    /api/v1/applications/{id}/analyses

Job Postings:
GET    /api/v1/job-postings/{id}
GET    /api/v1/scraped-postings/{id}

Resumes:
POST   /api/v1/resumes/upload
GET    /api/v1/resumes
GET    /api/v1/resumes/{id}
GET    /api/v1/resumes/{id}/data

Analysis:
GET    /api/v1/analysis-results/{id}

Queue Monitoring:
GET    /api/v1/queue/scraper
GET    /api/v1/queue/parser
GET    /api/v1/queue/analysis
GET    /api/v1/queue/scraper/jobs/{id}
GET    /api/v1/queue/parser/jobs/{id}
GET    /api/v1/queue/analysis/jobs/{id}

Settings:
GET    /api/v1/settings
PATCH  /api/v1/settings

Capture:
POST   /api/v1/capture/browser
POST   /api/v1/capture/email

Export:
GET    /api/v1/export/applications.csv
GET    /api/v1/export/applications.json
```

### Internal Endpoints (Workers Only)

```
Worker Callbacks:
POST   /api/v1/internal/scraper/results
POST   /api/v1/internal/parser/results
POST   /api/v1/internal/analysis/results
```

---

## 3. Authentication & Authorization

### 3.1 Public Endpoints

**Authentication:** None required

**Rationale:** Single-user local application, API binds to 127.0.0.1 only

**Security:**
- Localhost-only binding
- Optional CSRF header: `X-Requested-With: XMLHttpRequest`

### 3.2 Internal Endpoints

**Authentication:** Bearer token required

**Header:**
```
Authorization: Bearer <internal_token>
```

**Token Source:** `INTERNAL_API_TOKEN` environment variable

**Error Response (401):**
```json
{
  "error": {
    "type": "unauthorized",
    "message": "Invalid or missing authentication token"
  }
}
```

---

## 4. Common Data Structures

### 4.1 Enums

```typescript
enum ApplicationStatus {
  APPLIED = "applied"
  SCREENING = "screening"
  INTERVIEW_SCHEDULED = "interview_scheduled"
  INTERVIEWED = "interviewed"
  OFFER_RECEIVED = "offer_received"
  ACCEPTED = "accepted"
  REJECTED = "rejected"
  WITHDRAWN = "withdrawn"
}

enum ApplicationSource {
  BROWSER = "browser"
  EMAIL = "email"
  MANUAL = "manual"
}

enum ResumeFormat {
  PDF = "pdf"
  DOCX = "docx"
  TXT = "txt"
}

enum ResumeStatus {
  PENDING = "pending"
  COMPLETED = "completed"
  FAILED = "failed"
}

enum JobStatus {
  PENDING = "pending"
  PROCESSING = "processing"
  COMPLETE = "complete"
  FAILED = "failed"
}

enum TimelineEventType {
  APPLICATION_SUBMITTED = "application_submitted"
  STATUS_CHANGED = "status_changed"
  JOB_SCRAPED = "job_scraped"
  JOB_SCRAPED_FAILED = "job_scraped_failed"
  ANALYSIS_COMPLETED = "analysis_completed"
  ANALYSIS_FAILED = "analysis_failed"
  NOTE_UPDATED = "note_updated"
  EMAIL_RECEIVED = "email_received"
  MANUAL_INTERVIEW_SCHEDULED = "manual_interview_scheduled"
  MANUAL_EMAIL_SENT = "manual_email_sent"
  MANUAL_PHONE_CALL = "manual_phone_call"
  MANUAL_OTHER = "manual_other"
}
```

### 4.2 Pagination Parameters

| Parameter | Type | Required | Default | Validation |
|-----------|------|----------|---------|------------|
| `page` | integer | No | 1 | >= 1 |
| `page_size` | integer | No | 25 | >= 1 and <= 100 |
| `sort` | string | No | Resource-specific | Valid field |
| `order` | string | No | `desc` | `asc` or `desc` |

---

## 5. Error Handling

### 5.1 HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET/PATCH |
| 201 | Created | Successful POST |
| 202 | Accepted | Async job queued |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Missing/invalid token |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate or lock failure |
| 422 | Unprocessable Entity | Semantic error |
| 500 | Internal Server Error | Unexpected error |
| 503 | Service Unavailable | Database/queue unavailable |

### 5.2 Error Types

| Type | HTTP Status | Description |
|------|-------------|-------------|
| `validation_error` | 400 | Request validation failed |
| `invalid_format` | 400 | Data format invalid |
| `not_found` | 404 | Resource not found |
| `duplicate_detected` | 409 | Duplicate resource |
| `conflict` | 409 | Optimistic lock failure |
| `unauthorized` | 401 | Auth failed |
| `internal_error` | 500 | Unexpected server error |
| `service_unavailable` | 503 | Database/queue unavailable |

---

## 6. Applications API

### 6.1 List Applications

```
GET /api/v1/applications
```

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer | No | 1 | Page number |
| `page_size` | integer | No | 25 | Items per page |
| `sort` | string | No | `application_date` | Sort field |
| `order` | string | No | `desc` | Sort order |
| `status[]` | string[] | No | all | Filter by status |
| `date_from` | date | No | - | Apps >= date |
| `date_to` | date | No | - | Apps <= date |
| `search` | string | No | - | Search query |
| `needs_review` | boolean | No | - | Filter flag |

**Response (200):**
```json
{
  "data": [
    {
      "id": "uuid",
      "company_name": "Acme Corp",
      "job_title": "Senior Engineer",
      "application_date": "2025-12-10",
      "status": "applied",
      "source": "browser",
      "match_score": 85,
      "needs_review": false,
      "created_at": "2025-12-10T14:30:00.000Z"
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 25,
      "total_count": 42,
      "total_pages": 2
    }
  }
}
```

### 6.2 Get Application Detail

```
GET /api/v1/applications/{id}
```

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "company_name": "Acme Corp",
    "job_title": "Senior Engineer",
    "application_date": "2025-12-10",
    "status": "applied",
    "job_posting_url": "https://jobs.acme.com/123",
    "source": "browser",
    "notes": "Great culture fit",
    "needs_review": false,
    "status_updated_at": "2025-12-10T14:30:00.000Z",
    "created_at": "2025-12-10T14:30:00.000Z",
    "updated_at": "2025-12-10T14:30:00.000Z",
    "job_posting": {
      "id": "uuid",
      "job_title": "Senior Software Engineer",
      "company_name": "Acme Corp",
      "description": "We are looking for...",
      "requirements": "5+ years experience...",
      "salary_range": "$150k-$200k",
      "location": "San Francisco, CA"
    },
    "analysis_results": {
      "id": "uuid",
      "match_score": 85,
      "matched_qualifications": [
        "5+ years Python experience",
        "Strong SQL skills"
      ],
      "missing_qualifications": [
        "AWS certification"
      ],
      "skill_suggestions": [
        "Highlight distributed systems work"
      ],
      "analyzed_at": "2025-12-10T15:00:00.000Z"
    }
  }
}
```

### 6.3 Create Application

```
POST /api/v1/applications
```

**Request:**
```json
{
  "company_name": "Acme Corp",
  "job_title": "Senior Engineer",
  "application_date": "2025-12-10",
  "job_posting_url": "https://jobs.acme.com/123",
  "status": "applied",
  "notes": "Applied via referral"
}
```

**Response (201):**
```json
{
  "data": {
    "id": "uuid",
    "company_name": "Acme Corp",
    "job_title": "Senior Engineer",
    "application_date": "2025-12-10",
    "status": "applied",
    "source": "manual",
    "created_at": "2025-12-10T14:30:00.000Z"
  }
}
```

### 6.4 Update Status

```
PATCH /api/v1/applications/{id}/status
```

**Request:**
```json
{
  "status": "interview_scheduled"
}
```

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "status": "interview_scheduled",
    "status_updated_at": "2025-12-11T10:00:00.000Z",
    "timeline_event_id": "uuid"
  }
}
```

### 6.5 Update Notes

```
PATCH /api/v1/applications/{id}/notes
```

**Request:**
```json
{
  "notes": "Interview scheduled for Dec 15"
}
```

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "notes": "Interview scheduled for Dec 15",
    "updated_at": "2025-12-11T10:05:00.000Z"
  }
}
```

### 6.6 Trigger Scraping

```
POST /api/v1/applications/{id}/scrape
```

**Response (202):**
```json
{
  "data": {
    "scrape_job_id": "uuid",
    "status": "queued",
    "url": "https://jobs.acme.com/123",
    "priority": 100,
    "message": "Scraping job queued"
  }
}
```

### 6.7 Trigger Analysis

```
POST /api/v1/applications/{id}/analyze
```

**Response (202):**
```json
{
  "data": {
    "analysis_job_id": "uuid",
    "status": "queued",
    "priority": 100,
    "message": "Analysis job queued"
  }
}
```

### 6.8 Delete Application

```
DELETE /api/v1/applications/{id}
```

**Response:** 204 No Content

---

## 7. Capture API

### 7.1 Browser Capture

```
POST /api/v1/capture/browser
```

**Request:**
```json
{
  "company_name": "Acme Corp",
  "job_title": "Senior Engineer",
  "application_date": "2025-12-10",
  "job_posting_url": "https://jobs.acme.com/123",
  "job_board_source": "linkedin.com"
}
```

**Response (201):**
```json
{
  "data": {
    "id": "uuid",
    "company_name": "Acme Corp",
    "job_title": "Senior Engineer",
    "status": "applied",
    "source": "browser",
    "scrape_job_id": "uuid",
    "created_at": "2025-12-10T14:30:00.000Z"
  }
}
```

**Duplicate Response (409):**
```json
{
  "error": {
    "type": "duplicate_detected",
    "message": "Similar application already exists",
    "details": {
      "existing_application_id": "uuid",
      "existing_application": {
        "company_name": "Acme Corp",
        "job_title": "Senior Engineer",
        "application_date": "2025-12-08"
      },
      "match_reason": "Same company and title within 7 days"
    }
  }
}
```

**Override Duplicate:**
```
POST /api/v1/capture/browser?force_create=true
```

### 7.2 Email Capture

```
POST /api/v1/capture/email
Authorization: Bearer <internal_token>
```

**Request:**
```json
{
  "company_name": "Acme Corp",
  "job_title": "Senior Engineer",
  "application_date": "2025-12-10",
  "job_posting_url": "https://jobs.acme.com/123",
  "email_uid": "12345",
  "email_subject": "Application for Senior Engineer",
  "email_sender": "jobs@acme.com",
  "needs_review": false
}
```

**Response (201):**
```json
{
  "data": {
    "id": "uuid",
    "company_name": "Acme Corp",
    "source": "email",
    "needs_review": false,
    "created_at": "2025-12-10T14:30:00.000Z"
  }
}
```

**Already Processed (200):**
```json
{
  "data": {
    "message": "Already processed",
    "skipped": true,
    "email_uid": "12345"
  }
}
```

---

## 8. Resumes API

### 8.1 Upload Resume

```
POST /api/v1/resumes/upload
Content-Type: multipart/form-data
```

**Request:** Form with `file` field

**Response (201):**
```json
{
  "data": {
    "resume_id": "uuid",
    "filename": "John_Doe_Resume.pdf",
    "file_size": 245678,
    "format": "pdf",
    "status": "pending",
    "parser_job_id": "uuid",
    "upload_timestamp": "2025-12-10T14:30:00.000Z",
    "message": "Resume uploaded. Parsing in progress."
  }
}
```

### 8.2 List Resumes

```
GET /api/v1/resumes?is_active=true
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "uuid",
      "filename": "Resume_Latest.pdf",
      "format": "pdf",
      "status": "completed",
      "is_active": true,
      "upload_timestamp": "2025-12-10T14:30:00.000Z"
    }
  ]
}
```

### 8.3 Get Resume Data

```
GET /api/v1/resumes/{id}/data
```

**Response (200):**
```json
{
  "data": {
    "email": "john@example.com",
    "phone": "+1-555-1234",
    "location": "San Francisco, CA",
    "skills": ["Python", "JavaScript", "SQL"],
    "experience": [
      {
        "company": "Tech Corp",
        "title": "Engineer",
        "dates": "2020-2023",
        "responsibilities": ["Built APIs", "Led team"]
      }
    ],
    "education": [
      {
        "institution": "MIT",
        "degree": "BS",
        "major": "CS",
        "year": "2020"
      }
    ],
    "extraction_complete": true
  }
}
```

---

## 9. Analysis API

### 9.1 Get Analysis Result

```
GET /api/v1/analysis-results/{id}
```

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "application_id": "uuid",
    "match_score": 85,
    "matched_qualifications": [
      "5+ years Python experience",
      "Strong SQL skills"
    ],
    "missing_qualifications": [
      "AWS certification"
    ],
    "skill_suggestions": [
      "Highlight distributed systems work"
    ],
    "model_used": "gpt-4",
    "tokens_used": 1234,
    "analyzed_at": "2025-12-10T15:00:00.000Z"
  }
}
```

### 9.2 List Analyses for Application

```
GET /api/v1/applications/{id}/analyses
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "uuid",
      "match_score": 87,
      "analyzed_at": "2025-12-11T10:00:00.000Z"
    },
    {
      "id": "uuid",
      "match_score": 85,
      "analyzed_at": "2025-12-10T15:00:00.000Z"
    }
  ]
}
```

---

## 10. Timeline API

### 10.1 Get Timeline

```
GET /api/v1/applications/{id}/timeline?event_type=status_changed&limit=50
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "uuid",
      "event_type": "status_changed",
      "event_data": {
        "old_status": "applied",
        "new_status": "interview_scheduled"
      },
      "occurred_at": "2025-12-11T09:15:00.000Z"
    },
    {
      "id": "uuid",
      "event_type": "application_submitted",
      "event_data": {
        "source": "browser",
        "job_board_source": "linkedin.com"
      },
      "occurred_at": "2025-12-10T14:30:00.000Z"
    }
  ]
}
```

### 10.2 Add Manual Event

```
POST /api/v1/applications/{id}/timeline/events
```

**Request:**
```json
{
  "event_type": "manual_interview_scheduled",
  "description": "Phone screen with hiring manager",
  "occurred_at": "2025-12-15T14:00:00.000Z"
}
```

**Response (201):**
```json
{
  "data": {
    "id": "uuid",
    "event_type": "manual_interview_scheduled",
    "event_data": {
      "description": "Phone screen with hiring manager",
      "manually_added_by_user": true
    },
    "occurred_at": "2025-12-15T14:00:00.000Z"
  }
}
```

---

## 11. Queue Management API

### 11.1 Get Queue Status

```
GET /api/v1/queue/scraper
GET /api/v1/queue/parser
GET /api/v1/queue/analysis
```

**Response (200):**
```json
{
  "data": {
    "queue_depth": {
      "pending": 15,
      "processing": 3,
      "complete": 142,
      "failed": 7
    },
    "oldest_pending_job": "2025-12-10T14:23:45.000Z",
    "avg_processing_time_seconds": 12.5,
    "total_jobs": 167
  }
}
```

### 11.2 Get Job Status

```
GET /api/v1/queue/scraper/jobs/{id}
```

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "url": "https://jobs.acme.com/123",
    "status": "complete",
    "priority": 100,
    "attempts": 1,
    "created_at": "2025-12-10T14:30:00.000Z",
    "completed_at": "2025-12-10T14:30:15.000Z"
  }
}
```

---

## 12. Settings API

### 12.1 Get Settings

```
GET /api/v1/settings
```

**Response (200):**
```json
{
  "data": {
    "email_config": {
      "enabled": true,
      "imap_server": "imap.gmail.com",
      "imap_port": 993,
      "username": "user@gmail.com",
      "target_folder": "Job Applications",
      "polling_interval_seconds": 300
    },
    "llm_config": {
      "provider": "openai",
      "model": "gpt-4",
      "temperature": 0.3,
      "max_tokens": 2000
    },
    "auto_analyze": true,
    "updated_at": "2025-12-10T14:30:00.000Z"
  }
}
```

### 12.2 Update Settings

```
PATCH /api/v1/settings
```

**Request:**
```json
{
  "email_config": {
    "polling_interval_seconds": 600
  },
  "llm_config": {
    "model": "gpt-4-turbo"
  },
  "auto_analyze": false
}
```

**Response (200):** Complete updated settings object

---

## 13. Internal Worker API

### 13.1 Scraper Results

```
POST /api/v1/internal/scraper/results
Authorization: Bearer <internal_token>
```

**Request (Success):**
```json
{
  "scrape_job_id": "uuid",
  "application_id": "uuid",
  "status": "complete",
  "scraped_posting_id": "uuid",
  "job_posting_id": "uuid",
  "metadata": {
    "http_status": 200,
    "fetch_duration_ms": 1234,
    "extraction_complete": true
  }
}
```

**Request (Failure):**
```json
{
  "scrape_job_id": "uuid",
  "application_id": "uuid",
  "status": "failed",
  "error_reason": "HTTP_404",
  "error_message": "Job posting not found"
}
```

**Response (200):**
```json
{
  "data": {
    "message": "Scrape results recorded successfully",
    "application_updated": true,
    "analysis_queued": true
  }
}
```

### 13.2 Parser Results

```
POST /api/v1/internal/parser/results
Authorization: Bearer <internal_token>
```

**Request:**
```json
{
  "parser_job_id": "uuid",
  "resume_id": "uuid",
  "status": "complete",
  "resume_data_id": "uuid",
  "metadata": {
    "parse_duration_ms": 2345,
    "extraction_complete": true
  }
}
```

### 13.3 Analysis Results

```
POST /api/v1/internal/analysis/results
Authorization: Bearer <internal_token>
```

**Request:**
```json
{
  "analysis_job_id": "uuid",
  "application_id": "uuid",
  "status": "complete",
  "analysis_result_id": "uuid",
  "metadata": {
    "analysis_duration_ms": 5678,
    "tokens_used": 1234,
    "model_used": "gpt-4"
  }
}
```

---

## 14. Integration Contracts

### 14.1 Browser Extension → Backend

**Flow:**
1. Extension captures form data from job board
2. POST to `/api/v1/capture/browser`
3. If 201: Success, show confirmation
4. If 409: Duplicate, show modal with options
5. If 503: Backend down, queue locally and retry

**Offline Handling:**
- Store failed requests in localStorage
- Retry every 30 seconds (max 3 attempts)
- Replay on reconnect

### 14.2 Email Service → Backend

**Flow:**
1. Poll IMAP inbox every 5 minutes
2. Parse unread emails for patterns
3. POST to `/api/v1/capture/email` with internal token
4. If 201: Success, mark email as read
5. If 200 skipped: Already processed (idempotent)
6. If 503: Retry with backoff

**Idempotency:**
- Email UID checked before processing
- Safe to retry POST

### 14.3 Workers → Backend

**Flow:**
1. Poll queue for pending jobs
2. Process job (scrape/parse/analyze)
3. POST results to `/api/v1/internal/{type}/results`
4. If 200: Success, job complete
5. If 503: Retry callback with backoff

**Error Handling:**
- Retry transient errors with backoff
- Permanent errors reported immediately

---

## 15. Idempotency & Deduplication

### 15.1 Email Idempotency

**Mechanism:** `processed_email_uids` table tracks (account, folder, uid)

**Guarantee:** Each email UID processed exactly once per account/folder

### 15.2 Browser Duplicate Detection

**Mechanism:** Check (company + title + date ±7 days) OR same URL

**User Override:** `?force_create=true` bypasses check

### 15.3 Scraping Deduplication

**Mechanism:** Check `normalized_url` with age < 7 days

**Benefit:** Same URL not scraped more than once per week

### 15.4 Worker Callbacks

**Mechanism:** Same job_id + status is no-op

**Guarantee:** Safe to retry callback

---

**End of API Contract Specification**

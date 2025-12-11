# Job Application Tracker - Non-Functional Requirements Specification

**Document Version:** 1.0  
**Last Updated:** December 10, 2025  
**System Type:** Single-User Desktop Application  
**Deployment Model:** Local-Only, On-Premises

---

## 1. Performance Requirements

### 1.1 Response Time Requirements

**PERF-001: Browser Extension Response Time**
- Browser extension popup MUST render within 500ms of icon click under normal system load
- Form submission detection MUST trigger within 200ms of submission event
- Confirmation modal MUST display within 2000ms of form submission detection
- Modal interaction (Confirm/Cancel) MUST complete within 1000ms

**PERF-002: Dashboard Response Time**
- Application list view MUST load and render within 2000ms for datasets up to 1,000 applications
- Application list view MUST load and render within 5000ms for datasets between 1,000 and 5,000 applications
- Application detail view MUST load within 1500ms regardless of linked data volume
- Search operations MUST return results within 1000ms for datasets up to 5,000 applications
- Filter operations MUST apply within 800ms
- Sort operations MUST complete within 500ms

**PERF-003: Backend API Response Time**
- REST API endpoints MUST respond within 500ms for simple CRUD operations (95th percentile)
- Complex aggregation queries (dashboard statistics) MUST respond within 2000ms (95th percentile)
- Export generation MUST complete within 5000ms for datasets up to 1,000 applications
- Export generation MUST complete within 30,000ms for datasets up to 5,000 applications

**PERF-004: Email Polling Response Time**
- Email polling cycle MUST complete within 30 seconds under normal conditions
- Email parsing MUST process individual email within 2000ms
- Batch email processing (multiple unread emails) MUST process at minimum 5 emails per minute

### 1.2 Throughput Requirements

**PERF-005: Web Scraping Throughput**
- Scraping subsystem MUST support minimum 10 concurrent scrape requests per domain per minute
- Scraping subsystem MUST process minimum 50 URLs per hour across all domains
- Individual scrape request timeout MUST NOT exceed 30 seconds
- Scraping queue MUST support minimum 100 pending URLs without performance degradation

**PERF-006: AI Analysis Throughput**
- AI analysis subsystem MUST support minimum 10 analyses per hour (accounting for API rate limits)
- AI analysis queue MUST support minimum 50 pending analysis jobs
- Individual analysis request timeout MUST NOT exceed 60 seconds
- Batch analysis (user-triggered for multiple applications) MUST process minimum 5 analyses concurrently

**PERF-007: Data Ingestion Throughput**
- Browser capture MUST support capturing 1 application per minute sustainably
- Email ingestion MUST process minimum 20 confirmation emails per polling cycle
- Manual application entry MUST support data entry and save within 5000ms per application

### 1.3 Concurrency Requirements

**PERF-008: Asynchronous Task Execution**
- System MUST support minimum 5 concurrent web scraping tasks
- System MUST support minimum 3 concurrent AI analysis tasks
- System MUST support minimum 2 concurrent email polling operations (if multiple accounts configured)
- Background tasks MUST NOT block UI responsiveness (UI thread isolation required)

**PERF-009: Database Concurrency**
- Database MUST support minimum 10 concurrent read operations without lock contention
- Database MUST support minimum 5 concurrent write operations with serializable isolation
- Long-running queries (exports, aggregations) MUST NOT block transactional operations

### 1.4 Resource Efficiency Requirements

**PERF-010: Memory Usage**
- Browser extension MUST consume less than 100MB RAM under normal operation
- Backend service MUST consume less than 500MB RAM with dataset of 1,000 applications
- Backend service MUST consume less than 2GB RAM with dataset of 5,000 applications
- Dashboard UI MUST consume less than 300MB RAM per browser tab

**PERF-011: CPU Usage**
- Backend service MUST maintain average CPU utilization below 10% during idle state
- Scraping operations MUST maintain average CPU utilization below 30% during active scraping
- AI analysis operations MUST maintain average CPU utilization below 40% during active analysis
- Database operations MUST maintain average CPU utilization below 20% during normal query load

**PERF-012: Disk I/O**
- Database write operations MUST NOT exceed 10MB/s sustained write rate
- HTML storage MUST NOT exceed 5MB per stored job posting
- Resume file storage MUST NOT exceed 10MB per resume file
- Log file rotation MUST occur at 100MB size limit per log file

### 1.5 Scalability Limits (Single-User Context)

**PERF-013: Dataset Size Limits**
- System MUST support minimum 5,000 application records with acceptable performance (as defined in PERF-002)
- System MUST support minimum 10,000 scraped job posting records
- System MUST support minimum 5,000 AI analysis results
- System MUST support minimum 50,000 timeline events
- System SHOULD gracefully degrade performance beyond these limits rather than fail catastrophically

**PERF-014: Polling Intervals**
- Email polling interval MUST default to 300 seconds (5 minutes)
- Email polling interval MUST be user-configurable between 60 seconds (1 minute) and 3600 seconds (1 hour)
- Scraping queue processing interval MUST default to 10 seconds
- Failed task retry check interval MUST default to 60 seconds

---

## 2. Reliability & Fault Tolerance Requirements

### 2.1 Retry Policies

**REL-001: Web Scraping Retry Policy**
- Failed scrape requests MUST retry automatically with exponential backoff: 1 minute, 5 minutes, 15 minutes
- Maximum retry attempts MUST be 3 before marking scrape as permanently failed
- Transient errors (timeouts, 5xx responses) MUST trigger retry logic
- Permanent errors (404, 403, 401) MUST NOT trigger retry logic
- Retry attempts MUST be logged with failure reason and attempt number

**REL-002: AI Analysis Retry Policy**
- Failed API requests due to rate limiting (429) MUST retry with exponential backoff: 1 minute, 5 minutes, 15 minutes
- Failed API requests due to timeout MUST retry once after 10 seconds
- Failed API requests due to server errors (5xx) MUST retry with exponential backoff: 1 minute, 5 minutes
- Maximum retry attempts MUST be 3 before marking analysis as permanently failed
- Invalid API key errors (401, 403) MUST NOT trigger retry and MUST notify user immediately

**REL-003: Email Polling Retry Policy**
- Failed IMAP connections MUST retry on next scheduled polling interval (no immediate retry)
- Authentication failures MUST NOT trigger automatic retry and MUST notify user
- Network timeout during polling MUST abandon current cycle and retry on next interval
- Partial email processing failures MUST NOT halt entire polling cycle

**REL-004: Browser Extension Retry Policy**
- Failed backend communication MUST retry once after 5 seconds
- After second failure, extension MUST offer "Save for Later" option to persist data locally
- Locally stored data MUST sync automatically on next successful backend connection
- Maximum locally stored pending submissions MUST be 50 before warning user

### 2.2 Backoff Strategies

**REL-005: Exponential Backoff Implementation**
- Exponential backoff MUST use formula: wait_time = base_delay * (2 ^ attempt_number) with jitter
- Jitter MUST be randomized between 0-20% of calculated wait time to prevent thundering herd
- Maximum backoff delay MUST NOT exceed 1 hour regardless of attempt number
- Backoff state MUST persist across application restarts for background tasks

**REL-006: Rate Limit Backoff**
- Rate limit backoff for web scraping MUST use per-domain cooldown periods
- Rate limit backoff for AI API MUST respect Retry-After header if provided
- System MUST maintain rate limit state in memory with 1-hour expiration
- Rate limit violations MUST NOT result in data loss; requests MUST be queued

### 2.3 Safe Degradation Modes

**REL-007: Component Failure Isolation**
- Web scraping failures MUST NOT prevent application record creation
- AI analysis failures MUST NOT prevent application record viewing or editing
- Email ingestion failures MUST NOT impact browser capture functionality
- Dashboard unavailability MUST NOT impact background task execution (scraping, polling, analysis)

**REL-008: Partial Data Degradation**
- Applications with failed scrapes MUST display with available metadata and clear indication of scraping failure
- Applications with failed analysis MUST display without analysis results and offer manual retry option
- Job postings with partial extraction MUST store available fields and mark extraction as incomplete
- Resumes with partial parsing MUST store raw text as fallback and mark parsing as incomplete

**REL-009: Network Outage Behavior**
- System MUST continue to accept manual application entries during network outage
- Browser extension MUST queue captured applications locally when backend unavailable
- Email polling MUST suspend during outage and resume automatically on connectivity restoration
- User MUST be notified of degraded functionality with clear status indicators

### 2.4 Data Durability Requirements

**REL-010: Database Durability**
- Database MUST enforce ACID properties for all transactional operations
- Write-ahead logging (WAL) MUST be enabled for PostgreSQL or equivalent mechanism for other databases
- Database MUST fsync writes to disk before transaction commit
- Database backup MUST be user-triggerable via UI or CLI command

**REL-011: Data Loss Prevention**
- Application records MUST be written to database before confirming success to user
- Browser extension local storage MUST persist captured data until confirmed delivered to backend
- Email processing MUST NOT mark emails as read until application record persisted
- Export operations MUST write to temporary file before moving to final location (atomic operation)

**REL-012: Crash Recovery**
- System MUST recover gracefully from unexpected shutdown without data corruption
- In-progress scraping tasks MUST resume from queue on restart
- In-progress analysis tasks MUST resume from queue on restart
- Database connections MUST be released cleanly on shutdown or recover on restart

**REL-013: Data Integrity Validation**
- Database foreign key constraints MUST be enforced at all times
- Application record updates MUST validate required fields before persistence
- Concurrent updates to same record MUST use optimistic locking (updated_at timestamp check)
- Data import/export operations MUST validate schema compatibility

---

## 3. Security Requirements

### 3.1 Credential and Secrets Management

**SEC-001: Email Credentials Storage**
- Email IMAP credentials MUST be encrypted at rest using AES-256 or equivalent
- Encryption keys MUST be derived from system-level keychain/credential store (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- Credentials MUST NOT be stored in plaintext in configuration files
- Credentials MUST NOT be logged in any circumstance, including debug logs
- Credential decryption MUST occur only in memory at time of use and MUST NOT persist in memory after use

**SEC-002: API Key Protection**
- LLM API keys MUST be encrypted at rest using AES-256 or equivalent
- API keys MUST be stored using same secure mechanism as email credentials (system keychain)
- API keys MUST NOT be transmitted to any service except the configured LLM provider
- API keys MUST NOT appear in error messages, logs, or exports
- API key validation MUST occur on configuration save with clear success/failure feedback

**SEC-003: Browser Extension Permissions**
- Extension MUST request minimum permissions: activeTab, storage, host permissions for monitored job boards only
- Extension MUST NOT request broad host permissions (e.g., <all_urls>) unless explicitly justified
- Extension MUST declare all requested permissions in manifest with user-visible justification
- Extension content scripts MUST run only on declared job board domains
- Extension MUST NOT access browsing history beyond current active tab

### 3.2 Data Protection

**SEC-004: Local Storage Security**
- Database files MUST have file system permissions restricted to owner (user) only (chmod 600 or equivalent)
- Configuration files MUST have file system permissions restricted to owner only
- Log files MUST have file system permissions restricted to owner only
- Resume files MUST be stored in user-private directory with restricted permissions
- Exported data files MUST have owner-only permissions by default

**SEC-005: Encryption in Transit**
- All HTTPS connections (web scraping, API calls) MUST validate SSL/TLS certificates
- Certificate validation MUST NOT be bypassable by user configuration
- Minimum TLS version MUST be 1.2
- IMAP connections MUST use SSL/TLS (IMAPS on port 993) or STARTTLS
- Backend-to-frontend communication MUST use localhost-only binding (no network exposure)

**SEC-006: Sensitive Data Handling**
- Resume content containing PII (email, phone, address) MUST be stored in database with access controls
- Job posting HTML snapshots MUST be stored separately from structured data with purge capability
- Email content MUST be stored with subject and sender only; full email body optional and user-configurable
- Data deletion (soft or hard delete) MUST be permanent and irrecoverable for hard deletes
- System MUST provide clear documentation on what data is stored and where

### 3.3 Input Validation and Injection Prevention

**SEC-007: SQL Injection Prevention**
- All database queries MUST use parameterized queries or prepared statements
- String concatenation for SQL query construction MUST NOT be used
- User-provided input MUST NOT be directly interpolated into SQL queries
- ORM frameworks MUST be configured to prevent SQL injection by default

**SEC-008: Command Injection Prevention**
- System MUST NOT execute shell commands with user-provided input
- If external commands required (e.g., PDF processing), input MUST be validated against strict whitelist
- File paths provided by user MUST be validated and sanitized
- Uploaded filenames MUST be sanitized and not used directly in file system operations

**SEC-009: Cross-Site Scripting (XSS) Prevention**
- Dashboard UI MUST sanitize all user-provided content before rendering
- Job descriptions and notes MUST be escaped when displayed in HTML context
- Markdown rendering MUST use safe renderer with HTML tag stripping
- Content Security Policy (CSP) MUST be implemented for dashboard web interface

### 3.4 Authentication and Authorization

**SEC-010: Local Access Control**
- Backend service MUST bind only to localhost (127.0.0.1) and MUST NOT be accessible from network
- Backend service MUST use random port assignment or user-configured port with validation
- Browser extension MUST authenticate to backend using locally generated token stored securely
- Dashboard access MUST NOT require user authentication (single-user assumption) but MUST validate origin

**SEC-011: Browser Extension Security**
- Extension MUST validate backend service identity before sending captured data
- Extension MUST use Content Security Policy to prevent code injection
- Extension MUST NOT execute eval() or similar dynamic code execution
- Extension MUST NOT load external JavaScript libraries from CDNs at runtime

---

## 4. Privacy Requirements

### 4.1 Local-Only Data Constraints

**PRIV-001: No Cloud Transmission**
- All application data, resumes, job postings, and analysis results MUST remain on user's local machine
- System MUST NOT transmit user data to any service except:
  - Configured LLM API provider (for analysis only)
  - IMAP servers (for email retrieval only)
  - Job posting URLs (for scraping only)
- System MUST NOT include telemetry, analytics, or crash reporting that transmits user data
- System MUST NOT phone home to vendor servers for any purpose

**PRIV-002: Third-Party Data Sharing**
- LLM API providers MUST receive only: resume content, job posting content, and analysis request
- LLM API providers MUST NOT receive: application status, timeline events, personal notes, email addresses, or identifiable metadata
- Web scraping MUST NOT transmit user identity or application tracking data to scraped sites
- Email servers MUST receive only standard IMAP authentication and retrieval requests

### 4.2 Data Retention and Deletion

**PRIV-003: User-Controlled Retention**
- System MUST provide user-configurable retention policies for:
  - Scraped job posting HTML (default: retain indefinitely, option to purge after 90 days)
  - Timeline events (default: retain indefinitely, option to purge after 1 year)
  - Email content (default: subject and sender only, option to store full body or none)
- System MUST provide "Delete All Data" function that permanently removes all application records, job postings, resumes, and analysis results
- Soft-deleted records MUST be permanently purged after user-configurable period (default: 30 days)

**PRIV-004: Resume Data Retention**
- Resume files MUST be retained indefinitely by default
- System MUST provide option to delete uploaded resume files while retaining extracted structured data
- System MUST provide option to delete all resume data (files and extracted data)
- Archived resumes MUST be user-deletable independently of active resume

### 4.3 Opt-In and Consent

**PRIV-005: Browser Capture Consent**
- Browser extension MUST display first-run consent prompt explaining data capture behavior
- Extension MUST provide easily accessible disable/enable toggle in popup UI
- Extension MUST respect user disable state and NOT capture applications when disabled
- Extension MUST allow per-site opt-out (e.g., disable capture for specific job board)

**PRIV-006: Email Monitoring Consent**
- Email ingestion setup MUST display clear explanation of what emails will be accessed and processed
- Email monitoring MUST be opt-in only; NOT enabled by default
- System MUST provide easy disable mechanism for email monitoring
- System MUST allow user to revoke email credentials without data loss

**PRIV-007: AI Analysis Consent**
- System MUST inform user that resume and job posting content will be sent to third-party LLM provider
- AI analysis MUST be opt-in per application or globally configurable
- System MUST display LLM provider name and link to provider's privacy policy
- System MUST allow user to delete analysis results independently of application records

### 4.4 Anonymization and Redaction

**PRIV-008: PII Redaction (Optional)**
- System SHOULD provide optional PII redaction for resume content before AI analysis:
  - Email addresses replaced with [EMAIL]
  - Phone numbers replaced with [PHONE]
  - Street addresses replaced with [ADDRESS]
  - Full name optionally replaced with [NAME]
- Redaction MUST be user-configurable (on/off per field type)
- Redacted data MUST NOT affect resume section identification or skill extraction
- Original unredacted resume MUST be retained for user reference

**PRIV-009: Export Privacy**
- Exports MUST include warning when exporting data containing PII
- Exports MUST provide option to exclude sensitive fields:
  - Email addresses
  - Phone numbers
  - Full resume content
  - Email body content
- Export files MUST be named with clear indication of content type

---

## 5. Maintainability & Extensibility Requirements

### 5.1 Modular Architecture

**MAINT-001: Component Isolation**
- System MUST be organized into clearly separated modules:
  - Browser Extension (independent deployment)
  - Backend API Service (RESTful interface)
  - Email Ingestion Service (independent process)
  - Web Scraping Service (independent process or thread pool)
  - AI Analysis Service (independent process or thread pool)
  - Database Layer (abstraction over persistence)
  - Dashboard UI (independent frontend application)
- Modules MUST communicate via well-defined interfaces (REST API, message queue, or IPC)
- Module failures MUST NOT cascade to other modules (circuit breaker pattern)

**MAINT-002: Service Boundaries**
- Each service MUST have single, well-defined responsibility
- Services MUST NOT directly access other services' data stores
- Cross-service data access MUST occur through APIs only
- Services MUST be independently startable and stoppable without affecting others (except database dependency)

### 5.2 Extensibility Points

**MAINT-003: Job Board Adapter Pattern**
- Web scraping module MUST support pluggable job board adapters
- New job board support MUST be addable via configuration or code without modifying core scraping logic
- Each adapter MUST implement standard interface:
  - detectJobBoard(url) → boolean
  - extractMetadata(html) → structured_data
  - extractJobPosting(html) → job_data
- Adapter registry MUST be extensible at runtime or configuration time

**MAINT-004: LLM Provider Abstraction**
- AI analysis module MUST support pluggable LLM provider adapters
- Provider adapters MUST implement standard interface:
  - constructPrompt(resume, job) → prompt
  - callAPI(prompt, config) → response
  - parseResponse(response) → analysis_result
- Provider switch MUST be configurable without code changes (configuration file)
- Multiple providers MUST be supported with user-selectable default

**MAINT-005: Resume Parser Extensibility**
- Resume parsing MUST support pluggable format handlers
- New format support (e.g., ODT, RTF) MUST be addable without core logic changes
- Format handlers MUST implement standard interface:
  - canHandle(file_path) → boolean
  - extractText(file_path) → plain_text
- Handler registry MUST be automatically discoverable (e.g., via naming convention or decorator)

**MAINT-006: Email Parser Extensibility**
- Email confirmation detection MUST support pluggable pattern matchers
- New email patterns MUST be addable via configuration (regex or keyword lists)
- Custom parsers MUST be pluggable for company-specific email formats
- Parser priority MUST be configurable to prefer custom parsers over generic ones

### 5.3 Configuration Management

**MAINT-007: Externalized Configuration**
- All environment-specific settings MUST be externalized to configuration files
- Configuration MUST support multiple formats: JSON, YAML, or TOML
- Configuration changes MUST NOT require code recompilation
- Configuration schema MUST be documented and validated on load
- Configuration MUST support environment variable overrides for sensitive values

**MAINT-008: Feature Flags**
- New or experimental features MUST be guarded by feature flags
- Feature flags MUST be user-configurable (UI settings or config file)
- Feature flags MUST default to off for breaking or experimental changes
- Feature flag state MUST be logged on application startup

### 5.4 Logging and Observability

**MAINT-009: Structured Logging**
- All services MUST implement structured logging (JSON format preferred)
- Log entries MUST include:
  - Timestamp (ISO 8601 format with timezone)
  - Log level (DEBUG, INFO, WARN, ERROR, FATAL)
  - Component/service identifier
  - Message
  - Structured context fields (e.g., application_id, user_action)
- Logs MUST NOT contain sensitive data (credentials, API keys, full resume content, email passwords)

**MAINT-010: Log Levels and Verbosity**
- System MUST support configurable log levels per component
- Default log level MUST be INFO for production use
- DEBUG level MUST be enableable without restart (via configuration reload or signal)
- Log rotation MUST occur automatically at 100MB file size with 10 file retention

**MAINT-011: Error Tracking**
- All exceptions MUST be logged with full stack traces at ERROR level
- Critical errors (data loss, corruption) MUST be logged at FATAL level
- User-facing errors MUST be correlated with backend log entries via request ID or error ID
- Errors MUST include contextual information (component, operation, affected resource)

**MAINT-012: Operational Metrics**
- System MUST expose operational metrics:
  - Scraping: success rate, failure rate, average latency, queue depth
  - AI Analysis: success rate, failure rate, average latency, API cost per analysis
  - Email Ingestion: emails processed per cycle, parse success rate
  - Database: query latency (p50, p95, p99), connection pool utilization
- Metrics MUST be accessible via log files or local metrics endpoint (e.g., Prometheus format)
- Metrics MUST be retained for minimum 7 days

**MAINT-013: Audit Logging**
- Key user actions MUST be logged to audit log:
  - Application creation (manual, browser, email)
  - Application deletion
  - Status changes
  - Resume uploads
  - Configuration changes (email setup, API keys)
- Audit log entries MUST be tamper-evident (append-only, checksummed)
- Audit logs MUST be retained for minimum 90 days

### 5.5 Code Quality and Documentation

**MAINT-014: Code Documentation**
- All public APIs (REST endpoints, service interfaces) MUST be documented with OpenAPI/Swagger or equivalent
- All configuration options MUST be documented with examples
- All pluggable interfaces (adapters, parsers) MUST have implementation guides
- Installation and deployment procedures MUST be documented with troubleshooting guides

**MAINT-015: Dependency Management**
- All dependencies MUST be explicitly versioned (no "latest" tags)
- Dependency versions MUST be locked (requirements.txt, package-lock.json, or equivalent)
- Security vulnerability scanning MUST be performed on dependencies (manual or automated)
- Deprecated dependencies MUST be documented with migration paths

---

## 6. Scalability Requirements (Single-User Context)

### 6.1 Data Volume Limits

**SCALE-001: Maximum Dataset Sizes**
- System MUST support minimum 5,000 application records without performance degradation below PERF-002 thresholds
- System MUST support minimum 10,000 scraped job posting records with HTML snapshots (assuming 2MB average size = 20GB storage)
- System MUST support minimum 5,000 AI analysis results
- System MUST support minimum 50,000 timeline events
- System SHOULD provide warnings when approaching 80% of tested limits

**SCALE-002: Storage Growth Management**
- Database growth rate MUST NOT exceed 10MB per 100 applications (excluding HTML snapshots)
- HTML snapshot storage MUST be user-purgeable without affecting application records
- System MUST provide storage usage dashboard showing breakdown by data type
- System MUST warn user when storage exceeds 10GB total usage

### 6.2 Task Queue Limits

**SCALE-003: Queue Depth Limits**
- Scraping queue MUST support minimum 500 pending URLs
- AI analysis queue MUST support minimum 200 pending analysis jobs
- Email processing queue MUST support minimum 100 pending emails
- Queues exceeding 80% capacity MUST log warnings
- Queues at 100% capacity MUST reject new items with clear error messages

**SCALE-004: Concurrent Task Limits**
- System MUST limit concurrent scraping tasks to maximum 10 to prevent resource exhaustion
- System MUST limit concurrent AI analysis tasks to maximum 5 to prevent API rate limit violations
- System MUST limit concurrent database write transactions to maximum 10 to prevent lock contention
- Limits MUST be user-configurable within safe bounds (1-20 for scraping, 1-10 for analysis)

### 6.3 Performance Degradation Thresholds

**SCALE-005: Graceful Degradation**
- When application count exceeds 5,000:
  - Dashboard list view pagination MUST reduce default page size from 25 to 10
  - Search operations MAY take up to 3000ms (degraded from 1000ms)
  - Statistics calculations MAY be cached with 5-minute TTL
- When scraping queue exceeds 100 items:
  - New scrape requests MAY be delayed up to 5 minutes before processing
  - User MUST be notified of queue backlog
- When analysis queue exceeds 50 items:
  - New analysis requests MAY be delayed up to 10 minutes before processing
  - User MUST be notified of queue backlog

---

## 7. Usability Requirements

### 7.1 Error Messages and User Feedback

**USE-001: Error Message Quality**
- All error messages MUST be written in plain language avoiding technical jargon
- Error messages MUST include:
  - Clear description of what went wrong
  - Reason for failure (if known)
  - Actionable remediation steps
- Examples:
  - GOOD: "Could not connect to email server. Please check your internet connection and verify IMAP settings."
  - BAD: "IMAP connection failed: socket.timeout"
- Technical details MUST be available in expandable "More Info" section, not in primary message

**USE-002: Error Context and Recovery**
- Errors MUST provide context about the operation being performed
- Errors MUST include relevant identifiers (application name, job title) when applicable
- Errors MUST offer recovery options:
  - Retry button for transient failures
  - Edit button for input validation failures
  - Help/Documentation link for configuration errors
- Errors MUST NOT result in silent failures; user MUST be notified

**USE-003: Success Feedback**
- Successful operations MUST provide clear confirmation:
  - Application captured: "Application for [Job Title] at [Company] saved successfully"
  - Analysis completed: "Analysis complete: [Match Score]% match"
  - Export completed: "Export complete: [Count] applications exported"
- Success messages MUST auto-dismiss after 5 seconds or be manually dismissible
- Success messages MUST be visually distinct from error messages (color, icon)

### 7.2 Progress Indicators and Status

**USE-004: Long-Running Operation Indicators**
- Operations exceeding 2 seconds MUST display progress indicator
- Progress indicators MUST show:
  - Operation description ("Scraping job posting...")
  - Progress percentage when determinable
  - Estimated time remaining when determinable
  - Cancel option for user-triggered operations
- Indeterminate operations (unknown duration) MUST display animated spinner

**USE-005: Background Task Status**
- Dashboard MUST display status of background tasks:
  - Email polling: Last check time, next check time, status (active/paused/error)
  - Scraping queue: Number of pending scrapes, currently scraping
  - Analysis queue: Number of pending analyses, currently analyzing
- Status indicators MUST be real-time or near-real-time (update interval < 5 seconds)
- Failed background tasks MUST display failure count and error summary

**USE-006: Sync and Data Freshness Indicators**
- Application list MUST display last refresh timestamp
- Manual refresh button MUST be available and clearly labeled
- Stale data (not refreshed in > 5 minutes) SHOULD display visual indicator
- Browser extension MUST indicate connection status to backend (connected/disconnected)

### 7.3 Fallback UX for Automation Failures

**USE-007: Failed Extraction Fallbacks**
- When browser capture extraction fails:
  - Pre-fill form with "Unknown Company" and "Unknown Position"
  - Provide clear instructions: "Could not extract details automatically. Please enter manually."
  - All fields MUST be editable
- When email parsing fails:
  - Display email subject and sender
  - Provide "Extract Manually" button opening editable form pre-filled with available data
- When job posting scraping fails:
  - Display reason for failure (404, timeout, etc.)
  - Provide "Retry" button
  - Provide "Paste Job Description" text area for manual entry

**USE-008: Missing Data Handling**
- Missing optional fields MUST display as "Not provided" or "Not available" rather than blank
- Missing critical fields MUST display placeholder with call-to-action: "Add company name"
- Applications with incomplete data MUST be visually tagged (e.g., "⚠️ Incomplete" badge)
- Bulk actions MUST allow filtering for incomplete applications for easy cleanup

**USE-009: Empty States**
- Dashboard with zero applications MUST display onboarding message:
  - Welcome message
  - Quick start guide (install extension, set up email, add first application)
  - Visual illustration or tutorial video link
- Lists with zero results (after filtering) MUST display: "No applications match your filters. Try adjusting filters or clearing them."
- Search with zero results MUST display: "No applications found matching '[query]'. Try different keywords."

### 7.4 Accessibility and Responsiveness

**USE-010: Keyboard Navigation**
- All interactive elements MUST be keyboard-accessible (tab navigation)
- Keyboard shortcuts MUST be documented and discoverable
- Focus indicators MUST be clearly visible
- Modal dialogs MUST trap focus until dismissed

**USE-011: Visual Accessibility**
- Text MUST maintain minimum 4.5:1 contrast ratio (WCAG AA standard)
- Color MUST NOT be sole indicator of status (use icons, text labels)
- Font size MUST be minimum 14px for body text, 16px for primary UI elements
- UI MUST support browser zoom up to 200% without layout breaking

---

## 8. Compliance Requirements

### 8.1 Data Handling Best Practices

**COMP-001: Local Data Compliance**
- System MUST NOT transmit user data to third parties except as explicitly documented (LLM providers, scraped websites, IMAP servers)
- System MUST provide clear privacy notice on first run detailing:
  - What data is collected and stored
  - Where data is stored (local machine)
  - What data is transmitted to third parties and why
  - How to delete all data
- Privacy notice MUST be accessible from settings at all times

**COMP-002: Third-Party Service Compliance**
- System MUST document which third-party services receive user data:
  - LLM API providers: resume content, job posting content
  - Email servers: IMAP authentication credentials
  - Scraped websites: HTTP requests with standard headers
- System MUST link to third-party privacy policies
- System MUST allow user to opt out of third-party data transmission (disable AI analysis, disable email ingestion)

### 8.2 Web Scraping Ethics and Compliance

**COMP-003: Robots.txt Compliance**
- Web scraping MUST respect robots.txt directives
- URLs disallowed by robots.txt MUST NOT be scraped
- User-agent string MUST identify scraper honestly (not impersonate browser)
- Scraping failures due to robots.txt MUST inform user clearly

**COMP-004: Rate Limiting and Fair Use**
- Scraping MUST enforce rate limits to avoid overwhelming target servers (PERF-005: 10 req/min per domain)
- Scraping MUST implement polite delays between requests (minimum 6 seconds per domain)
- Scraping MUST NOT attempt to bypass anti-bot measures (CAPTCHAs, JavaScript challenges)
- Scraping failures due to anti-bot measures MUST inform user and NOT retry aggressively

**COMP-005: Copyright and Content Storage**
- Scraped job posting HTML MUST be stored for personal use only
- System MUST NOT provide functionality to share or publish scraped content
- System MUST provide clear mechanism to delete scraped content at user request
- System MUST NOT scrape or store content marked as copyrighted or proprietary if detectable

### 8.3 Email Content Compliance

**COMP-006: Email Storage Limitations**
- System MUST store only confirmation emails matching defined patterns
- System MUST NOT store entire mailbox or unrelated emails
- Email body storage MUST be opt-in with clear justification (improved parsing)
- System MUST provide mechanism to purge stored email content

**COMP-007: Email Privacy**
- Stored email content MUST be protected with file system permissions (SEC-004)
- Email content MUST NOT be transmitted to third parties (including LLM providers)
- System MUST NOT parse or store emails containing sensitive information beyond confirmation details (e.g., salary negotiations, personal correspondence)

### 8.4 Resume and PII Handling

**COMP-008: Resume Data Sensitivity**
- System MUST treat resume content as highly sensitive PII
- Resume data MUST be encrypted at rest if technically feasible
- Resume data transmitted to LLM providers MUST be done with user consent (PRIV-007)
- System MUST provide option to redact PII before AI analysis (PRIV-008)

---

## 9. Environmental & Deployment Requirements

### 9.1 Supported Platforms

**ENV-001: Operating System Support**
- System MUST support the following desktop operating systems:
  - macOS 12 (Monterey) and later
  - Windows 10 (version 1909) and later
  - Ubuntu 20.04 LTS and later
  - Other Linux distributions with equivalent glibc and systemd (informally supported)
- System MUST provide platform-specific installation packages:
  - macOS: .dmg or Homebrew formula
  - Windows: .exe installer or MSI package
  - Linux: .deb package, .rpm package, or tarball with install script

**ENV-002: Browser Compatibility**
- Browser extension MUST support:
  - Google Chrome 100 and later
  - Microsoft Edge 100 and later
  - Chromium-based browsers (Brave, Vivaldi) - informally supported
- Extension MUST NOT support Firefox or Safari in MVP (explicitly out of scope)

### 9.2 Resource Usage Limits

**ENV-003: CPU Resource Limits**
- Backend service MUST NOT exceed 50% CPU utilization sustained over 5 minutes on dual-core systems
- Background tasks (scraping, analysis) MUST be CPU-throttleable via configuration
- CPU-intensive operations (resume parsing, HTML parsing) MUST yield periodically to prevent system unresponsiveness

**ENV-004: Memory Resource Limits**
- Total system memory consumption MUST NOT exceed 3GB across all components under normal operation
- Components MUST NOT have memory leaks; long-running services MUST maintain stable memory footprint
- Out-of-memory conditions MUST be detected and logged before crash
- System MUST provide memory usage monitoring in dashboard or logs

**ENV-005: Disk Space Requirements**
- Minimum disk space required: 100MB for application binaries and dependencies
- Recommended disk space: 10GB for application data (5,000 applications with HTML snapshots)
- System MUST check available disk space before write-heavy operations (exports, scraping)
- System MUST warn user when available disk space falls below 1GB

**ENV-006: Network Resource Limits**
- Network bandwidth consumption MUST NOT exceed 10 Mbps sustained during scraping operations
- Background network operations MUST be pausable/resumable by user
- System MUST function in offline mode for:
  - Manual application entry
  - Viewing existing data
  - Editing applications
  - Local exports

### 9.3 Dependency Isolation and Management

**ENV-007: Runtime Dependencies**
- System MUST bundle all required runtime dependencies in installation package OR provide clear installation instructions
- Required dependencies:
  - Python 3.10 or later (for backend services)
  - Node.js 18 or later (for dashboard build, optional at runtime)
  - PostgreSQL 14 or later OR SQLite 3.35 or later (user-selectable)
- System MUST check for dependency availability at startup and display clear error if missing

**ENV-008: Database Installation**
- System MUST support SQLite as zero-configuration database option (default for ease of setup)
- System MUST support PostgreSQL as performance-optimized option for larger datasets
- Database schema migrations MUST be automated on application startup
- Database connection parameters MUST be configurable via environment variables or config file

**ENV-009: Python Virtual Environment**
- Python dependencies MUST be installed in isolated virtual environment
- Virtual environment MUST be created automatically during installation
- System MUST NOT require user to manually manage Python environment
- System MUST document Python version requirements clearly

### 9.4 Installation and Uninstallation

**ENV-010: Installation Process**
- Installation MUST be completable by non-technical user with documented steps
- Installation MUST NOT require administrator/root privileges except for:
  - Installing system-level dependencies (Python, PostgreSQL)
  - Browser extension installation (standard browser flow)
- Installation MUST validate all prerequisites and provide clear error messages for missing dependencies
- Installation MUST create necessary directories with proper permissions

**ENV-011: Uninstallation Process**
- Uninstallation MUST remove all application binaries and dependencies
- Uninstallation MUST preserve user data by default with option to delete
- Uninstallation MUST provide clear warning before deleting user data
- Uninstallation MUST leave system clean (no orphaned processes, files, or registry entries)

**ENV-012: Upgrade Process**
- System MUST support in-place upgrades without data loss
- Database schema migrations MUST be automated and reversible
- Upgrades MUST backup user data before applying schema changes
- Upgrade failures MUST be recoverable (rollback to previous version)

### 9.5 Process Management

**ENV-013: Service Lifecycle**
- Backend services MUST be startable via single command or system service
- Services MUST log startup success/failure clearly
- Services MUST expose health check endpoint (HTTP /health or equivalent)
- Services MUST shut down gracefully on SIGTERM (complete in-progress tasks, close connections)

**ENV-014: Automatic Startup**
- System SHOULD provide option to start backend services on system boot (systemd, launchd, Task Scheduler)
- Auto-startup MUST be user-configurable (opt-in or opt-out based on platform norms)
- Auto-startup MUST be disableable without uninstallation

---

## 10. Observability Requirements

### 10.1 Structured Logging (Detailed)

**OBS-001: Log Format Standardization**
- All logs MUST use structured JSON format with fields:
  ```json
  {
    "timestamp": "2025-12-10T14:23:45.123Z",
    "level": "INFO",
    "component": "web-scraper",
    "message": "Scrape completed successfully",
    "context": {
      "url": "https://example.com/job/123",
      "duration_ms": 1234,
      "status_code": 200
    }
  }
  ```
- Logs MUST be written to rotating log files (100MB max, 10 files retained)
- Logs MUST also output to console (stdout/stderr) with human-readable format option

**OBS-002: Log Levels and Usage**
- DEBUG: Detailed diagnostic information (variable values, function entry/exit)
- INFO: General informational messages (service started, scrape completed, application created)
- WARN: Warning messages indicating potential issues (rate limit approaching, queue depth high)
- ERROR: Error messages indicating operation failures (scrape failed, API error)
- FATAL: Critical errors requiring immediate attention (database connection lost, unrecoverable state)

**OBS-003: Sensitive Data Exclusion from Logs**
- Logs MUST NOT contain:
  - Email passwords or IMAP credentials
  - API keys or tokens
  - Full resume content (summary or excerpt only)
  - Full job descriptions (URL and title only)
  - Full email bodies (subject line and sender only)
- Logs MAY contain:
  - Application IDs (UUIDs)
  - Job titles and company names
  - URLs
  - Error messages and stack traces (sanitized)

### 10.2 Metrics and Monitoring

**OBS-004: Scraping Metrics**
- System MUST track and expose:
  - `scraping_requests_total{domain, status}` - Total scrape requests (counter)
  - `scraping_duration_seconds{domain}` - Scrape request latency (histogram)
  - `scraping_queue_depth` - Number of pending scrapes (gauge)
  - `scraping_failures_total{domain, reason}` - Failed scrapes by reason (counter)
- Metrics MUST be logged to file at 1-minute intervals
- Metrics SHOULD be exposed via Prometheus endpoint on localhost if Prometheus client library available

**OBS-005: AI Analysis Metrics**
- System MUST track and expose:
  - `analysis_requests_total{provider, status}` - Total analysis requests (counter)
  - `analysis_duration_seconds{provider}` - Analysis latency including API call (histogram)
  - `analysis_queue_depth` - Number of pending analyses (gauge)
  - `analysis_api_errors_total{provider, error_type}` - API errors by type (counter)
  - `analysis_tokens_used_total{provider}` - Cumulative tokens used (counter, for cost tracking)
- Metrics MUST be logged to file at 1-minute intervals

**OBS-006: Email Ingestion Metrics**
- System MUST track and expose:
  - `email_polling_cycles_total{status}` - Total polling cycles (counter)
  - `email_processed_total{source}` - Emails processed per source (counter)
  - `email_parse_failures_total{reason}` - Parse failures by reason (counter)
  - `email_polling_duration_seconds` - Time per polling cycle (histogram)
- Metrics MUST be logged to file at 1-minute intervals

**OBS-007: Database Metrics**
- System MUST track and expose:
  - `database_query_duration_seconds{operation}` - Query latency by operation type (histogram)
  - `database_connections_active` - Active database connections (gauge)
  - `database_transactions_total{status}` - Total transactions (counter)
  - `database_size_bytes{table}` - Database size per table (gauge, updated hourly)
- Metrics MUST be logged to file at 5-minute intervals

**OBS-008: Application Metrics**
- System MUST track and expose:
  - `applications_total{source}` - Total applications by source (gauge)
  - `applications_created_total{source}` - Applications created (counter)
  - `applications_by_status{status}` - Applications per status (gauge)
  - `timeline_events_total{event_type}` - Timeline events by type (counter)
- Metrics MUST be updated in real-time and logged at 5-minute intervals

### 10.3 Error Reporting and Alerting

**OBS-009: Error Aggregation**
- System MUST aggregate similar errors to prevent log spam:
  - Errors with same type and message within 5-minute window MUST be counted, not repeated
  - Aggregated error log format: `[ERROR] (occurred 15 times in last 5 minutes) Message`
- First occurrence of error MUST include full stack trace
- Subsequent occurrences MUST reference first occurrence log entry

**OBS-010: Critical Error Notification**
- System MUST provide mechanism to notify user of critical errors:
  - Dashboard notification banner for errors affecting functionality
  - System tray notification (optional, user-configurable) for service failures
  - Log file location prominently displayed in UI for troubleshooting
- Notification MUST include:
  - Error summary in plain language
  - Timestamp
  - Link to relevant log file or section
  - Suggested remediation steps

### 10.4 Audit Logging (Detailed)

**OBS-011: Audit Log Entries**
- System MUST log following user actions to separate audit log file:
  - User authentication to backend (if implemented)
  - Application record creation, update, deletion
  - Status changes with old/new values
  - Resume uploads with filename and size
  - AI analysis requests with application context
  - Configuration changes (email setup, API keys added/removed)
  - Data exports with export parameters
- Audit log format MUST include:
  - Timestamp (ISO 8601)
  - Action type
  - User identifier (single-user system: system user or "local")
  - Resource affected (application_id, resume_id, etc.)
  - Old and new values for updates
  - Outcome (success/failure)

**OBS-012: Audit Log Retention and Security**
- Audit logs MUST be append-only (no modifications or deletions)
- Audit logs MUST be retained for minimum 90 days
- Audit logs MUST be rotated at 50MB size with 20 file retention
- Audit log files MUST have owner-only read permissions (chmod 400 or equivalent)
- Audit logs MUST be included in backup recommendations

### 10.5 Performance Profiling

**OBS-013: Performance Instrumentation**
- System SHOULD support optional performance profiling mode (enabled via configuration)
- Profiling mode MUST capture:
  - Function call stacks and durations
  - Database query execution plans and timings
  - HTTP request/response sizes and latencies
- Profiling data MUST be exportable for analysis (e.g., flame graphs, trace files)
- Profiling mode MUST clearly indicate performance overhead (typically 10-30%)

---

## Appendix A: NFR Summary Matrix

| Category | Total Requirements | Critical (MUST) | Recommended (SHOULD) |
|----------|-------------------|-----------------|---------------------|
| Performance | 14 | 14 | 0 |
| Reliability & Fault Tolerance | 13 | 13 | 0 |
| Security | 11 | 11 | 0 |
| Privacy | 9 | 8 | 1 |
| Maintainability & Extensibility | 15 | 13 | 2 |
| Scalability | 5 | 4 | 1 |
| Usability | 11 | 11 | 0 |
| Compliance | 8 | 8 | 0 |
| Environmental & Deployment | 14 | 13 | 1 |
| Observability | 13 | 12 | 1 |
| **TOTAL** | **113** | **107** | **6** |

---

## Appendix B: NFR Verification Methods

Each NFR category should be verified using the following methods:

**Performance**: Load testing, benchmark suite, profiling tools  
**Reliability**: Chaos engineering (network failures, service crashes), retry validation  
**Security**: Security audit, penetration testing, credential storage validation  
**Privacy**: Data flow analysis, third-party transmission monitoring  
**Maintainability**: Code review, architecture review, extensibility testing  
**Scalability**: Dataset growth testing, queue overflow testing  
**Usability**: User acceptance testing, error message review  
**Compliance**: Legal review, scraping behavior validation  
**Environmental**: Multi-platform installation testing, resource monitoring  
**Observability**: Log parsing validation, metrics collection verification  

---

**End of Non-Functional Requirements Specification**
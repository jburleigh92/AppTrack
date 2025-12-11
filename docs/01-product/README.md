---
title: "Job Application Tracker – Product Requirements Document (PRD)"
version: 1.0
status: Draft
last_updated: 2025-12-10
owner: "Jason Burleigh"
---

# Job Application Tracker – Product Requirements Document (PRD)

## Table of Contents
- [1. Overview](#1-overview)
- [2. Problem Statement](#2-problem-statement)
- [3. Target User & Constraints](#3-target-user--constraints)
  - [3.1 Target User](#31-target-user)
  - [3.2 User Constraints](#32-user-constraints)
- [4. Core MVP Features](#4-core-mvp-features)
  - [F1: Browser Event Capture](#f1-browser-event-capture)
  - [F2: Email Integration](#f2-email-integration)
  - [F3: Job Posting Scraper](#f3-job-posting-scraper)
  - [F4: AI Resume Analysis](#f4-ai-resume-analysis)
  - [F5: Unified Application Dashboard](#f5-unified-application-dashboard)
  - [F6: Data Storage & Export](#f6-data-storage--export)
- [5. Explicitly Out of Scope](#5-explicitly-out-of-scope)
- [6. High-Level User Workflows](#6-high-level-user-workflows)
  - [W1: Initial Setup](#w1-initial-setup)
  - [W2: Passive Application Capture (Browser)](#w2-passive-application-capture-browser)
  - [W3: Passive Application Capture (Email)](#w3-passive-application-capture-email)
  - [W4: Manual Application Entry](#w4-manual-application-entry)
  - [W5: AI Analysis Review](#w5-ai-analysis-review)
  - [W6: Status Management](#w6-status-management)
  - [W7: Data Export](#w7-data-export)
- [7. Assumptions & Constraints](#7-assumptions--constraints)
  - [7.1 Technical Assumptions](#71-technical-assumptions)
  - [7.2 Functional Assumptions](#72-functional-assumptions)
  - [7.3 Platform Constraints](#73-platform-constraints)
  - [7.4 Data & Privacy Constraints](#74-data--privacy-constraints)
  - [7.5 Scalability Constraints](#75-scalability-constraints)
- [8. Summary](#8-summary)

---

## 1. Overview

The Job Application Tracker is a personal automation platform that unifies job application activity across browser submissions, confirmation emails, and job posting URLs. It centralizes data into a structured, local-first system and enriches each tracked application with AI-powered resume-to-job matching. This allows job seekers to eliminate manual tracking, avoid duplicate submissions, and gain actionable insights into qualification gaps and prioritization.

The MVP is engineered for **local use**, **single user deployment**, and **zero cloud dependencies**, providing maximum privacy with minimal complexity.

---

## 2. Problem Statement

Job seekers experience critical workflow challenges:

1. **Fragmented application data** spread across browser history, emails, and job boards with no consolidated view.  
2. **Manual tracking overhead** using spreadsheets that quickly fall out of date.  
3. **Lack of actionable insight** into job–resume alignment, leading to misprioritization and missed follow-ups.

These issues create cognitive load, information gaps, and inefficiencies that prevent job seekers from strategically managing their application pipeline.

---

## 3. Target User & Constraints

### 3.1 Target User
An individual job seeker who:

- Applies to 5–50+ roles concurrently.  
- Submits applications across multiple job boards.  
- Wants to automate tracking and centralize application data.  
- Values AI-generated insights on resume-job fit.  
- Is comfortable configuring a browser extension and IMAP email access.

### 3.2 User Constraints

- Local, single-user environment only.  
- Desktop workflow; no mobile app UI.  
- Resume must be text-extractable (PDF, DOCX, TXT).  
- English-language content only.  
- IMAP access required for email ingestion.  
- Browser permissions required for extension event detection.

---

## 4. Core MVP Features

### F1: Browser Event Capture
- Detect form submissions on major job boards.  
- Extract company, title, timestamp, URL.  
- Confirm data with user before saving.  

### F2: Email Integration
- Poll designated inbox/folder for confirmation emails.  
- Parse message content for job application metadata.  
- Deduplicate using email UID.  
- Support common formats (LinkedIn, Indeed, Greenhouse, Lever).

### F3: Job Posting Scraper
- Accept manually entered or auto-detected URLs.  
- Extract title, company, description, requirements, salary (if available).  
- Store raw HTML snapshot + structured data.  

### F4: AI Resume Analysis
- Parse uploaded resume into structured JSON.  
- Generate:  
  - Match score (0–100)  
  - Matched qualifications  
  - Missing qualifications  
  - Improvement suggestions  
- Triggered manually or automatically after scraping.

### F5: Unified Application Dashboard
- List all applications with sorting/filtering (date, status, score, company).  
- Show detailed view including full job description, AI insights, timeline, and metadata.  
- Allow manual updates to status and notes.

### F6: Data Storage & Export
- Persist all data locally.  
- Export applications to CSV.  
- Prevent duplicate entries via smart matching on company/title/date/URL.

---

## 5. Explicitly Out of Scope

To maintain MVP focus, the following are excluded:

- Calendar integrations or reminders  
- Multiple resume profiles  
- Deadline tracking  
- Recruiter/contact CRM  
- AI cover letter generation  
- Interview preparation tooling  
- Salary intelligence  
- Autofilling job applications  
- Mobile UI  
- Team/shared accounts  
- Advanced analytics or funnel visualizations  
- Job discovery or recommendations  
- Multi-document storage  
- Email thread tracking  

---

## 6. High-Level User Workflows

### W1: Initial Setup
1. Install browser extension.  
2. Configure job boards.  
3. Connect email inbox (IMAP or forwarding).  
4. Upload resume.  
5. System verifies connectivity.

### W2: Passive Application Capture (Browser)
1. User applies to job online.  
2. Extension detects submission and extracts metadata.  
3. User confirms details.  
4. Application saved; URL queued for scraping.

### W3: Passive Application Capture (Email)
1. Confirmation email arrives.  
2. Email parser extracts job data.  
3. Application saved with source = “Email”.  
4. URL (if present) queued for scraping.

### W4: Manual Application Entry
1. User fills form with application data.  
2. System saves and triggers scraping if URL exists.

### W5: AI Analysis Review
1. User opens an application.  
2. Clicks “Run Analysis” (or auto-runs).  
3. System evaluates job-description vs resume.  
4. Score and insights displayed.

### W6: Status Management
- User updates status (Applied → Interview → Offer, etc.).  
- Timeline logs each action.

### W7: Data Export
- User selects export format.  
- System generates and downloads CSV.

---

## 7. Assumptions & Constraints

### 7.1 Technical Assumptions
- Stable internet required for scraping + AI API calls.  
- Resume/job posting structures predictable enough for parsing.  
- LLM reliably outputs structured JSON.  
- Email formats match established parsing patterns.

### 7.2 Functional Assumptions
- Job postings remain accessible for 30–90 days.  
- Resume content does not change frequently.  
- Confirmation emails arrive within 24 hours.

### 7.3 Platform Constraints
- Requires Chromium-based browser.  
- IMAP or forwarding required for email capture.  
- No real-time sync; data is local-only.  

### 7.4 Data & Privacy Constraints
- All data stored locally.  
- User responsible for their own backups.  
- Sensitive resume and job information requires secure storage.  
- IMAP credentials never sent externally.  
- No telemetry or analytics collection.

### 7.5 Scalability Constraints
- Designed for up to ~500 applications.  
- Scraping rate limited to ~10 requests/min per domain.  
- AI analysis is one-job-per-request.

---

## 8. Summary

This PRD defines the functional, non-functional, and architectural boundaries of the Job Application Tracker MVP. The platform provides:

- Automated ingestion of applications from browser and email  
- Accurate job scraping  
- AI-assisted resume–job fit analysis  
- Local, privacy-first data storage  
- A unified dashboard for tracking and reviewing applications  

The MVP is intentionally scoped to deliver high-value automation and insights without unnecessary complexity. Future enhancements may include: multi-resume support, analytics dashboards, notification systems, collaboration features, and mobile integration.

---

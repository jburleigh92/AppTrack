# Changelog
All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)  
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## v0.1.1 — 2025-12-11

### Fixed
- Corrected database initialization flow to ensure `init_db()` is called before any DB access.
- Repaired `/health/ready` dependency by using the proper `get_db` import.
- Fixed environment variable loading by moving `.env` to `backend/app/core` and updating `config.py`.
- Resolved missing or incorrect imports in `timeline_service` (added backwards-compatibility wrappers).
- Updated timeline schemas to reflect the actual models in use.
- Added "*.db" to `.gitignore` to prevent SQLite database files from being committed.



## [Unreleased]
### Added
- (Place future changes here before next release)

---

## [v0.1.0] — 2025-12-11

### Added
- Full product scope documentation
- User flows and UX sequences
- Complete system design including:
  - Ingestion layer
  - FastAPI backend structure
  - Worker queue architecture
  - AI analysis pipeline
  - Scraper module design
  - Timeline event system design
- Data schema and migration definitions
- API contracts for each module
- Module decomposition plan
- Development milestone plan
- Ingestion pipelines (Chrome extension + Gmail polling/webhook)
- Correlation engine logic
- Scraper service design + extraction structure
- AI analysis engine logic + scoring structure
- Timeline event system design
- Export layer (CSV + Sheets sync)
- Full documentation hierarchy under `/docs`
- Backend scaffolding under `/backend/app`
- Initial FastAPI entrypoint + routing layout

### Notes
This release represents the completion of **Phases 1–4** of the A→Z development plan:
- Product discovery  
- System design  
- Implementation planning  
- Core architecture + scaffolding  

This is the first stable foundation ready for integration testing and Phase 5 hardening.
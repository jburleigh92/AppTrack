# Data Schema Overview

## Purpose
This section documents the complete data model for the Job Application Tracker, including relational schema, normalization decisions, indexing strategy, and lifecycle rules for all entities.

## Contents
- `data-schema-design.md` – Full, authoritative schema specification  
- `er-diagram.png` – Visual ERD (optional)  
- `migration-strategy.md` – How migrations are structured and applied (optional)  

## Quick Summary
- 12 core entities  
- Full normalization (3NF+)  
- Separate raw vs extracted job posting tables  
- Separate file metadata vs parsed resume data  
- Append-only audit logs  
- Three worker queues with independent schemas  

## For Engineers
- Always read the Data Schema Design Document before writing models  
- Follow naming conventions and immutability rules  
- Never store credentials in the database (keychain/secret store only)  

## For Migrations
- All changes must include:
  - forward migration SQL  
  - backward migration SQL  
  - version bump in Alembic  

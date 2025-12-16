# WS1 — Phase 3 Schema & Migrations
**Phase:** Phase 3 (Designed, Not Implemented)  
**Work Stream:** WS1  
**Status:** Execution-ready  
**Scope:** Additive persistence only  
**Risk Level:** Low (isolated, rollback-safe)

---

## 1. Objective

Define all **Phase 3–specific schema changes** required to support advisory-only intelligence while guaranteeing:

- Zero mutation of Phase 1 or Phase 2 state
- Zero coupling to Phase 1/2 truth derivation
- Instant rollback with no data loss risk
- Complete isolation behind a kill-switch

This work stream introduces **new tables only**, all prefixed with `p3_`, and does **not** modify, constrain, or reference existing tables via blocking foreign keys.

---

## 2. Hard Constraints (Non-Negotiable)

These constraints are enforced structurally by schema design:

1. **No ALTERs**
   - No changes to existing Phase 1 or Phase 2 tables
   - No new columns, indexes, triggers, or constraints on existing tables

2. **Prefix Isolation**
   - All Phase 3 tables must be prefixed with `p3_`
   - This enables:
     - Clear audit separation
     - Write-guard enforcement
     - Drop-only rollback

3. **No Blocking Foreign Keys**
   - Phase 3 tables may reference Phase 1/2 identifiers **logically only**
   - No FK constraints are allowed that could:
     - Block Phase 1/2 writes
     - Create dependency ordering
     - Introduce cascading deletes

4. **Advisory-Only Persistence**
   - Phase 3 tables store *derived guidance*, not truth
   - All data is ignorable by design

5. **Rollback Must Be Destructive-Only to Phase 3**
   - Rollback is accomplished exclusively via `DROP TABLE`
   - No data migration or backfill reversal required

---

## 3. Phase 3 Table Inventory

WS1 defines **exactly four tables**.

---

### 3.1 `p3_advisory_signal`

**Purpose**  
Stores computed advisory outputs derived from existing matches (`analysis_results`).  
Each row represents *one advisory signal* for a specific resume–job pair.

**Authoritativeness**  
- ❌ Not authoritative  
- ❌ Does not affect user_state  
- ❌ Does not affect ranking or workflow  
- ✅ Safe to ignore

**Schema**
```sql
CREATE TABLE p3_advisory_signal (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Logical references only (NO FOREIGN KEYS)
    resume_id UUID NOT NULL,
    job_posting_id UUID NOT NULL,

    -- Advisory content
    signal_type TEXT NOT NULL,
    signal_payload JSONB NOT NULL,
    confidence_score NUMERIC(5,4) NOT NULL
        CHECK (confidence_score BETWEEN 0 AND 1),

    -- Provenance
    model_version TEXT NOT NULL,
    computed_at TIMESTAMP NOT NULL DEFAULT now(),

    -- Lifecycle
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,

    created_at TIMESTAMP NOT NULL DEFAULT now()
);
```

**Key Design Decisions**
- No uniqueness constraints → multiple advisory generations allowed
- `confidence_score` bounded to [0,1] for consistency
- `expires_at` is advisory-only; expired rows are ignored, not deleted
- `is_active=false` provides soft invalidation without deletes

---

### 3.2 `p3_advisory_budget`

**Purpose**  
Enforces **Phase 3–only cost ceilings** so advisory computation cannot overwhelm the system.

**Scope**
- Budget is per `resume_id` per calendar day
- Budget applies **only** to Phase 3 advisory computation
- Budget is independent from Phase 2 analysis rate limits

**Schema**
```sql
CREATE TABLE p3_advisory_budget (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Logical scope (NO FOREIGN KEYS)
    resume_id UUID NOT NULL,
    budget_day DATE NOT NULL,

    max_advisories INTEGER NOT NULL,
    used_advisories INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT now(),

    UNIQUE (resume_id, budget_day)
);
```

**Key Design Decisions**
- Unique constraint enforces one budget row per resume per day
- Atomic updates guarantee race safety
- Budget exhaustion causes silent skip, never failure

---

### 3.3 `p3_advisory_cache`

**Purpose**  
Guarantees **idempotency and deduplication** of advisory computation.

**Behavior**
- Multiple workers may attempt the same advisory
- Cache collapses duplicates to a single canonical signal

**Schema**
```sql
CREATE TABLE p3_advisory_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cache_key TEXT NOT NULL,
    signal_id UUID NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT now(),

    UNIQUE (cache_key)
);
```

**Key Design Decisions**
- `cache_key` is deterministic and collision-resistant
- No FK to `p3_advisory_signal` to avoid blocking deletes
- Cache rows are never required to be deleted

---

### 3.4 `p3_feature_state`

**Purpose**  
Single authoritative **kill-switch and rollout control** for all Phase 3 behavior.

**Schema**
```sql
CREATE TABLE p3_feature_state (
    feature_name TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT false,
    rollout_percent INTEGER NOT NULL DEFAULT 0
        CHECK (rollout_percent BETWEEN 0 AND 100),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
```

**Key Design Decisions**
- One row per Phase 3 feature
- Backend-only authority (no env flags)
- Changing this table requires no deploy

---

## 4. Indexes (Non-Blocking)

```sql
CREATE INDEX idx_p3_signal_resume_job
    ON p3_advisory_signal (resume_id, job_posting_id);

CREATE INDEX idx_p3_signal_active
    ON p3_advisory_signal (is_active);

CREATE INDEX idx_p3_budget_day
    ON p3_advisory_budget (budget_day);

CREATE INDEX idx_p3_cache_signal
    ON p3_advisory_cache (signal_id);
```

---

## 5. Migration Execution Checklist

**Order is mandatory.**

### Step 1 — Create tables
- `p3_advisory_signal`
- `p3_advisory_budget`
- `p3_advisory_cache`
- `p3_feature_state`

### Step 2 — Create indexes
- Only after tables exist

### Step 3 — Seed kill-switch (dark launch)
```sql
INSERT INTO p3_feature_state (feature_name, enabled, rollout_percent)
VALUES ('p3_advisory', false, 0)
ON CONFLICT (feature_name) DO NOTHING;
```

### Step 4 — Verify isolation
- No Phase 1/2 tables altered
- No FKs created

---

## 6. Rollback Strategy (Guaranteed Safe)

Rollback is **drop-only** and order-independent:

```sql
DROP TABLE IF EXISTS p3_advisory_cache;
DROP TABLE IF EXISTS p3_advisory_budget;
DROP TABLE IF EXISTS p3_advisory_signal;
DROP TABLE IF EXISTS p3_feature_state;
```

**Rollback Properties**
- No cascading effects
- No orphan risk
- No impact on Phase 1/2 execution
- Safe at any time

---

## 7. Verification Queries

### Confirm Phase 3 tables exist
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_name LIKE 'p3_%'
ORDER BY table_name;
```

### Confirm no foreign keys
```sql
SELECT *
FROM information_schema.table_constraints
WHERE table_name LIKE 'p3_%'
  AND constraint_type = 'FOREIGN KEY';
```
Expected: **0 rows**

---

### Confirm kill-switch default
```sql
SELECT *
FROM p3_feature_state
WHERE feature_name = 'p3_advisory';
```
Expected:
- `enabled = false`
- `rollout_percent = 0`

---

### Confirm empty initial state
```sql
SELECT count(*) FROM p3_advisory_signal;
```
Expected: `0`

---

## 8. Explicit Non-Goals

WS1 does **not**:
- Populate any Phase 3 data
- Reference queue state
- Affect API responses
- Change UX
- Introduce migrations to Phase 1/2 tables

Those concerns belong to WS2–WS8.

---

## 9. WS1 Completion Criteria

WS1 is complete when:
- All tables exist
- Kill-switch is seeded OFF
- No Phase 1/2 tables are modified
- Rollback has been dry-run successfully

---

## WS1 STATUS
✅ **COMPLETE — SAFE TO PROCEED**

End of WS1.

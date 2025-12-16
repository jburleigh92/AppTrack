# WS2 — Data Population Logic (Read-Only Inputs)
**Phase:** Phase 3 (Designed, Not Implemented)  
**Work Stream:** WS2  
**Status:** Execution-ready  
**Scope:** Phase 3 data population only  
**Risk Level:** Medium (logic-heavy, isolated writes)

---

## 1. Objective

Define **exactly how Phase 3 advisory data is populated** using **read-only inputs** from Phase 1 and Phase 2, while guaranteeing:

- No mutation of Phase 1 or Phase 2 state
- No coupling to user_state or truth derivation
- No blocking or retry behavior
- Deterministic, bounded execution
- Full compliance with Phase 3 kill-switch discipline

This work stream governs *when* and *how* Phase 3 writes to `p3_*` tables occur.  
It does **not** define advisory computation logic (WS3) or caching/budget enforcement (WS4), only **population flow and gating**.

---

## 2. Hard Constraints (Non-Negotiable)

1. **Read-Only Inputs**
   - Phase 3 may only READ from existing persisted Phase 1/2 artifacts
   - No writes, updates, or side effects outside `p3_*` tables

2. **No Queue or Worker State**
   - No reading from queues, retries, attempt counters, or worker metadata
   - Population decisions are based on persisted facts only

3. **No Blocking**
   - Phase 3 population must never block upstream requests
   - Budget exhaustion, cache hits, or missing data result in silent skip

4. **Kill-Switch Supremacy**
   - If Phase 3 is disabled, WS2 performs **zero reads and zero writes**

5. **Idempotent by Design**
   - Population logic must tolerate repeated execution without duplication

---

## 3. Authoritative Inputs (Read-Only)

WS2 consumes **only persisted artifacts** that already exist and are authoritative in Phase 1/2.

### 3.1 Canonical Match Baseline (Locked)

**Table:** `analysis_results`  
This table is the **sole authoritative source** of completed resume ↔ job matches.

Required fields (read-only):
- `id` (analysis_result_id)
- `resume_id`
- `job_posting_id`
- Match outputs (score, qualification lists, suggestions, metadata)
- `created_at`
- Model/provider metadata

**Rules**
- No advisory is generated unless an `analysis_results` row exists
- Phase 3 must never infer matches from other tables

---

### 3.2 Optional Context Inputs (Read-Only, If Already Used Elsewhere)

Phase 3 may additionally read:
- `job_postings` (job attributes already consumed by Phase 2 ranking)
- `applications` (timestamps or lifecycle context if already read elsewhere)

**Forbidden Reads**
- Queue tables
- Retry tables
- Worker attempt logs
- Transient execution metadata

---

## 4. Population Trigger Model

WS2 does **not** introduce new triggers or workflows.

Population may occur:
- Opportunistically during existing Phase 2 read paths
- In background Phase 3-only workers
- In scheduled Phase 3 batch jobs

**Rules**
- Population must be best-effort
- Missing prerequisites result in skip
- No retry loops are permitted

---

## 5. Candidate Selection

### 5.1 Candidate Definition

A **candidate** is a `(resume_id, job_posting_id, analysis_result_id)` tuple derived from an existing `analysis_results` row.

### 5.2 Candidate Query (Canonical)

```sql
SELECT
  ar.id AS analysis_result_id,
  ar.resume_id,
  ar.job_posting_id,
  ar.created_at
FROM analysis_results ar
WHERE 1=1;
```

**Notes**
- No joins are required
- Filtering (recency, job activity) is optional but must be deterministic and read-only
- Absence of a row means Phase 3 does nothing

---

## 6. Population Flow (Ordered, Mandatory)

The following steps must execute **in order**.  
Failure or skip at any step aborts the remainder silently.

---

### Step 0 — Kill-Switch Gate

Before **any** Phase 3 logic:

```sql
SELECT enabled, rollout_percent
FROM p3_feature_state
WHERE feature_name = 'p3_advisory';
```

- `enabled=false` → return immediately
- `rollout_percent=0` → return immediately

No further reads or writes are permitted if disabled.

---

### Step 1 — Rollout Eligibility Gate

Eligibility is deterministic per resume:

```text
bucket = hash(resume_id) % 100
eligible = bucket < rollout_percent
```

- If not eligible → skip
- No state is recorded for ineligible resumes

---

### Step 2 — Cache Gate (Read-Only)

Before any compute or budget usage:

```sql
SELECT signal_id
FROM p3_advisory_cache
WHERE cache_key = $cache_key;
```

- Cache hit → population stops (reuse existing advisory)
- Cache miss → proceed

**Important**
- Cache key derivation is defined in WS4
- Cache hit does NOT consume budget

---

### Step 3 — Budget Initialization (Phase 3-Only Write)

Ensure a budget row exists for the resume/day:

```sql
INSERT INTO p3_advisory_budget (
  resume_id,
  budget_day,
  max_advisories,
  used_advisories
)
VALUES ($resume_id, CURRENT_DATE, $configured_max, 0)
ON CONFLICT (resume_id, budget_day) DO NOTHING;
```

- Idempotent
- No locks on Phase 1/2 tables

---

### Step 4 — Budget Consumption Gate

Attempt atomic budget consumption:

```sql
UPDATE p3_advisory_budget
SET used_advisories = used_advisories + 1
WHERE resume_id = $resume_id
  AND budget_day = CURRENT_DATE
  AND used_advisories < max_advisories;
```

- `rowcount = 1` → proceed
- `rowcount = 0` → budget exhausted → skip silently

---

### Step 5 — Advisory Computation (Delegated)

At this point:
- Inputs are locked
- Budget is granted
- Cache miss confirmed

WS2 **hands off** to WS3 for computation.

**Important**
- WS2 does not define compute logic
- WS2 only governs gating and write eligibility

---

### Step 6 — Persist Advisory Outputs (Phase 3-Only)

WS3 returns:
- `signal_type`
- `signal_payload`
- `confidence_score`
- `model_version`
- Optional `expires_at`

WS2 persists results to:
- `p3_advisory_signal`
- `p3_advisory_cache`

If cache insert fails (duplicate key):
- Discard newly created advisory
- Re-select existing cache row
- Do not retry

---

## 7. Failure & Skip Semantics

| Condition | Behavior |
|--------|---------|
| Kill-switch disabled | Immediate no-op |
| Rollout ineligible | Skip |
| No analysis_results row | Skip |
| Cache hit | Skip |
| Budget exhausted | Skip |
| Compute error | Log + skip |
| DB write error | Log + skip |

**Never**
- Retry
- Throw user-visible errors
- Block requests
- Modify Phase 1/2 state

---

## 8. Idempotency Guarantees

WS2 guarantees idempotency through:
- Deterministic cache keys
- UNIQUE constraints in `p3_advisory_cache`
- Atomic budget updates
- Skip-on-conflict semantics

Repeated execution with identical inputs produces **at most one advisory output**.

---

## 9. Verification Queries

### Confirm population occurred
```sql
SELECT count(*) FROM p3_advisory_signal;
```

---

### Confirm logical references only
```sql
SELECT resume_id, job_posting_id
FROM p3_advisory_signal
LIMIT 20;
```

---

### Confirm budget correctness
```sql
SELECT resume_id, budget_day, max_advisories, used_advisories
FROM p3_advisory_budget
WHERE used_advisories > max_advisories;
```
Expected: **0 rows**

---

### Confirm cache coverage
```sql
SELECT
  COUNT(*) AS cache_rows,
  COUNT(DISTINCT cache_key) AS unique_keys
FROM p3_advisory_cache;
```
Expected: `cache_rows = unique_keys`

---

## 10. Explicit Non-Goals

WS2 does **not**:
- Define advisory heuristics
- Define caching mechanics (WS4)
- Expose APIs (WS5)
- Change UX (WS6)
- Enforce contracts (WS7)

Those responsibilities belong to other work streams.

---

## 11. WS2 Completion Criteria

WS2 is complete when:
- Population is gated correctly
- No Phase 1/2 writes occur
- Budget exhaustion is skip-safe
- Cache prevents duplication
- Kill-switch suppresses all activity

---

## WS2 STATUS
✅ **COMPLETE — SAFE TO PROCEED**

End of WS2.

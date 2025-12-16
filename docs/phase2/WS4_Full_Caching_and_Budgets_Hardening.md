# WS4 — Caching & Budgets Hardening
**Phase:** Phase 3 (Designed, Not Implemented)  
**Work Stream:** WS4  
**Status:** Execution-ready  
**Scope:** Cache correctness, idempotency, and cost controls  
**Risk Level:** Medium (concurrency, cost containment)

---

## 1. Objective

Harden Phase 3 advisory execution so that it is:

- Deterministic and idempotent under concurrency
- Cost-bounded and skip-safe under load
- Fully kill-switchable
- Incapable of affecting Phase 1 or Phase 2 behavior

WS4 defines **how caching and budgets are enforced**, not *what* is computed (WS3) or *when* population is triggered (WS2).

---

## 2. Hard Constraints (Non-Negotiable)

1. **Phase 3 Isolation**
   - All writes are confined to `p3_*`
   - No locks or writes on Phase 1/2 tables

2. **No Blocking**
   - Cache conflicts, budget exhaustion, or compute errors must never block
   - All failure modes result in silent skip

3. **Kill-Switch Supremacy**
   - If disabled, no cache reads, no budget reads, no writes, no compute

4. **Concurrency Safety**
   - Multiple workers may execute concurrently
   - Correctness must not depend on execution order

---

## 3. Cache Hardening

### 3.1 Canonical Cache Key (Locked)

**Purpose**  
Collapse duplicate advisory computation across workers, retries, and restarts.

**Definition**
```
cache_key = SHA256(
  analysis_result_id +
  signal_type +
  model_version
)
```

**Rules**
- Must be deterministic
- Must not include timestamps
- Must not include confidence_score
- Must not include application_id
- Changing `model_version` intentionally invalidates cache

---

### 3.2 Cache Read Semantics

Before any budget consumption or compute:

```sql
SELECT signal_id
FROM p3_advisory_cache
WHERE cache_key = $cache_key;
```

- Row exists → cache hit → stop execution
- No row → cache miss → proceed

**Rules**
- Cache hit does NOT consume budget
- Cache read is read-only and non-blocking

---

### 3.3 Cache Write Semantics

After successful advisory computation:

1. Insert advisory signal
2. Insert cache row

```sql
INSERT INTO p3_advisory_cache (cache_key, signal_id)
VALUES ($cache_key, $signal_id);
```

**Conflict Handling**
- If UNIQUE constraint violation occurs:
  - Discard newly created advisory signal
  - Re-select existing cache row
  - Do not retry

This guarantees **at-most-one advisory per cache key**.

---

### 3.4 Cache Eviction Policy

- No automatic eviction required
- Cache rows may remain indefinitely
- Optional soft invalidation via `is_active=false` on signal rows

**Rationale**
- Eviction is optimization, not correctness
- Retaining cache rows prevents recompute storms

---

## 4. Budget Hardening

### 4.1 Budget Scope (Locked)

- Budget key: `(resume_id, budget_day)`
- Applies only to Phase 3 advisory computation
- Independent from Phase 2 analysis limits

---

### 4.2 Budget Initialization

Idempotent initialization:

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

- No locks
- No Phase 1/2 interaction

---

### 4.3 Budget Consumption (Atomic)

```sql
UPDATE p3_advisory_budget
SET used_advisories = used_advisories + 1
WHERE resume_id = $resume_id
  AND budget_day = CURRENT_DATE
  AND used_advisories < max_advisories;
```

**Interpretation**
- `rowcount = 1` → budget granted
- `rowcount = 0` → budget exhausted → skip silently

---

### 4.4 Budget Consumption Ordering (Mandatory)

Correct order:
1. Cache read
2. Budget initialize
3. Budget consume
4. Compute

**Forbidden**
- Consuming budget before cache check
- Retrying on budget exhaustion

---

### 4.5 Budget Exhaustion Semantics

When exhausted:
- Skip advisory computation
- Emit informational log
- Do not retry
- Do not error

This ensures Phase 3 degrades gracefully.

---

## 5. Kill-Switch Enforcement

Before **any** WS4 logic:

```sql
SELECT enabled, rollout_percent
FROM p3_feature_state
WHERE feature_name = 'p3_advisory';
```

Rules:
- `enabled=false` → immediate no-op
- `rollout_percent=0` → immediate no-op

No cache reads, no budget reads, no writes when disabled.

---

## 6. Concurrency & Race Safety

### 6.1 Allowed Races

- Multiple workers compute same advisory concurrently
- Budget rows initialized concurrently
- Cache inserts collide

These are expected and safe.

---

### 6.2 Safety Mechanisms

- UNIQUE(cache_key) enforces idempotency
- Atomic budget updates enforce limits
- Losers discard work without side effects

---

### 6.3 Forbidden Patterns

- SELECT ... FOR UPDATE on Phase 1/2 tables
- Cross-worker locks
- Retries on cache or budget failure
- Blocking waits

---

## 7. Observability Hooks (WS4-Level)

Emit structured, Phase 3–scoped logs:

| Event | Condition |
|-----|-----------|
| `phase3.cache_hit` | Cache row exists |
| `phase3.cache_miss` | Cache row absent |
| `phase3.budget_granted` | Budget update succeeded |
| `phase3.budget_exhausted` | Budget update failed |
| `phase3.compute_skipped_disabled` | Kill-switch disabled |
| `phase3.compute_error` | Compute failed (swallowed) |

Rules:
- No PII
- No Phase 1/2 internals
- Log volume must be rate-limited

---

## 8. Verification Queries

### Cache correctness
```sql
SELECT
  COUNT(*) AS cache_rows,
  COUNT(DISTINCT cache_key) AS unique_keys
FROM p3_advisory_cache;
```
Expected: `cache_rows = unique_keys`

---

### Budget correctness
```sql
SELECT resume_id, budget_day, max_advisories, used_advisories
FROM p3_advisory_budget
WHERE used_advisories > max_advisories;
```
Expected: **0 rows**

---

### Kill-switch proof
```sql
UPDATE p3_feature_state
SET enabled = false, rollout_percent = 0
WHERE feature_name = 'p3_advisory';
```

Trigger advisory logic → expect **no cache reads, no budget writes, no advisory writes**.

---

## 9. Explicit Non-Goals

WS4 does **not**:
- Define advisory heuristics
- Select candidates
- Expose APIs
- Render UX
- Enforce Phase 3 contracts globally (WS7)

---

## 10. WS4 Completion Criteria

WS4 is complete when:
- Cache is deterministic and collision-safe
- Budget enforcement is atomic and skip-safe
- Kill-switch halts all behavior
- Concurrency cannot create duplicates
- No Phase 1/2 coupling exists

---

## WS4 STATUS
✅ **COMPLETE — SAFE TO PROCEED**

End of WS4.

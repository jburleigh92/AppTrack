# WS8 — Flags & Rollout (Progressive Enablement, Kill-Switch Discipline)
**Phase:** Phase 3 (Designed, Not Implemented)  
**Work Stream:** WS8  
**Status:** Execution-ready  
**Scope:** Progressive rollout control and instant disablement  
**Risk Level:** Low (control-plane only)

---

## 1. Objective

Define **how Phase 3 is safely enabled, expanded, and disabled** in production while guaranteeing:

- Phase 3 starts fully dark
- Phase 3 can be enabled incrementally
- Phase 3 can be disabled instantly with no redeploy
- Phase 1/2 behavior is unchanged at every rollout stage

WS8 governs **control-plane behavior only**.  
It introduces no new features, logic, or data paths.

---

## 2. Canonical Control Surface (Locked)

Phase 3 rollout is controlled exclusively via:

### `p3_feature_state`

```sql
feature_name = 'p3_advisory'
enabled BOOLEAN
rollout_percent INTEGER (0–100)
```

**Rules**
- This table is the **single source of truth**
- No environment variables
- No client-side feature flags
- No secondary toggles
- Backend logic is authoritative

---

## 3. Flag Semantics (Hard Rules)

### 3.1 `enabled = false`
- Phase 3 is fully disabled
- No reads
- No writes
- No compute
- No advisory UX
- Only `phase3.disabled_noop` logs allowed

---

### 3.2 `enabled = true` AND `rollout_percent = 0`
- Treated identically to disabled
- Used for safe staging and validation
- Must not activate any Phase 3 behavior

---

### 3.3 `enabled = true` AND `rollout_percent > 0`
- Phase 3 is selectively active
- Eligibility is determined per-resume (see below)
- All other constraints still apply

---

## 4. Rollout Gating Algorithm (Deterministic)

Eligibility is computed **per resume**, deterministically:

```text
bucket = hash(resume_id) % 100
eligible = enabled AND (bucket < rollout_percent)
```

**Properties**
- Stable across requests
- Independent of servers or sessions
- No sticky state
- No coordination required

If `eligible = false` → Phase 3 logic must no-op immediately.

---

## 5. Recommended Rollout Stages

### Stage 0 — Dark Launch (Default)

```sql
enabled = false
rollout_percent = 0
```

- Safe to deploy to production
- Zero runtime effect
- Required initial state

---

### Stage 1 — Canary (Internal Validation)

```sql
enabled = true
rollout_percent = 1
```

- ~1% of resumes eligible
- Minimal cost exposure
- Observe WS7 metrics only

---

### Stage 2 — Limited Exposure

```sql
rollout_percent = 5 → 10
```

Validate:
- Cache hit rate
- Budget adherence
- No contract violations
- No Phase 1/2 anomalies

---

### Stage 3 — Broad Exposure

```sql
rollout_percent = 25 → 50
```

- Advisory visible to many users
- Still advisory-only
- Continue monitoring invariants

---

### Stage 4 — Full Rollout

```sql
rollout_percent = 100
```

- Phase 3 fully enabled
- Kill-switch remains authoritative

---

## 6. Instant Kill-Switch Procedure

### Single Command Rollback

```sql
UPDATE p3_feature_state
SET enabled = false,
    rollout_percent = 0
WHERE feature_name = 'p3_advisory';
```

**Immediate Effects**
- All Phase 3 logic halts
- No reads or writes
- No advisory UX
- No retries
- No errors

**No redeploy required**

---

## 7. Rollback Philosophy

- Disable > observe > decide
- Never delete Phase 3 data as rollback
- Phase 3 tables remain inert when disabled
- Rollback is logical, not physical

---

## 8. Guardrails Against Misuse

### Forbidden Actions
- Increasing rollout without metrics review
- Enabling Phase 3 without kill-switch validation
- Running batch backfills tied to rollout
- Conditioning rollout on user_state or application status

---

### Required Preconditions Before Increasing Rollout

- Zero `phase3.contract_violation` events
- Budget exhaustion within expected bounds
- Cache hit rate stable or improving
- No Phase 1/2 write anomalies

---

## 9. Verification Checklist

### 9.1 Deterministic Gating

```sql
SELECT enabled, rollout_percent
FROM p3_feature_state
WHERE feature_name = 'p3_advisory';
```

Verify behavior changes only when expected.

---

### 9.2 Kill-Switch Proof

1. Enable Phase 3 at low percentage
2. Confirm advisory writes occur
3. Disable Phase 3
4. Confirm:
   - No new `p3_*` writes
   - No advisory reads
   - No UI changes

---

### 9.3 Phase 1/2 Isolation Proof

```sql
SELECT relname, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
WHERE relname NOT LIKE 'p3_%';
```

Expected: **no Phase 3-attributable mutations**

---

## 10. Explicit Non-Goals

WS8 does **not**:
- Define advisory computation
- Modify caching or budgets
- Expose APIs
- Render UX
- Enforce contracts (WS7)

---

## 11. WS8 Completion Criteria

WS8 is complete when:
- Phase 3 can be enabled progressively
- Phase 3 can be disabled instantly
- No redeploy is required for control
- Phase 1/2 behavior is unchanged at all rollout stages

---

## WS8 STATUS
✅ **COMPLETE — PHASE 3 FULLY CONTROLLABLE**

End of WS8.

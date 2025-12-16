# WS7 — Observability & Enforcement (Phase 3 Contracts)
**Phase:** Phase 3 (Designed, Not Implemented)  
**Work Stream:** WS7  
**Status:** Execution-ready  
**Scope:** Contract enforcement, observability, and safety guarantees  
**Risk Level:** Medium (guardrails and detection)

---

## 1. Objective

Provide **hard guarantees and proof** that Phase 3:

- Never mutates Phase 1 or Phase 2 state
- Never affects user_state derivation
- Never blocks user-visible flows
- Remains advisory-only at all times
- Can be disabled instantly and completely

WS7 introduces **enforcement points and observability**, not new behavior.

---

## 2. Phase 3 Contract Invariants (Hard)

The following are **never-events**. Any occurrence is a defect.

1. **No Phase 1/2 Writes**
   - Phase 3 must not INSERT, UPDATE, or DELETE outside `p3_*` tables.

2. **No user_state Influence**
   - Phase 3 must not read from or write to user_state derivation logic or inputs.

3. **No Blocking**
   - Phase 3 must not introduce waits, retries, or synchronous dependencies.

4. **Kill-Switch Supremacy**
   - When disabled, Phase 3 performs zero reads, zero writes, zero compute, and zero UX changes.

5. **Advisory-Only Semantics**
   - Phase 3 outputs must not gate actions, reorder content, or imply outcomes.

---

## 3. Enforcement Points (Code-Level)

### 3.1 Write-Path Guard (Mandatory)

All Phase 3 database sessions must enforce a **write allowlist**.

**Rule**
- Allowed writes: tables matching `p3_%`
- Forbidden writes: all other tables

**Behavior**
- Any attempted write to a non-`p3_*` table:
  - Raises an internal error
  - Error is logged as a contract violation
  - Error is swallowed (no propagation)

This prevents accidental coupling at runtime.

---

### 3.2 Kill-Switch Gate (Centralized)

Every Phase 3 entrypoint must invoke a shared gate:

```sql
SELECT enabled, rollout_percent
FROM p3_feature_state
WHERE feature_name = 'p3_advisory';
```

**Rules**
- Gate executes before:
  - Any read of `analysis_results`
  - Any advisory compute
  - Any `p3_*` read or write
- If disabled or rollout-ineligible → immediate no-op

---

### 3.3 Read-Only Input Guard

Phase 3 read paths must be explicitly declared read-only.

**Allowed Reads**
- `analysis_results`
- Read-only Phase 2 tables already used by ranking

**Forbidden Reads**
- Queue state
- Retry counters
- Worker metadata
- Transient execution state

Any forbidden read is a contract violation.

---

## 4. Observability Signals (Structured)

All Phase 3 logs must:

- Be structured
- Be namespaced (e.g., `phase3.*`)
- Avoid PII
- Avoid Phase 1/2 internals

### 4.1 Required Log Events

| Event | Condition |
|-----|-----------|
| `phase3.disabled_noop` | Kill-switch blocks execution |
| `phase3.cache_hit` | Advisory reused |
| `phase3.cache_miss` | Advisory computed |
| `phase3.budget_granted` | Budget increment succeeded |
| `phase3.budget_exhausted` | Budget gate blocks compute |
| `phase3.compute_success` | Advisory written |
| `phase3.compute_error` | Compute failed (swallowed) |
| `phase3.contract_violation` | Any invariant breach |

---

### 4.2 Metrics (Minimal Set)

**Counters**
- `phase3.compute.attempted`
- `phase3.compute.completed`
- `phase3.compute.skipped.disabled`
- `phase3.compute.skipped.budget`
- `phase3.compute.failed`

**Derived Ratios**
- Cache hit rate
- Budget exhaustion rate

**Ceilings**
- Advisory compute rate must never exceed configured budgets.

---

## 5. Contract Violation Detection

### 5.1 DB-Level Audit

Run periodically or on-demand:

```sql
SELECT relname, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
WHERE relname NOT LIKE 'p3_%'
  AND (n_tup_ins > 0 OR n_tup_upd > 0 OR n_tup_del > 0);
```

**Expected**
- Zero rows attributable to Phase 3 execution windows

---

### 5.2 API Contract Audit

Verify:
- No response changes when Phase 3 is disabled
- No required fields added
- Advisory fields are optional and labeled

Any deviation is a rollback trigger.

---

### 5.3 UX Contract Audit

With Phase 3 disabled:
- No advisory UI rendered
- No layout shifts
- No placeholders or spinners

Must be verifiable via snapshot tests.

---

## 6. Alerting Thresholds (Actionable Only)

Alerts must be rare and meaningful.

| Alert | Trigger |
|-----|---------|
| Phase 3 contract violation | Any `phase3.contract_violation` |
| Non-p3 write detected | DB audit returns rows |
| Compute failure spike | Failed / attempted > 5% |
| Budget exhaustion spike | Unexpected surge vs baseline |

No alerts for:
- Cache hits
- Budget skips
- Disabled no-ops

---

## 7. Safe Failure Modes

| Failure | Behavior |
|------|----------|
| DB read error | Skip advisory |
| Compute exception | Log + skip |
| Cache conflict | Reuse existing |
| Budget exhausted | Skip |
| Kill-switch off | No-op |

**Never**
- Bubble errors to users
- Change HTTP status
- Block rendering

---

## 8. Rollback Validation

**Procedure**
1. Set `p3_feature_state.enabled=false`
2. Trigger advisory paths
3. Verify:
   - No `p3_*` writes
   - No advisory reads
   - No UI changes
   - No errors surfaced

Rollback requires no deploy.

---

## 9. Explicit Non-Goals

WS7 does **not**:
- Define advisory heuristics
- Implement caching or budgets
- Expose APIs
- Render UX
- Control rollout (WS8)

---

## 10. WS7 Completion Criteria

WS7 is complete when:
- All Phase 3 invariants are enforceable
- Violations are immediately detectable
- Kill-switch halts all behavior
- Isolation from Phase 1/2 is provable

---

## WS7 STATUS
✅ **COMPLETE — SAFE TO PROCEED**

End of WS7.

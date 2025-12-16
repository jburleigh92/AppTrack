# WS3 — Advisory Computation
**Phase:** Phase 3 (Designed, Not Implemented)  
**Work Stream:** WS3  
**Status:** Execution-ready  
**Scope:** Advisory-only computation  
**Risk Level:** Medium (compute correctness, no side effects)

---

## 1. Objective

Define **how Phase 3 advisory intelligence is computed** using **existing, authoritative match data**, while guaranteeing:

- No mutation of Phase 1 or Phase 2 state
- No influence on user_state, ranking, or workflow
- Advisory-only, non-authoritative outputs
- Deterministic, explainable computation
- Full compliance with kill-switch, cache, and budget gates

WS3 is responsible **only for computation logic**.  
It does **not** handle:
- Data population gating (WS2)
- Cache and budget mechanics (WS4)
- API exposure (WS5)
- UX rendering (WS6)

---

## 2. Hard Constraints (Non-Negotiable)

1. **Authoritative Inputs Only**
   - Advisory computation may only use persisted Phase 1/2 artifacts
   - No transient, inferred, or queue-derived data

2. **Read-Only Phase 1/2**
   - WS3 must never write to Phase 1/2 tables
   - All writes are confined to `p3_*` via WS2/WS4

3. **Advisory-Only Semantics**
   - Outputs are guidance, not truth
   - Outputs must not be interpreted as approval, rejection, or ranking

4. **No Blocking / No Retry**
   - Computation failures are swallowed
   - No retries, no backoff, no escalation

5. **Kill-Switch Supremacy**
   - If Phase 3 is disabled or rollout-ineligible, WS3 must not run

---

## 3. Authoritative Inputs (Read-Only)

### 3.1 Canonical Match Artifact (Locked)

**Table:** `analysis_results`

This table represents the **final, completed resume ↔ job match** and is the sole baseline for advisory computation.

Required fields:
- `id` (analysis_result_id)
- `resume_id`
- `job_posting_id`
- Match outputs (score, qualification lists, suggestions)
- Model/provider metadata
- `created_at`

**Rules**
- If no `analysis_results` row exists, no advisory may be computed
- WS3 must not infer matches from applications, jobs, or resumes alone

---

### 3.2 Optional Read-Only Context

WS3 may additionally read:
- `job_postings` (job age, attributes already used elsewhere)
- `applications` (timestamps only, if already used by Phase 2)

**Forbidden**
- Queue tables
- Retry counters
- Worker attempt metadata
- User interaction logs

---

## 4. Advisory Signal Model

WS3 computes **advisory signals**, each labeled by a `signal_type`.

Signal types are **labels**, not workflows.

### 4.1 Allowed Signal Types (Enumerated)

| signal_type | Description |
|------------|-------------|
| `timing_hint` | Suggests when to act (early / now / deprioritize) |
| `fit_stability` | Estimates how stable the match score is over time |
| `confidence_adjustment` | Adjusts confidence based on model reliability |
| `opportunity_risk` | Estimates downside risk of pursuing the job |

**Rules**
- New signal types require explicit Phase 3 redesign (out of scope here)
- Signal type must always be explicitly set

---

## 5. Deterministic Computation Rules

### 5.1 Pure Function Requirement

Advisory computation must be:
- Deterministic
- Side-effect free
- Repeatable for identical inputs

Formally:

```
output = f(analysis_results_row, optional_context)
```

Where:
- `f` has no external dependencies
- No randomness or time-based branching is allowed

---

### 5.2 Confidence Score Semantics

Each advisory output includes a `confidence_score`:

- Range: `[0.0, 1.0]`
- Represents *confidence in the advisory*, not correctness of the match
- Must be explainable based on inputs

Confidence score must:
- Be monotonic with respect to reliability indicators
- Never be binary (0 or 1) unless mathematically justified

---

### 5.3 Explainability Requirement

Each advisory must produce:
- A structured `signal_payload` explaining:
  - Inputs considered
  - Heuristics applied
  - Factors influencing confidence

Opaque outputs are forbidden.

---

## 6. Computation Flow (WS3 Responsibility)

WS3 computation is entered **only after WS2 gates pass**.

### Step 1 — Input Validation

Before compute:
- Confirm `analysis_result_id` exists
- Confirm required fields are present

Missing or malformed inputs → skip compute.

---

### Step 2 — Advisory Derivation

For each configured `signal_type`:

- Apply deterministic heuristics
- Produce:
  - `signal_type`
  - `signal_payload`
  - `confidence_score`
  - `model_version`
  - Optional `expires_at`

No advisory may:
- Modify existing match score
- Re-rank jobs
- Trigger workflows

---

### Step 3 — Output Handoff

WS3 returns computed advisory outputs to WS2/WS4 for persistence.

WS3 itself performs **no writes**.

---

## 7. Failure Semantics

| Failure | Behavior |
|------|----------|
| Missing input data | Skip |
| Invalid analysis row | Skip |
| Compute exception | Log + skip |
| Partial compute | Discard entirely |
| Kill-switch off | Skip |

**Never**
- Retry
- Block upstream logic
- Propagate errors

---

## 8. Model Versioning

Each advisory output must include:
- `model_version` (string)

Rules:
- Version changes intentionally invalidate cache
- Version is advisory provenance only
- Version does not affect Phase 2 behavior

---

## 9. Expiration Semantics

WS3 may optionally assign `expires_at` when:
- Advisory is time-sensitive
- Job freshness is critical

Rules:
- Expired advisories are ignored, not deleted
- Expiration does not trigger recompute

---

## 10. Verification Guidance

### Confirm advisory provenance
```sql
SELECT signal_type, confidence_score, model_version, computed_at
FROM p3_advisory_signal
ORDER BY computed_at DESC
LIMIT 10;
```

---

### Confirm no Phase 1/2 mutation
```sql
SELECT relname, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
WHERE relname NOT LIKE 'p3_%';
```

Expected: No Phase 3-attributable mutations.

---

## 11. Explicit Non-Goals

WS3 does **not**:
- Decide when advisories run (WS2)
- Enforce budgets or caching (WS4)
- Expose APIs (WS5)
- Render UI (WS6)
- Enforce contracts (WS7)

---

## 12. WS3 Completion Criteria

WS3 is complete when:
- Advisory computation is deterministic
- Outputs are explainable
- No Phase 1/2 writes occur
- Kill-switch fully suppresses computation

---

## WS3 STATUS
✅ **COMPLETE — SAFE TO PROCEED**

End of WS3.

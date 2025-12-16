# WS5 — API Exposure (Read-Only Advisory Surface)
**Phase:** Phase 3 (Designed, Not Implemented)  
**Work Stream:** WS5  
**Status:** Execution-ready  
**Scope:** Read-only advisory exposure  
**Risk Level:** Low (additive, non-blocking)

---

## 1. Objective

Expose Phase 3 advisory intelligence via APIs as **optional, non-authoritative, read-only data** that:

- Never mutates Phase 1 or Phase 2 state
- Never blocks existing responses
- Never alters user_state, ranking, or workflows
- Is fully suppressible via kill-switch
- Degrades cleanly when unavailable

This work stream defines **exposure only**. It does not define computation (WS3), caching/budgets (WS4), or UX rendering (WS6).

---

## 2. Hard Constraints (Non-Negotiable)

1. **Read-Only**
   - API handlers may only READ from `p3_*`
   - No writes during read paths

2. **No Contract Changes**
   - Existing Phase 1/2 endpoints must remain backward-compatible
   - No required fields added
   - No behavior changes when advisory is absent

3. **No New States**
   - Advisory data must not map to user_state
   - No new lifecycle or status values introduced

4. **Kill-Switch Supremacy**
   - If Phase 3 is disabled, advisory reads must be fully suppressed

5. **Fail-Open**
   - Advisory failures must never fail the request
   - Omit advisory silently on any error

---

## 3. Exposure Strategy (Non-Invasive)

### 3.1 Additive Augmentation Pattern

Advisory data is exposed as an **optional object** attached to existing responses.

- Advisory presence is optional
- Absence must not change client behavior
- Advisory object is clearly labeled as non-authoritative

---

## 4. Advisory Eligibility Rules

An advisory may be returned **only if all conditions are met**:

1. Phase 3 kill-switch enabled
2. Rollout eligibility passes
3. Advisory row exists in `p3_advisory_signal`
4. `is_active = true`
5. `expires_at IS NULL OR expires_at > now()`

Failure of any condition → advisory omitted.

---

## 5. API Shapes (Additive Only)

### 5.1 Existing Match / Analysis Endpoints

**Example Endpoint**
```
GET /applications/{application_id}/analysis
```

**Additive Response Extension**
```json
{
  "analysis": {
    "score": 0.82,
    "qualifications": ["Python", "FastAPI"],
    "metadata": {...}
  },
  "advisory": {
    "advisory_only": true,
    "generated_at": "2025-01-12T10:42:00Z",
    "signals": [
      {
        "type": "timing_hint",
        "confidence": 0.76,
        "summary": "Apply sooner rather than later",
        "details": {...},
        "model_version": "p3_v1"
      },
      {
        "type": "fit_stability",
        "confidence": 0.64,
        "summary": "Match stability is moderate",
        "details": {...},
        "model_version": "p3_v1"
      }
    ]
  }
}
```

**Rules**
- `analysis` remains authoritative
- `advisory` must never override or replace analysis fields
- Advisory object may be omitted entirely

---

### 5.2 Advisory-Only Read Endpoint (Optional)

If implemented, it must be strictly read-only and optional.

**Endpoint**
```
GET /api/v1/advisory?resume_id=...&job_posting_id=...
```

**Response**
```json
{
  "resume_id": "...",
  "job_posting_id": "...",
  "advisory_only": true,
  "signals": [
    {
      "type": "opportunity_risk",
      "confidence": 0.58,
      "summary": "Moderate downside risk",
      "details": {...},
      "model_version": "p3_v1"
    }
  ]
}
```

**HTTP Semantics**
- `200 OK` → advisory present
- `204 No Content` → no advisory available
- **Never** 404 for “not computed”
- **Never** 202 (no async implication)

---

## 6. Canonical Read Query

```sql
SELECT
  signal_type,
  confidence_score,
  signal_payload,
  model_version,
  computed_at
FROM p3_advisory_signal
WHERE resume_id = $1
  AND job_posting_id = $2
  AND is_active = true
  AND (expires_at IS NULL OR expires_at > now())
ORDER BY computed_at DESC;
```

**Notes**
- No joins to Phase 1/2 tables required
- No cache mutation on read
- Latest advisory preferred by ordering

---

## 7. Kill-Switch Enforcement (Mandatory)

Before any advisory read:

```sql
SELECT enabled, rollout_percent
FROM p3_feature_state
WHERE feature_name = 'p3_advisory';
```

Rules:
- `enabled=false` → omit advisory
- `rollout_percent=0` → omit advisory
- Rollout gating logic must be consistent with WS8

---

## 8. Error & Failure Semantics

| Condition | Behavior |
|--------|---------|
| Advisory not found | Omit advisory |
| Kill-switch disabled | Omit advisory |
| Expired advisory | Omit advisory |
| DB read error | Omit advisory + log |
| Partial payload | Omit advisory |

**Never**
- Fail request
- Change HTTP status for Phase 3 reasons
- Expose internal errors

---

## 9. Client & UX Guarantees

- Advisory content must be clearly labeled:
  - “Guidance”
  - “Prediction”
  - “Advisory only”
- Advisory presence must not:
  - Gate actions
  - Change sorting
  - Change defaults

(UX rendering specifics are defined in WS6.)

---

## 10. Verification Queries

### Confirm read-only behavior
```sql
SELECT
  relname,
  n_tup_ins,
  n_tup_upd,
  n_tup_del
FROM pg_stat_user_tables
WHERE relname LIKE 'p3_%';
```

Expected during reads:
- `n_tup_ins = 0`
- `n_tup_upd = 0`
- `n_tup_del = 0`

---

### Confirm advisory isolation
```sql
SELECT *
FROM p3_advisory_signal
LIMIT 5;
```

Advisory rows exist independently of API read success/failure.

---

## 11. Explicit Non-Goals

WS5 does **not**:
- Trigger advisory computation
- Enforce budgets or caching
- Change user_state
- Render UI
- Enforce Phase 3 contracts globally (WS7)

---

## 12. WS5 Completion Criteria

WS5 is complete when:
- Advisory data is exposed additively
- Kill-switch suppresses all advisory exposure
- No Phase 1/2 contracts are altered
- Fail-open behavior is guaranteed

---

## WS5 STATUS
✅ **COMPLETE — SAFE TO PROCEED**

End of WS5.

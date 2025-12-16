# WS6 — UX Integration (Non-Blocking, Optional Surfaces)
**Phase:** Phase 3 (Designed, Not Implemented)  
**Work Stream:** WS6  
**Status:** Execution-ready  
**Scope:** UX presentation only (non-authoritative)  
**Risk Level:** Low (additive, fail-open)

---

## 1. Objective

Integrate Phase 3 advisory outputs into the user experience as **optional, non-blocking guidance** while guaranteeing:

- No change to Phase 1/2 truth or behavior
- No new user-visible states
- No gating of actions or workflows
- Instant removal via kill-switch
- Pixel-identical UX when advisory is disabled

This work stream defines **presentation rules only**.  
It does **not** define computation (WS3), API exposure (WS5), or enforcement (WS7).

---

## 2. Non-Negotiable UX Rules

These rules apply to **all surfaces**.

1. **Advisory is Additive**
   - Advisory content may supplement, but never replace, authoritative content.
   - Match score, analysis text, and application status remain primary.

2. **No Gating**
   - No buttons, actions, or flows may depend on advisory presence.
   - Users must be able to proceed exactly as before Phase 3.

3. **No New States**
   - UI must not introduce labels like “recommended,” “unsafe,” or “high risk.”
   - Advisory content must not imply a lifecycle or status.

4. **Fail-Open**
   - If advisory data is missing, disabled, expired, or errored, the UI behaves as if Phase 3 does not exist.

---

## 3. Allowed Surfaces

### 3.1 Match / Analysis Detail View (Primary Surface)

**Location**
- Adjacent to the existing analysis content
- Must not appear above or replace the authoritative match

**Presentation Pattern**
- Collapsible panel labeled clearly (e.g., “Guidance”)
- Default state: collapsed
- User-controlled expansion only

**Content Rules**
- Display at most one summarized insight per `signal_type`
- Display confidence as:
  - Numeric (0.00–1.00), or
  - Qualitative buckets (“Low / Medium / High”)
- Show generation time (relative, not absolute if preferred)

**Example (Conceptual)**
```
Guidance (optional)
• Apply sooner rather than later (Confidence: 0.76)
• Match stability is moderate (Confidence: 0.64)
```

---

### 3.2 Job List / Card View (Secondary Surface)

**Allowed**
- Small, non-intrusive indicator (icon or badge)
- Tooltip stating “Guidance available”

**Forbidden**
- Sorting by advisory
- Reordering based on advisory
- Replacing existing labels or badges

**Performance Rule**
- Do not issue new API calls solely to fetch advisory data
- Advisory may only be shown if already present in the list payload

---

### 3.3 Advisory-Only View (Optional)

If implemented:

- Must be explicitly user-initiated
- Read-only
- No actions, CTAs, or workflow triggers
- Advisory-only labeling required

---

## 4. Kill-Switch UX Behavior

When Phase 3 is disabled:

- Advisory components are not rendered
- No placeholders or empty states
- No “loading” indicators
- UI is visually identical to pre-Phase-3

This must be verifiable via snapshot testing.

---

## 5. Copy & Language Guardrails

### Required Labels
- “Guidance”
- “Prediction”
- “Advisory only”

### Required Disclaimer (Concise)
- “This guidance is advisory only and does not affect your application.”

### Forbidden Language
- “Recommended”
- “Approved / Rejected”
- “Safe / Unsafe”
- “Guaranteed”
- “You should / must”

---

## 6. Error & Edge Handling

| Condition | UX Behavior |
|--------|-------------|
| Advisory missing | Do not render |
| Advisory expired | Do not render |
| Partial advisory payload | Do not render |
| API error | Silent omit |
| Kill-switch off | Silent omit |

**Never**
- Show error banners
- Show retry buttons
- Show spinners tied to advisory

---

## 7. Accessibility & Performance

- Advisory content must be screen-reader accessible
- Collapsible controls must be keyboard-navigable
- No layout shift when advisory loads
- No blocking render paths
- No polling or retries

---

## 8. UI-Side Instrumentation (Optional, Non-Blocking)

If analytics already exist, the UI may emit:

- `advisory_viewed`
- `advisory_expanded`
- `advisory_dismissed`

Rules:
- Fire-and-forget only
- Must not block rendering
- Must not require backend acknowledgment

---

## 9. Verification Checklist

- With Phase 3 disabled, UI is pixel-identical to baseline
- With advisory present, all actions remain unchanged
- With advisory absent, no visual gaps appear
- No new user_state or implied priority
- No performance regression on list views

---

## 10. Explicit Non-Goals

WS6 does **not**:
- Change ranking or ordering
- Gate applications
- Introduce new flows
- Display internal confidence thresholds
- Enforce Phase 3 contracts (WS7)

---

## 11. WS6 Completion Criteria

WS6 is complete when:

- Advisory surfaces are optional and non-blocking
- Kill-switch removes all Phase 3 UX instantly
- No new states or actions are introduced
- Phase 1/2 UX semantics are preserved exactly

---

## WS6 STATUS
✅ **COMPLETE — SAFE TO PROCEED**

End of WS6.

"""WS7 observability and enforcement helpers.

These utilities are intentionally additive and fail-open. They provide
structured logging for Phase 3 advisory lifecycle events and lightweight
contract enforcement signals without altering behavior or control flow.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, MutableMapping, Optional
from uuid import UUID

from app.db.models import AnalysisResult

logger = logging.getLogger(__name__)


EVENT_DISABLED_NOOP = "phase3.disabled_noop"
EVENT_CACHE_HIT = "phase3.cache_hit"
EVENT_CACHE_MISS = "phase3.cache_miss"
EVENT_BUDGET_GRANTED = "phase3.budget_granted"
EVENT_BUDGET_EXHAUSTED = "phase3.budget_exhausted"
EVENT_COMPUTE_SKIPPED_DISABLED = "phase3.compute_skipped_disabled"
EVENT_COMPUTE_ERROR = "phase3.compute_error"
EVENT_COMPUTE_SUCCESS = "phase3.compute_success"
EVENT_CONTRACT_VIOLATION = "phase3.contract_violation"
EVENT_ROLLOUT_INELIGIBLE = "phase3.rollout_ineligible"
EVENT_COMPUTE_ATTEMPTED = "phase3.compute_attempted"


def _safe_string(value: Optional[UUID | str]) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _build_context(
    *,
    analysis_result: Optional[AnalysisResult] = None,
    application_id: Optional[UUID] = None,
    analysis_id: Optional[UUID] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> MutableMapping[str, Any]:
    context: MutableMapping[str, Any] = {}

    if analysis_result:
        context.update(
            {
                "analysis_id": _safe_string(getattr(analysis_result, "id", None)),
                "application_id": _safe_string(
                    getattr(analysis_result, "application_id", None)
                ),
                "resume_id": _safe_string(getattr(analysis_result, "resume_id", None)),
                "job_posting_id": _safe_string(
                    getattr(analysis_result, "job_posting_id", None)
                ),
            }
        )

    if application_id:
        context.setdefault("application_id", _safe_string(application_id))
    if analysis_id:
        context.setdefault("analysis_id", _safe_string(analysis_id))

    if extra:
        for key, value in extra.items():
            context[key] = value

    return context


def log_phase3_event(
    event: str,
    *,
    advisory_stage: str,
    decision: str,
    reason: str,
    analysis_result: Optional[AnalysisResult] = None,
    application_id: Optional[UUID] = None,
    analysis_id: Optional[UUID] = None,
    extra: Optional[Mapping[str, Any]] = None,
    level: str = "info",
) -> None:
    payload = _build_context(
        analysis_result=analysis_result,
        application_id=application_id,
        analysis_id=analysis_id,
        extra=extra,
    )

    payload.update(
        {
            "advisory_stage": advisory_stage,
            "decision": decision,
            "reason": reason,
        }
    )

    try:
        log_fn = logger.debug if level == "debug" else logger.info
        log_fn(event, extra=payload)
    except Exception:
        logger.debug("WS7: failed to emit observability log", exc_info=True)


def log_contract_violation(
    *,
    advisory_stage: str,
    reason: str,
    analysis_result: Optional[AnalysisResult] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> None:
    log_phase3_event(
        EVENT_CONTRACT_VIOLATION,
        advisory_stage=advisory_stage,
        decision="contract_violation_logged",
        reason=reason,
        analysis_result=analysis_result,
        extra=extra,
    )


def enforce_p3_write_allowlist(
    *,
    table_name: str,
    advisory_stage: str,
    analysis_result: Optional[AnalysisResult] = None,
) -> None:
    if not table_name.startswith("p3_"):
        log_contract_violation(
            advisory_stage=advisory_stage,
            reason="write_outside_p3_table",
            analysis_result=analysis_result,
            extra={"table_name": table_name},
        )
        return

    log_phase3_event(
        "phase3.write_allowlist_ok",
        advisory_stage=advisory_stage,
        decision="allowed",
        reason="p3_write_path",
        analysis_result=analysis_result,
        extra={"table_name": table_name},
        level="debug",
    )


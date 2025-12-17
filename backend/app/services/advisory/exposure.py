"""WS5: Read-only advisory exposure helpers.

All functions in this module are best-effort and must never introduce side
effects. Failures suppress advisory output instead of surfacing errors to
callers.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models.p3 import P3AdvisorySignal, P3FeatureState
from app.services.advisory.observability import (
    EVENT_CACHE_HIT,
    EVENT_CACHE_MISS,
    EVENT_DISABLED_NOOP,
    EVENT_ROLLOUT_INELIGIBLE,
    log_contract_violation,
    log_phase3_event,
)

logger = logging.getLogger(__name__)

FEATURE_NAME = "p3_advisory"


def _deterministic_bucket(resume_id: UUID) -> int:
    digest = hashlib.sha256(resume_id.bytes).hexdigest()
    return int(digest, 16) % 100


def _is_feature_enabled(feature_state: Optional[P3FeatureState]) -> bool:
    return bool(
        feature_state
        and feature_state.enabled
        and feature_state.rollout_percent is not None
        and feature_state.rollout_percent > 0
    )


def _is_rollout_eligible(resume_id: UUID, rollout_percent: int) -> bool:
    return _deterministic_bucket(resume_id) < rollout_percent


def _safe_details(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, dict):
        return payload
    return None


def _safe_summary(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    if not payload:
        return None
    summary = payload.get("summary")
    return summary if isinstance(summary, str) else None


def _load_feature_state(db: Session) -> Optional[P3FeatureState]:
    try:
        return (
            db.query(P3FeatureState)
            .filter(P3FeatureState.feature_name == FEATURE_NAME)
            .first()
        )
    except Exception:
        logger.debug("WS5: feature state lookup failed; suppressing advisory", exc_info=True)
        return None


def get_advisory_envelope(
    db: Session, *, resume_id: UUID, job_posting_id: UUID
) -> Optional[Dict[str, Any]]:
    """Return advisory payload when available, otherwise ``None``.

    This function is read-only and must never trigger writes, population, or
    computation. Any failure returns ``None`` to keep caller flows non-blocking.
    """

    feature_state = _load_feature_state(db)
    if not _is_feature_enabled(feature_state):
        log_phase3_event(
            EVENT_DISABLED_NOOP,
            advisory_stage="exposure.kill_switch",
            decision="skip",
            reason="feature_disabled",
            extra={"resume_id": str(resume_id), "job_posting_id": str(job_posting_id)},
        )
        return None

    try:
        if not _is_rollout_eligible(resume_id, feature_state.rollout_percent):
            log_phase3_event(
                EVENT_ROLLOUT_INELIGIBLE,
                advisory_stage="exposure.rollout",
                decision="skip",
                reason="deterministic_bucket_ineligible",
                extra={
                    "resume_id": str(resume_id),
                    "job_posting_id": str(job_posting_id),
                    "rollout_percent": feature_state.rollout_percent,
                },
            )
            return None
    except Exception:
        logger.debug("WS5: rollout eligibility failed; suppressing advisory", exc_info=True)
        log_contract_violation(
            advisory_stage="exposure.rollout",
            reason="rollout_eligibility_error",
            extra={"resume_id": str(resume_id), "job_posting_id": str(job_posting_id)},
        )
        return None

    try:
        signals: List[P3AdvisorySignal] = (
            db.query(P3AdvisorySignal)
            .filter(
                P3AdvisorySignal.resume_id == resume_id,
                P3AdvisorySignal.job_posting_id == job_posting_id,
                P3AdvisorySignal.is_active == True,
                or_(
                    P3AdvisorySignal.expires_at.is_(None),
                    P3AdvisorySignal.expires_at > func.now(),
                ),
            )
            .order_by(P3AdvisorySignal.computed_at.desc())
            .all()
        )
    except Exception:
        logger.debug("WS5: advisory signal lookup failed; suppressing", exc_info=True)
        log_contract_violation(
            advisory_stage="exposure.signal_lookup",
            reason="signal_lookup_failed",
            extra={"resume_id": str(resume_id), "job_posting_id": str(job_posting_id)},
        )
        return None

    if not signals:
        log_phase3_event(
            EVENT_CACHE_MISS,
            advisory_stage="exposure.signal_lookup",
            decision="skip",
            reason="no_active_signals",
            extra={"resume_id": str(resume_id), "job_posting_id": str(job_posting_id)},
            level="debug",
        )
        return None

    log_phase3_event(
        EVENT_CACHE_HIT,
        advisory_stage="exposure.signal_lookup",
        decision="return_payload",
        reason="signals_found",
        extra={
            "resume_id": str(resume_id),
            "job_posting_id": str(job_posting_id),
            "signal_count": len(signals),
        },
        level="debug",
    )

    payload_signals: List[Dict[str, Any]] = []
    for signal in signals:
        details = _safe_details(signal.signal_payload)
        payload_signals.append(
            {
                "type": signal.signal_type,
                "confidence": float(signal.confidence_score)
                if signal.confidence_score is not None
                else None,
                "summary": _safe_summary(details),
                "details": details,
                "model_version": signal.model_version,
                "computed_at": signal.computed_at,
            }
        )

    return {
        "resume_id": resume_id,
        "job_posting_id": job_posting_id,
        "advisory_only": True,
        "generated_at": signals[0].computed_at,
        "signals": payload_signals,
    }

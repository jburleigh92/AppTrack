"""WS3 advisory computation logic.

This module implements the deterministic, side-effect-free computation
required for Phase 3 advisory signals. All functions are pure and operate
solely on in-memory data supplied by callers. No database access or other
integration concerns are introduced here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence

from app.db.models import AnalysisResult
from app.services.advisory.population import (
    AdvisoryComputationRequest,
    AdvisoryComputationResult,
)


# Model provenance for all WS3 computations. Incrementing this string should
# intentionally invalidate any downstream caches while keeping computation
# deterministic.
MODEL_VERSION = "ws3_advisory_v1"


@dataclass(frozen=True)
class AdvisoryContext:
    """Optional, read-only context for advisory computation."""

    job_posting_created_at: Optional[datetime] = None
    application_date: Optional[datetime] = None


def _safe_decimal(value: float) -> Decimal:
    """Clamp and convert a floating value into a Decimal within [0, 1]."""

    clamped = min(1.0, max(0.0, value))
    return Decimal(f"{clamped:.6f}")


def _validate_analysis(analysis_result: AnalysisResult) -> bool:
    """Lightweight validation to ensure required inputs are present."""

    if not analysis_result:
        return False

    required_fields = [
        analysis_result.id,
        analysis_result.resume_id,
        analysis_result.job_posting_id,
        analysis_result.match_score,
        analysis_result.qualifications_met,
        analysis_result.qualifications_missing,
        analysis_result.suggestions,
        analysis_result.llm_provider,
        analysis_result.llm_model,
        analysis_result.created_at,
    ]

    return all(field is not None for field in required_fields)


def _plan_requests() -> Sequence[AdvisoryComputationRequest]:
    """Define the advisory signals WS3 computes."""

    return (
        AdvisoryComputationRequest(signal_type="timing_hint", model_version=MODEL_VERSION),
        AdvisoryComputationRequest(signal_type="fit_stability", model_version=MODEL_VERSION),
        AdvisoryComputationRequest(signal_type="confidence_adjustment", model_version=MODEL_VERSION),
        AdvisoryComputationRequest(signal_type="opportunity_risk", model_version=MODEL_VERSION),
    )


def _timing_hint(
    analysis_result: AnalysisResult, context: AdvisoryContext
) -> Optional[AdvisoryComputationResult]:
    if not context.job_posting_created_at:
        return None

    job_age_days = max(
        0,
        (analysis_result.created_at.date() - context.job_posting_created_at.date()).days,
    )

    if job_age_days <= 3:
        recommendation = "apply_now"
        confidence_base = 0.78
    elif job_age_days <= 14:
        recommendation = "standard_window"
        confidence_base = 0.68
    else:
        recommendation = "deprioritize"
        confidence_base = 0.6

    payload = {
        "job_age_days": job_age_days,
        "heuristic": "recent_posting" if job_age_days <= 3 else "age_decay",
        "recommendation": recommendation,
    }

    confidence = _safe_decimal(confidence_base)

    return AdvisoryComputationResult(
        signal_type="timing_hint",
        model_version=MODEL_VERSION,
        signal_payload=payload,
        confidence_score=confidence,
    )


def _fit_stability(
    analysis_result: AnalysisResult, context: AdvisoryContext
) -> AdvisoryComputationResult:
    met = analysis_result.qualifications_met or []
    missing = analysis_result.qualifications_missing or []

    met_count = len(met)
    missing_count = len(missing)
    total = met_count + missing_count

    if total == 0:
        stability_ratio = 0.5
    else:
        stability_ratio = met_count / total

    volatility = abs(0.5 - stability_ratio)
    stability_score = 0.55 + volatility * 0.35

    payload = {
        "met_count": met_count,
        "missing_count": missing_count,
        "stability_ratio": round(stability_ratio, 3),
        "inference": "stable" if stability_ratio >= 0.5 else "volatile",
    }

    confidence = _safe_decimal(stability_score)

    return AdvisoryComputationResult(
        signal_type="fit_stability",
        model_version=MODEL_VERSION,
        signal_payload=payload,
        confidence_score=confidence,
    )


def _confidence_adjustment(
    analysis_result: AnalysisResult, context: AdvisoryContext
) -> AdvisoryComputationResult:
    provider_weights = {
        "openai": 0.15,
        "anthropic": 0.14,
        "azure": 0.12,
    }

    provider_key = (analysis_result.llm_provider or "").lower()
    provider_bonus = provider_weights.get(provider_key, 0.1)

    match_component = min(1.0, analysis_result.match_score / 100) * 0.4
    payload = {
        "llm_provider": analysis_result.llm_provider,
        "llm_model": analysis_result.llm_model,
        "match_score": analysis_result.match_score,
        "provider_bonus": round(provider_bonus, 3),
    }

    confidence = _safe_decimal(0.5 + provider_bonus + match_component)

    return AdvisoryComputationResult(
        signal_type="confidence_adjustment",
        model_version=MODEL_VERSION,
        signal_payload=payload,
        confidence_score=confidence,
    )


def _opportunity_risk(
    analysis_result: AnalysisResult, context: AdvisoryContext
) -> AdvisoryComputationResult:
    missing = analysis_result.qualifications_missing or []
    met = analysis_result.qualifications_met or []

    missing_count = len(missing)
    met_count = len(met)

    if missing_count == 0 and met_count == 0:
        risk_level = "medium"
        confidence_base = 0.55
    elif missing_count > met_count:
        risk_level = "high"
        confidence_base = 0.7
    elif analysis_result.match_score >= 75:
        risk_level = "low"
        confidence_base = 0.72
    else:
        risk_level = "medium"
        confidence_base = 0.64

    payload = {
        "missing_count": missing_count,
        "met_count": met_count,
        "match_score": analysis_result.match_score,
        "risk_level": risk_level,
    }

    confidence = _safe_decimal(confidence_base)

    return AdvisoryComputationResult(
        signal_type="opportunity_risk",
        model_version=MODEL_VERSION,
        signal_payload=payload,
        confidence_score=confidence,
    )


def compute_advisories(
    analysis_result: AnalysisResult,
    *,
    context: Optional[AdvisoryContext] = None,
) -> list[AdvisoryComputationResult]:
    """
    Primary WS3 computation entrypoint.

    Accepts a fully populated ``AnalysisResult`` plus optional read-only
    context and returns advisory computation outputs. All failures are
    swallowed and expressed as empty results to satisfy the WS3 silent
    failure contract.
    """

    context = context or AdvisoryContext()

    try:
        if not _validate_analysis(analysis_result):
            return []

        results: list[AdvisoryComputationResult] = []
        for request in _plan_requests():
            if request.signal_type == "timing_hint":
                computed = _timing_hint(analysis_result, context)
            elif request.signal_type == "fit_stability":
                computed = _fit_stability(analysis_result, context)
            elif request.signal_type == "confidence_adjustment":
                computed = _confidence_adjustment(analysis_result, context)
            elif request.signal_type == "opportunity_risk":
                computed = _opportunity_risk(analysis_result, context)
            else:
                computed = None

            if computed:
                results.append(computed)

        return results
    except Exception:
        return []


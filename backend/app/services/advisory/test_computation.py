from datetime import datetime
from uuid import uuid4

import pytest

from app.db.models import AnalysisResult
from app.services.advisory import AdvisoryContext, compute_advisories


def _make_analysis_result(**overrides) -> AnalysisResult:
    base = dict(
        id=uuid4(),
        application_id=uuid4(),
        resume_id=uuid4(),
        job_posting_id=uuid4(),
        match_score=82,
        qualifications_met=["skill_a", "skill_b"],
        qualifications_missing=["skill_c"],
        suggestions=["suggestion"],
        llm_provider="OpenAI",
        llm_model="gpt-4",
        analysis_metadata={},
        created_at=datetime(2024, 1, 10),
    )

    base.update(overrides)
    return AnalysisResult(**base)


def test_compute_advisories_with_full_context_generates_all_signals():
    analysis = _make_analysis_result()
    context = AdvisoryContext(job_posting_created_at=datetime(2024, 1, 1))

    results = compute_advisories(analysis, context=context)

    assert {result.signal_type for result in results} == {
        "timing_hint",
        "fit_stability",
        "confidence_adjustment",
        "opportunity_risk",
    }

    timing_hint = next(r for r in results if r.signal_type == "timing_hint")
    assert timing_hint.signal_payload["recommendation"] == "standard_window"
    assert 0 < float(timing_hint.confidence_score) <= 1


def test_compute_advisories_without_job_context_skips_timing_hint():
    analysis = _make_analysis_result()
    context = AdvisoryContext()

    results = compute_advisories(analysis, context=context)

    assert {result.signal_type for result in results} == {
        "fit_stability",
        "confidence_adjustment",
        "opportunity_risk",
    }


def test_invalid_analysis_returns_empty_results():
    invalid_analysis = _make_analysis_result(match_score=None)

    results = compute_advisories(invalid_analysis, context=AdvisoryContext())

    assert results == []

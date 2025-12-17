import hashlib
import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Protocol, Sequence
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import AnalysisResult
from app.db.models.p3 import (
    P3AdvisoryBudget,
    P3AdvisoryCache,
    P3AdvisorySignal,
    P3FeatureState,
)

logger = logging.getLogger(__name__)


DEFAULT_MAX_ADVISORIES = 1
FEATURE_NAME = "p3_advisory"
EVENT_CACHE_HIT = "phase3.cache_hit"
EVENT_CACHE_MISS = "phase3.cache_miss"
EVENT_BUDGET_GRANTED = "phase3.budget_granted"
EVENT_BUDGET_EXHAUSTED = "phase3.budget_exhausted"
EVENT_COMPUTE_SKIPPED_DISABLED = "phase3.compute_skipped_disabled"
EVENT_COMPUTE_ERROR = "phase3.compute_error"


@dataclass(frozen=True)
class AdvisoryComputationRequest:
    signal_type: str
    model_version: str


@dataclass(frozen=True)
class AdvisoryComputationResult(AdvisoryComputationRequest):
    signal_payload: dict
    confidence_score: Decimal
    expires_at: Optional[datetime] = None


class AdvisoryComputer(Protocol):
    def plan(self, analysis_result: AnalysisResult) -> Sequence[AdvisoryComputationRequest]:
        ...

    def compute(
        self,
        analysis_result: AnalysisResult,
        request: AdvisoryComputationRequest,
    ) -> Optional[AdvisoryComputationResult]:
        ...


class NoOpAdvisoryComputer:
    def plan(self, analysis_result: AnalysisResult) -> Sequence[AdvisoryComputationRequest]:
        return []

    def compute(
        self,
        analysis_result: AnalysisResult,
        request: AdvisoryComputationRequest,
    ) -> Optional[AdvisoryComputationResult]:
        return None


def _deterministic_bucket(resume_id: UUID) -> int:
    digest = hashlib.sha256(resume_id.bytes).hexdigest()
    return int(digest, 16) % 100


def _log_event(event: str, **context: object) -> None:
    try:
        if context:
            logger.info("%s %s", event, context)
        else:
            logger.info(event)
    except Exception:
        logger.debug("WS4: failed to log event", exc_info=True)


def _cache_key(analysis_result_id: UUID, signal_type: str, model_version: str) -> str:
    raw_key = f"{analysis_result_id}{signal_type}{model_version}".encode("utf-8")
    return hashlib.sha256(raw_key).hexdigest()


def _is_feature_enabled(feature_state: Optional[P3FeatureState]) -> bool:
    return bool(
        feature_state
        and feature_state.enabled
        and feature_state.rollout_percent is not None
        and feature_state.rollout_percent > 0
    )


def _is_rollout_eligible(resume_id: UUID, rollout_percent: int) -> bool:
    return _deterministic_bucket(resume_id) < rollout_percent


def _ensure_budget(
    db: Session, *, resume_id: UUID, max_advisories: int
) -> bool:
    try:
        insert_stmt = (
            insert(P3AdvisoryBudget)
            .values(
                resume_id=resume_id,
                budget_day=date.today(),
                max_advisories=max_advisories,
                used_advisories=0,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    P3AdvisoryBudget.resume_id,
                    P3AdvisoryBudget.budget_day,
                ]
            )
        )

        db.execute(insert_stmt)
        db.flush()
        return True
    except Exception:
        logger.debug("WS2: budget initialization failed; skipping", exc_info=True)
        return False


def _consume_budget(db: Session, *, resume_id: UUID) -> bool:
    try:
        update_stmt = (
            update(P3AdvisoryBudget)
            .where(
                P3AdvisoryBudget.resume_id == resume_id,
                P3AdvisoryBudget.budget_day == date.today(),
                P3AdvisoryBudget.used_advisories < P3AdvisoryBudget.max_advisories,
            )
            .values(used_advisories=P3AdvisoryBudget.used_advisories + 1)
        )

        result = db.execute(update_stmt)
        granted = result.rowcount == 1
        _log_event(
            EVENT_BUDGET_GRANTED if granted else EVENT_BUDGET_EXHAUSTED,
            budget_day=str(date.today()),
        )
        return granted
    except Exception:
        logger.debug("WS2: budget consumption failed; skipping", exc_info=True)
        return False


def _select_cache(
    db: Session, *, cache_key: str
) -> tuple[Optional[P3AdvisoryCache], bool]:
    try:
        cache = (
            db.query(P3AdvisoryCache)
            .filter(P3AdvisoryCache.cache_key == cache_key)
            .first()
        )
        _log_event(EVENT_CACHE_HIT if cache else EVENT_CACHE_MISS, cache_key=cache_key)
        return cache, True
    except Exception:
        logger.debug("WS2: cache lookup failed; skipping", exc_info=True)
        return None, False


def _persist_signal(
    db: Session,
    *,
    analysis_result: AnalysisResult,
    compute_result: AdvisoryComputationResult,
    cache_key: str,
) -> None:
    try:
        signal = P3AdvisorySignal(
            resume_id=analysis_result.resume_id,
            job_posting_id=analysis_result.job_posting_id,
            signal_type=compute_result.signal_type,
            signal_payload=compute_result.signal_payload,
            confidence_score=compute_result.confidence_score,
            model_version=compute_result.model_version,
            expires_at=compute_result.expires_at,
        )

        db.add(signal)
        db.flush()

        cache_insert = (
            insert(P3AdvisoryCache)
            .values(cache_key=cache_key, signal_id=signal.id)
            .on_conflict_do_nothing(index_elements=[P3AdvisoryCache.cache_key])
        )

        result = db.execute(cache_insert)

        if result.rowcount == 0:
            db.delete(signal)
            db.flush()
            _select_cache(db, cache_key=cache_key)
    except Exception:
        logger.debug("WS2: signal persistence failed; skipping", exc_info=True)
        db.rollback()


def populate_advisories_ws2(
    db: Session,
    *,
    analysis_result: AnalysisResult,
    computer: AdvisoryComputer,
    max_advisories: int = DEFAULT_MAX_ADVISORIES,
) -> None:
    try:
        feature_state = (
            db.query(P3FeatureState)
            .filter(P3FeatureState.feature_name == FEATURE_NAME)
            .first()
        )
    except Exception:
        logger.debug("WS2: feature state lookup failed; skipping", exc_info=True)
        return

    if not _is_feature_enabled(feature_state):
        _log_event(EVENT_COMPUTE_SKIPPED_DISABLED)
        return

    if not _is_rollout_eligible(
        analysis_result.resume_id, feature_state.rollout_percent
    ):
        return

    try:
        planned_requests = list(computer.plan(analysis_result) or [])
    except Exception:
        logger.debug("WS2: computation planning failed; skipping", exc_info=True)
        return

    if not planned_requests:
        return

    for request in planned_requests:
        try:
            cache_key = _cache_key(
                analysis_result.id, request.signal_type, request.model_version
            )
        except Exception:
            logger.debug("WS2: cache key generation failed; skipping", exc_info=True)
            continue

        existing_cache, cache_lookup_ok = _select_cache(db, cache_key=cache_key)
        if not cache_lookup_ok:
            continue

        if existing_cache:
            continue

        if not _ensure_budget(db, resume_id=analysis_result.resume_id, max_advisories=max_advisories):
            continue

        if not _consume_budget(db, resume_id=analysis_result.resume_id):
            continue

        try:
            compute_result = computer.compute(analysis_result, request)
        except Exception:
            _log_event(EVENT_COMPUTE_ERROR, signal_type=request.signal_type)
            logger.debug("WS2: computation failed; skipping", exc_info=True)
            continue

        if not compute_result:
            continue

        _persist_signal(
            db,
            analysis_result=analysis_result,
            compute_result=compute_result,
            cache_key=cache_key,
        )


class AdvisoryPopulator:
    def __init__(self, computer: AdvisoryComputer, max_advisories: int = DEFAULT_MAX_ADVISORIES):
        self.computer = computer
        self.max_advisories = max_advisories

    def populate_from_analysis(self, db: Session, analysis_result: AnalysisResult) -> None:
        try:
            populate_advisories_ws2(
                db,
                analysis_result=analysis_result,
                computer=self.computer,
                max_advisories=self.max_advisories,
            )
        except Exception:
            logger.debug("WS2: population failed; skipping", exc_info=True)
            db.rollback()

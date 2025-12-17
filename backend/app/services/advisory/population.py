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
from app.services.advisory.observability import (
    EVENT_BUDGET_EXHAUSTED,
    EVENT_BUDGET_GRANTED,
    EVENT_CACHE_HIT,
    EVENT_CACHE_MISS,
    EVENT_COMPUTE_ATTEMPTED,
    EVENT_COMPUTE_ERROR,
    EVENT_COMPUTE_SUCCESS,
    EVENT_CONTRACT_VIOLATION,
    EVENT_DISABLED_NOOP,
    EVENT_ROLLOUT_INELIGIBLE,
    enforce_p3_write_allowlist,
    log_contract_violation,
    log_phase3_event,
)

logger = logging.getLogger(__name__)


DEFAULT_MAX_ADVISORIES = 1
FEATURE_NAME = "p3_advisory"


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
    db: Session,
    *,
    resume_id: UUID,
    max_advisories: int,
    analysis_result: Optional[AnalysisResult] = None,
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

        enforce_p3_write_allowlist(
            table_name=P3AdvisoryBudget.__tablename__,
            advisory_stage="population.budget_init",
            analysis_result=analysis_result,
        )

        db.execute(insert_stmt)
        db.flush()
        return True
    except Exception:
        logger.debug("WS2: budget initialization failed; skipping", exc_info=True)
        return False


def _consume_budget(
    db: Session, *, resume_id: UUID, analysis_result: Optional[AnalysisResult] = None
) -> bool:
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

        enforce_p3_write_allowlist(
            table_name=P3AdvisoryBudget.__tablename__,
            advisory_stage="population.budget_consume",
            analysis_result=analysis_result,
        )

        result = db.execute(update_stmt)
        granted = result.rowcount == 1
        log_phase3_event(
            EVENT_BUDGET_GRANTED if granted else EVENT_BUDGET_EXHAUSTED,
            advisory_stage="population.budget_consume",
            decision="granted" if granted else "skipped",
            reason="budget_consumed" if granted else "budget_exhausted",
            analysis_result=analysis_result,
            extra={"budget_day": str(date.today())},
        )
        return granted
    except Exception:
        logger.debug("WS2: budget consumption failed; skipping", exc_info=True)
        return False


def _select_cache(
    db: Session,
    *,
    cache_key: str,
    analysis_result: Optional[AnalysisResult] = None,
) -> tuple[Optional[P3AdvisoryCache], bool]:
    try:
        cache = (
            db.query(P3AdvisoryCache)
            .filter(P3AdvisoryCache.cache_key == cache_key)
            .first()
        )
        log_phase3_event(
            EVENT_CACHE_HIT if cache else EVENT_CACHE_MISS,
            advisory_stage="population.cache_lookup",
            decision="cache_hit" if cache else "cache_miss",
            reason="cache_reused" if cache else "cache_absent",
            analysis_result=analysis_result,
            extra={"cache_key": cache_key},
        )
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

        enforce_p3_write_allowlist(
            table_name=P3AdvisorySignal.__tablename__,
            advisory_stage="population.persist_signal",
            analysis_result=analysis_result,
        )

        db.add(signal)
        db.flush()

        cache_insert = (
            insert(P3AdvisoryCache)
            .values(cache_key=cache_key, signal_id=signal.id)
            .on_conflict_do_nothing(index_elements=[P3AdvisoryCache.cache_key])
        )

        enforce_p3_write_allowlist(
            table_name=P3AdvisoryCache.__tablename__,
            advisory_stage="population.persist_cache",
            analysis_result=analysis_result,
        )

        result = db.execute(cache_insert)

        if result.rowcount == 0:
            db.delete(signal)
            db.flush()
            _select_cache(db, cache_key=cache_key, analysis_result=analysis_result)

        log_phase3_event(
            EVENT_COMPUTE_SUCCESS,
            advisory_stage="population.persist_signal",
            decision="persisted",
            reason="signal_computed",
            analysis_result=analysis_result,
            extra={
                "signal_type": compute_result.signal_type,
                "cache_key": cache_key,
                "model_version": compute_result.model_version,
            },
        )
    except Exception:
        logger.debug("WS2: signal persistence failed; skipping", exc_info=True)
        log_contract_violation(
            advisory_stage="population.persist_signal",
            reason="persistence_failure",
            analysis_result=analysis_result,
            extra={"cache_key": cache_key},
        )
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
        log_phase3_event(
            EVENT_CONTRACT_VIOLATION,
            advisory_stage="population.feature_state",
            decision="skip",
            reason="feature_state_lookup_failed",
            analysis_result=analysis_result,
        )
        return

    if not _is_feature_enabled(feature_state):
        log_phase3_event(
            EVENT_DISABLED_NOOP,
            advisory_stage="population.kill_switch",
            decision="skip",
            reason="feature_disabled",
            analysis_result=analysis_result,
        )
        return

    if not _is_rollout_eligible(
        analysis_result.resume_id, feature_state.rollout_percent
    ):
        log_phase3_event(
            EVENT_ROLLOUT_INELIGIBLE,
            advisory_stage="population.rollout",
            decision="skip",
            reason="deterministic_bucket_ineligible",
            analysis_result=analysis_result,
            extra={"rollout_percent": feature_state.rollout_percent},
        )
        return

    try:
        planned_requests = list(computer.plan(analysis_result) or [])
    except Exception:
        logger.debug("WS2: computation planning failed; skipping", exc_info=True)
        log_phase3_event(
            EVENT_CONTRACT_VIOLATION,
            advisory_stage="population.plan",
            decision="skip",
            reason="computation_planning_failed",
            analysis_result=analysis_result,
        )
        return

    if not planned_requests:
        log_phase3_event(
            EVENT_CONTRACT_VIOLATION,
            advisory_stage="population.plan",
            decision="skip",
            reason="no_planned_requests",
            analysis_result=analysis_result,
        )
        return

    for request in planned_requests:
        try:
            cache_key = _cache_key(
                analysis_result.id, request.signal_type, request.model_version
            )
        except Exception:
            logger.debug("WS2: cache key generation failed; skipping", exc_info=True)
            log_phase3_event(
                EVENT_CONTRACT_VIOLATION,
                advisory_stage="population.cache_key",
                decision="skip",
                reason="cache_key_generation_failed",
                analysis_result=analysis_result,
                extra={"signal_type": request.signal_type},
            )
            continue

        existing_cache, cache_lookup_ok = _select_cache(
            db, cache_key=cache_key, analysis_result=analysis_result
        )
        if not cache_lookup_ok:
            log_phase3_event(
                EVENT_CONTRACT_VIOLATION,
                advisory_stage="population.cache_lookup",
                decision="skip",
                reason="cache_lookup_failed",
                analysis_result=analysis_result,
                extra={"cache_key": cache_key},
            )
            continue

        if existing_cache:
            log_phase3_event(
                EVENT_CACHE_HIT,
                advisory_stage="population.cache_lookup",
                decision="reuse",
                reason="cache_entry_exists",
                analysis_result=analysis_result,
                extra={"cache_key": cache_key},
            )
            continue

        if not _ensure_budget(
            db,
            resume_id=analysis_result.resume_id,
            max_advisories=max_advisories,
            analysis_result=analysis_result,
        ):
            log_phase3_event(
                EVENT_CONTRACT_VIOLATION,
                advisory_stage="population.budget_init",
                decision="skip",
                reason="budget_initialization_failed",
                analysis_result=analysis_result,
            )
            continue

        if not _consume_budget(
            db, resume_id=analysis_result.resume_id, analysis_result=analysis_result
        ):
            log_phase3_event(
                EVENT_BUDGET_EXHAUSTED,
                advisory_stage="population.budget_consume",
                decision="skip",
                reason="budget_not_granted",
                analysis_result=analysis_result,
            )
            continue

        try:
            log_phase3_event(
                EVENT_COMPUTE_ATTEMPTED,
                advisory_stage="population.compute",
                decision="attempt",
                reason="compute_invoked",
                analysis_result=analysis_result,
                extra={
                    "signal_type": request.signal_type,
                    "model_version": request.model_version,
                },
                level="debug",
            )
            compute_result = computer.compute(analysis_result, request)
        except Exception:
            log_phase3_event(
                EVENT_COMPUTE_ERROR,
                advisory_stage="population.compute",
                decision="skip",
                reason="compute_error",
                analysis_result=analysis_result,
                extra={"signal_type": request.signal_type},
            )
            logger.debug("WS2: computation failed; skipping", exc_info=True)
            continue

        if not compute_result:
            log_phase3_event(
                EVENT_CONTRACT_VIOLATION,
                advisory_stage="population.compute",
                decision="skip",
                reason="no_compute_result",
                analysis_result=analysis_result,
                extra={"signal_type": request.signal_type},
            )
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

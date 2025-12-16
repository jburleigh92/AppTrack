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


class AdvisoryPopulator:
    def __init__(self, computer: AdvisoryComputer, max_advisories: int = DEFAULT_MAX_ADVISORIES):
        self.computer = computer
        self.max_advisories = max_advisories

    def populate_from_analysis(self, db: Session, analysis_result: AnalysisResult) -> None:
        try:
            feature_state = db.query(P3FeatureState).filter(
                P3FeatureState.feature_name == FEATURE_NAME
            ).first()

            if not feature_state or not feature_state.enabled or feature_state.rollout_percent == 0:
                return

            if _deterministic_bucket(analysis_result.resume_id) >= feature_state.rollout_percent:
                return

            planned_requests = list(self.computer.plan(analysis_result) or [])
            if not planned_requests:
                return

            for request in planned_requests:
                cache_key = _cache_key(analysis_result.id, request.signal_type, request.model_version)

                existing_cache = db.query(P3AdvisoryCache).filter(
                    P3AdvisoryCache.cache_key == cache_key
                ).first()
                if existing_cache:
                    continue

                self._ensure_budget(db=db, resume_id=analysis_result.resume_id)

                if not self._consume_budget(db=db, resume_id=analysis_result.resume_id):
                    continue

                compute_result = self.computer.compute(analysis_result, request)
                if not compute_result:
                    continue

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

                cache_insert = insert(P3AdvisoryCache).values(
                    cache_key=cache_key,
                    signal_id=signal.id,
                ).on_conflict_do_nothing(index_elements=[P3AdvisoryCache.cache_key])

                result = db.execute(cache_insert)
                if result.rowcount == 0:
                    db.delete(signal)
                    db.flush()

            db.commit()
        except Exception:
            logger.exception("Phase 3 advisory population failed; skipping")
            db.rollback()

    def _ensure_budget(self, db: Session, resume_id: UUID) -> None:
        insert_stmt = insert(P3AdvisoryBudget).values(
            resume_id=resume_id,
            budget_day=date.today(),
            max_advisories=self.max_advisories,
            used_advisories=0,
        ).on_conflict_do_nothing(index_elements=[P3AdvisoryBudget.resume_id, P3AdvisoryBudget.budget_day])

        db.execute(insert_stmt)
        db.flush()

    def _consume_budget(self, db: Session, resume_id: UUID) -> bool:
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
        return result.rowcount == 1

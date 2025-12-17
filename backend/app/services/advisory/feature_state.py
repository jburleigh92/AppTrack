from __future__ import annotations

import hashlib
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.p3 import P3FeatureState

logger = logging.getLogger(__name__)

FEATURE_NAME = "p3_advisory"


def _deterministic_bucket(resume_id: UUID) -> int:
    digest = hashlib.sha256(resume_id.bytes).hexdigest()
    return int(digest, 16) % 100


def is_kill_switch_engaged(feature_state: Optional[P3FeatureState]) -> bool:
    return not (feature_state and feature_state.enabled)


def is_rollout_configured(feature_state: Optional[P3FeatureState]) -> bool:
    return bool(
        feature_state
        and feature_state.enabled
        and feature_state.rollout_percent is not None
        and feature_state.rollout_percent > 0
    )


def rollout_percent(feature_state: Optional[P3FeatureState]) -> int:
    if feature_state and feature_state.rollout_percent is not None:
        return int(feature_state.rollout_percent)
    return 0


def is_rollout_eligible(resume_id: UUID, feature_state: Optional[P3FeatureState]) -> bool:
    if not is_rollout_configured(feature_state):
        return False
    return _deterministic_bucket(resume_id) < int(feature_state.rollout_percent)


def load_feature_state(db: Session) -> Optional[P3FeatureState]:
    try:
        return (
            db.query(P3FeatureState)
            .filter(P3FeatureState.feature_name == FEATURE_NAME)
            .first()
        )
    except Exception:
        logger.debug("WS8: feature state lookup failed; failing closed", exc_info=True)
        return None

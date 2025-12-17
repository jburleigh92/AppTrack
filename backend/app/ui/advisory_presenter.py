"""WS6 advisory presentation helpers.

These helpers produce optional, non-blocking view models that can be
rendered by any UI layer without changing backend behavior. They implement
Phase 3 guidance rules by failing open when advisory data is missing,
disabled, or incomplete.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.schemas.advisory import AdvisoryEnvelope, AdvisorySignal

REQUIRED_DISCLAIMER = "This guidance is advisory only and does not affect your application."


def _confidence_bucket(confidence: Optional[float]) -> Optional[str]:
    """Return a qualitative bucket for the given confidence.

    WS6 allows either numeric or qualitative confidence. We expose both when
    confidence is available and silently skip when it is not.
    """

    if confidence is None:
        return None

    if confidence < 0.34:
        return "Low"
    if confidence < 0.67:
        return "Medium"
    return "High"


def _format_signal(signal: AdvisorySignal) -> Optional[Dict[str, Any]]:
    """Format a single advisory signal for UI consumption.

    Returns None when the payload is incomplete, satisfying the WS6 rule to
    suppress partial advisory data.
    """

    try:
        if not signal.summary:
            return None

        bucket = _confidence_bucket(signal.confidence)
        confidence_text = None
        if signal.confidence is not None:
            confidence_text = f"{signal.confidence:.2f}"
            if bucket:
                confidence_text = f"{confidence_text} ({bucket})"

        computed_at = signal.computed_at.isoformat() if signal.computed_at else None

        return {
            "signal_type": signal.type,
            "summary": signal.summary,
            "confidence": confidence_text,
            "computed_at": computed_at,
        }
    except Exception:
        return None


def _dedupe_signals(signals: List[AdvisorySignal]) -> List[AdvisorySignal]:
    """Return at most one signal per type, preserving order."""

    seen = set()
    deduped: List[AdvisorySignal] = []
    for signal in signals:
        if signal.type in seen:
            continue
        seen.add(signal.type)
        deduped.append(signal)
    return deduped


def build_guidance_panel(
    advisory: Optional[AdvisoryEnvelope],
    *,
    advisory_enabled: bool = True,
) -> Optional[Dict[str, Any]]:
    """Build the collapsible guidance panel view model.

    - Default collapsed
    - Fails open (returns None) when advisory is disabled, absent, or
      incomplete
    - Includes required labels and disclaimer text
    - Never blocks caller behavior
    """

    if not advisory_enabled:
        return None

    if not advisory or not advisory.signals:
        return None

    signals = _dedupe_signals(advisory.signals)
    formatted_signals = []
    for signal in signals:
        formatted = _format_signal(signal)
        if formatted:
            formatted_signals.append(formatted)

    if not formatted_signals:
        # Partial or invalid payloads are treated as absent
        return None

    generated_at = (
        advisory.generated_at.isoformat() if isinstance(advisory.generated_at, datetime) else None
    )

    return {
        "label": "Guidance (optional)",
        "collapsed_by_default": True,
        "advisory_only": True,
        "disclaimer": REQUIRED_DISCLAIMER,
        "generated_at": generated_at,
        "items": formatted_signals,
    }


def build_job_card_indicator(
    advisory: Optional[AdvisoryEnvelope],
    *,
    advisory_enabled: bool = True,
) -> Optional[Dict[str, str]]:
    """Return a minimal badge/tooltip model for job cards.

    The indicator is only returned when advisory content is present and
    enabled. It avoids additional lookups by assuming the caller already has
    the advisory payload from its existing data fetch.
    """

    if not advisory_enabled:
        return None

    if not advisory or not advisory.signals:
        return None

    return {
        "label": "Guidance available",
        "tooltip": "Guidance available (advisory only)",
        "advisory_only": "true",
        "disclaimer": REQUIRED_DISCLAIMER,
    }

"""Lightweight demo renders for WS6 advisory presentation.

This script simulates three scenarios:
- Advisory absent (panel/indicator hidden)
- Advisory present (panel populated, indicator shown)
- Advisory disabled (kill-switch removes all Phase 3 UX)

It exercises presentation helpers only; no database writes or API
contract changes are performed.
"""

from datetime import datetime
from uuid import uuid4

from app.schemas.advisory import AdvisoryEnvelope, AdvisorySignal
from app.ui.advisory_presenter import build_guidance_panel, build_job_card_indicator


def _sample_envelope(with_signal: bool = True) -> AdvisoryEnvelope:
    signals = []
    if with_signal:
        signals.append(
            AdvisorySignal(
                type="timing",
                confidence=0.76,
                summary="Apply sooner rather than later",
                details={"urgency": "medium"},
                model_version="ws3_advisory_v1",
                computed_at=datetime.utcnow(),
            )
        )
        signals.append(
            AdvisorySignal(
                type="stability",
                confidence=0.64,
                summary="Match stability is moderate",
                model_version="ws3_advisory_v1",
                computed_at=datetime.utcnow(),
            )
        )

    return AdvisoryEnvelope(
        resume_id=uuid4(),
        job_posting_id=uuid4(),
        generated_at=datetime.utcnow(),
        signals=signals,
    )


def _render(label: str, advisory: AdvisoryEnvelope | None, enabled: bool = True) -> None:
    panel = build_guidance_panel(advisory, advisory_enabled=enabled)
    indicator = build_job_card_indicator(advisory, advisory_enabled=enabled)

    print(f"\n=== {label} ===")
    print("Detail view panel:", panel or "hidden (no advisory rendered)")
    print("Job card indicator:", indicator or "hidden (no advisory rendered)")


if __name__ == "__main__":
    _render("Advisory absent", _sample_envelope(with_signal=False))
    _render("Advisory present", _sample_envelope(with_signal=True))
    _render("Advisory disabled", _sample_envelope(with_signal=True), enabled=False)

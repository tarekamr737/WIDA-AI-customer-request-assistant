"""Human-review actions over an existing processed request."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from src.models import AIAnalysis, validate_analysis_service_ids
from src.processor import ProcessingOutcome, build_internal_summary
from src.renderer import render_internal_summary
from src.storage import DEFAULT_RESULTS_PATH, update_request


def approve_request(
    outcome: ProcessingOutcome,
    edited_analysis: AIAnalysis,
    *,
    results_path: Path = DEFAULT_RESULTS_PATH,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> ProcessingOutcome:
    """Validate reviewer edits, recompute deterministic output, and approve one row."""

    validate_analysis_service_ids(edited_analysis, list(outcome.references.services))
    summary = build_internal_summary(
        edited_analysis,
        outcome.references,
        outcome.request.raw_request,
    ).model_copy(update={"review_status": "تمت المراجعة"})
    rendered = render_internal_summary(summary, outcome.references.raw_template_text)
    updated_request = outcome.request.model_copy(
        update={
            "updated_at": now(),
            "analysis": edited_analysis,
            "summary": summary,
        }
    )
    update_request(updated_request, results_path)
    return ProcessingOutcome(
        request=updated_request,
        rendered_summary=rendered,
        references=outcome.references,
    )

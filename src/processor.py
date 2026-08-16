"""Orchestrate one grounded request-processing run."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from src.llm_client import AnalysisClient
from src.models import (
    AIAnalysis,
    InternalSummary,
    ProcessedRequest,
    ReferenceData,
    ServiceDefinition,
    validate_analysis_service_ids,
)
from src.policy_engine import (
    commercial_register_status,
    evaluate_policies,
    find_missing_data,
)
from src.reference_loader import DEFAULT_REFERENCE_DIR, load_references
from src.renderer import render_internal_summary
from src.storage import DEFAULT_RESULTS_PATH, append_request


@dataclass(frozen=True)
class ProcessingOutcome:
    request: ProcessedRequest
    rendered_summary: str
    references: ReferenceData


def _service_display(
    service_id: int | None,
    services: tuple[ServiceDefinition, ...],
    *,
    fallback: str,
) -> str:
    if service_id is None:
        return fallback
    service = next(service for service in services if service.id == service_id)
    return f"{service.id}. {service.name}"


def _contact_display(analysis: AIAnalysis) -> str:
    if analysis.contact_name is None and analysis.contact_role is None:
        return "غير مذكور"
    name = analysis.contact_name or "الاسم غير مذكور"
    role = analysis.contact_role or "الصفة غير مذكورة"
    return f"{name} - {role}"


def _build_summary(
    analysis: AIAnalysis, references: ReferenceData, raw_request: str
) -> InternalSummary:
    missing_data = find_missing_data(analysis)
    policy = evaluate_policies(
        analysis,
        references.services,
        references.global_min_execution_days,
        raw_request=raw_request,
        missing_data=missing_data,
    )
    primary_fallback = (
        "خارج النطاق"
        if analysis.classification_state == "out_of_scope"
        else "غير محدد"
    )
    return InternalSummary(
        organization_name=analysis.organization_name or "غير مذكور",
        contact_person_and_role=_contact_display(analysis),
        contact_method=analysis.contact_method or "غير مذكور",
        need_summary=analysis.need_summary,
        primary_service=_service_display(
            analysis.primary_service_id,
            references.services,
            fallback=primary_fallback,
        ),
        secondary_service=_service_display(
            analysis.secondary_service_id,
            references.services,
            fallback="لا توجد",
        ),
        commercial_register=commercial_register_status(
            analysis.commercial_register_text
        ),
        requested_deadline=analysis.requested_deadline_text or "غير محدد",
        policy_status=policy.status,
        missing_data=missing_data,
        alerts=policy.alerts,
        next_step=policy.next_step,
        review_status="بانتظار المراجعة",
    )


def process_request(
    raw_request: str,
    input_source: str,
    llm_client: AnalysisClient,
    *,
    reference_dir: Path = DEFAULT_REFERENCE_DIR,
    results_path: Path = DEFAULT_RESULTS_PATH,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    new_request_id: Callable[[], str] = lambda: str(uuid4()),
) -> ProcessingOutcome:
    """Process, render, and auto-save one request as pending review."""

    normalized_request = raw_request.strip()
    if not normalized_request:
        raise ValueError("نص الطلب فارغ.")
    if not input_source.strip():
        raise ValueError("مصدر الطلب غير محدد.")

    references = load_references(reference_dir)
    analysis = llm_client.analyze(normalized_request, references.services)
    validate_analysis_service_ids(analysis, list(references.services))
    summary = _build_summary(analysis, references, normalized_request)
    rendered = render_internal_summary(summary, references.raw_template_text)
    timestamp = now()
    request = ProcessedRequest(
        request_id=new_request_id(),
        created_at=timestamp,
        updated_at=timestamp,
        input_source=input_source,
        raw_request=normalized_request,
        analysis=analysis,
        summary=summary,
    )
    append_request(request, results_path)
    return ProcessingOutcome(
        request=request,
        rendered_summary=rendered,
        references=references,
    )

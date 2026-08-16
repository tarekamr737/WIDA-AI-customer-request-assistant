from datetime import UTC, datetime
from pathlib import Path

from src.models import AIAnalysis
from src.processor import process_request
from src.reference_loader import DEFAULT_REFERENCE_DIR
from src.review import approve_request, request_clarification
from tests.test_processor import FakeLLM, _analysis


def test_approval_updates_same_row_and_recomputes_policy(tmp_path: Path) -> None:
    results_path = tmp_path / "results.csv"
    outcome = process_request(
        "نحتاج إلى لوحة بيانات خلال 5 أيام عمل.",
        "نص ملصق",
        FakeLLM(_analysis()),
        reference_dir=DEFAULT_REFERENCE_DIR,
        results_path=results_path,
        now=lambda: datetime(2026, 8, 16, 9, 0, tzinfo=UTC),
        new_request_id=lambda: "request-1",
    )
    edited = outcome.request.analysis.model_copy(
        update={
            "organization_name": "شركة مصححة",
            "requested_deadline_text": "خلال يومي عمل",
            "requested_working_days": 2,
        }
    )

    approved = approve_request(
        outcome,
        edited,
        results_path=results_path,
        now=lambda: datetime(2026, 8, 16, 10, 0, tzinfo=UTC),
    )

    csv_text = results_path.read_text(encoding="utf-8-sig")
    assert approved.request.summary.review_status == "تمت المراجعة"
    assert approved.request.summary.policy_status == "مخالف"
    assert approved.request.analysis.organization_name == "شركة مصححة"
    assert csv_text.count("request-1") == 1
    assert "تمت المراجعة" in csv_text
    assert "شركة مصححة" in csv_text
    assert approved.request.raw_request == outcome.request.raw_request


def test_approval_rejects_service_outside_current_catalog(tmp_path: Path) -> None:
    results_path = tmp_path / "results.csv"
    outcome = process_request(
        "نحتاج إلى لوحة بيانات.",
        "نص ملصق",
        FakeLLM(_analysis()),
        reference_dir=DEFAULT_REFERENCE_DIR,
        results_path=results_path,
    )
    invalid = AIAnalysis(
        need_summary="خدمة غير موثقة",
        primary_service_id=99,
        classification_state="matched",
        classification_reason="اختيار يدوي غير صالح.",
    )

    try:
        approve_request(outcome, invalid, results_path=results_path)
    except ValueError as exc:
        assert "99" in str(exc)
    else:
        raise AssertionError("Expected invalid reviewer service selection to fail")

    assert "بانتظار المراجعة" in results_path.read_text(encoding="utf-8-sig")


def test_clarification_saves_edits_and_keeps_request_pending(tmp_path: Path) -> None:
    results_path = tmp_path / "results.csv"
    outcome = process_request(
        "نحتاج إلى لوحة بيانات.",
        "نص ملصق",
        FakeLLM(_analysis()),
        reference_dir=DEFAULT_REFERENCE_DIR,
        results_path=results_path,
        new_request_id=lambda: "request-clarify",
    )
    edited = AIAnalysis.model_validate(
        {
            **outcome.request.analysis.model_dump(),
            "contact_role": None,
        }
    )

    clarified = request_clarification(
        outcome,
        edited,
        results_path=results_path,
        now=lambda: datetime(2026, 8, 16, 11, 0, tzinfo=UTC),
    )

    csv_text = results_path.read_text(encoding="utf-8-sig")
    assert clarified.request.summary.review_status == "بانتظار المراجعة"
    assert "طلب البيانات أو تفاصيل النطاق" in clarified.request.summary.next_step
    assert any("حدد المراجع" in alert for alert in clarified.request.summary.alerts)
    assert clarified.request.analysis.contact_role is None
    assert csv_text.count("request-clarify") == 1
    assert "بانتظار المراجعة" in csv_text

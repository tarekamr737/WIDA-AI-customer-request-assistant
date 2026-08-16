from datetime import UTC, datetime
from pathlib import Path
import csv

import pytest

from src.models import AIAnalysis, InternalSummary, ProcessedRequest
from src.storage import StorageError, append_request, update_request


def _request(*, reviewed: bool = False) -> ProcessedRequest:
    created_at = datetime(2026, 8, 16, 9, 0, tzinfo=UTC)
    analysis = AIAnalysis(
        organization_name="شركة الاختبار",
        contact_name="سارة",
        contact_role="مديرة العمليات",
        contact_method="sara@example.com",
        need_summary="إنشاء لوحة بيانات",
        primary_service_id=5,
        classification_state="matched",
        classification_reason="المخرج لوحة بيانات.",
    )
    summary = InternalSummary(
        organization_name="شركة الاختبار",
        contact_person_and_role="سارة - مديرة العمليات",
        contact_method="sara@example.com",
        need_summary="إنشاء لوحة بيانات",
        primary_service="5. تحليل البيانات ولوحات ذكاء الأعمال",
        secondary_service="لا توجد",
        commercial_register="غير واضح",
        requested_deadline="غير محدد",
        policy_status="مخالف",
        missing_data=["السجل التجاري"],
        alerts=["لا يمكن بدء التنفيذ الرسمي."],
        next_step="استكمال السجل التجاري.",
        review_status="تمت المراجعة" if reviewed else "بانتظار المراجعة",
    )
    return ProcessedRequest(
        request_id="request-1",
        created_at=created_at,
        updated_at=created_at,
        input_source="نص ملصق",
        raw_request="طلب عربي",
        analysis=analysis,
        summary=summary,
    )


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_append_writes_utf8_sig_and_auditable_fields(tmp_path: Path) -> None:
    path = tmp_path / "results.csv"

    append_request(_request(), path)

    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    rows = _rows(path)
    assert len(rows) == 1
    assert rows[0]["raw_request"] == "طلب عربي"
    assert rows[0]["review_status"] == "بانتظار المراجعة"
    assert "السجل التجاري" in rows[0]["missing_data"]


def test_update_replaces_the_same_row_without_duplication(tmp_path: Path) -> None:
    path = tmp_path / "results.csv"
    append_request(_request(), path)

    updated = _request(reviewed=True).model_copy(
        update={"updated_at": datetime(2026, 8, 16, 10, 0, tzinfo=UTC)}
    )
    update_request(updated, path)

    rows = _rows(path)
    assert len(rows) == 1
    assert rows[0]["review_status"] == "تمت المراجعة"
    assert rows[0]["updated_at"] == "2026-08-16T10:00:00+00:00"


def test_update_rejects_an_unknown_request_id(tmp_path: Path) -> None:
    with pytest.raises(StorageError, match="Expected one stored row"):
        update_request(_request(), tmp_path / "missing.csv")

from datetime import UTC, datetime
from pathlib import Path
import csv
import json

import pytest

from src.models import AIAnalysis, InternalSummary, ProcessedRequest
from src.storage import (
    COLUMN_HEADERS,
    LEGACY_FIELDNAMES,
    StorageError,
    append_request,
    migrate_results_file,
    update_request,
)


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
    assert rows[0]["نص الطلب الأصلي"] == "طلب عربي"
    assert rows[0]["حالة المراجعة"] == "بانتظار المراجعة"
    assert rows[0]["البيانات الناقصة"] == "السجل التجاري"
    assert "[" not in rows[0]["التنبيهات المهمة"]


def test_update_replaces_the_same_row_without_duplication(tmp_path: Path) -> None:
    path = tmp_path / "results.csv"
    append_request(_request(), path)

    updated = _request(reviewed=True).model_copy(
        update={"updated_at": datetime(2026, 8, 16, 10, 0, tzinfo=UTC)}
    )
    update_request(updated, path)

    rows = _rows(path)
    assert len(rows) == 1
    assert rows[0]["حالة المراجعة"] == "تمت المراجعة"
    assert rows[0]["آخر تحديث (UTC)"] == "2026-08-16T10:00:00+00:00"


def test_update_rejects_an_unknown_request_id(tmp_path: Path) -> None:
    with pytest.raises(StorageError, match="Expected one stored row"):
        update_request(_request(), tmp_path / "missing.csv")


def test_legacy_csv_is_migrated_to_readable_arabic_headers(tmp_path: Path) -> None:
    path = tmp_path / "legacy.csv"
    legacy_row = {
        field: "" for field in LEGACY_FIELDNAMES
    }
    legacy_row.update(
        {
            "request_id": "legacy-1",
            "organization_name": "شركة قديمة",
            "missing_data": json.dumps(["السجل التجاري"], ensure_ascii=False),
            "alerts": json.dumps(["تنبيه أول", "تنبيه ثان"], ensure_ascii=False),
            "review_status": "بانتظار المراجعة",
        }
    )
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEGACY_FIELDNAMES)
        writer.writeheader()
        writer.writerow(legacy_row)

    migrate_results_file(path)

    rows = _rows(path)
    assert list(rows[0]) == list(COLUMN_HEADERS.values())
    assert rows[0]["رقم الطلب"] == "legacy-1"
    assert rows[0]["البيانات الناقصة"] == "السجل التجاري"
    assert rows[0]["التنبيهات المهمة"] == "تنبيه أول • تنبيه ثان"

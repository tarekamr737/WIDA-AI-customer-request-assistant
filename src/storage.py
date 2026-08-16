"""Readable UTF-8-SIG CSV persistence for processed customer requests."""

from collections.abc import Iterable
from pathlib import Path
import csv
import json
import tempfile

from src.models import ProcessedRequest


DEFAULT_RESULTS_PATH = Path(__file__).resolve().parents[1] / "data" / "results.csv"

LEGACY_FIELDNAMES = (
    "request_id",
    "created_at",
    "updated_at",
    "input_source",
    "raw_request",
    "organization_name",
    "contact_name",
    "contact_role",
    "contact_method",
    "need_summary",
    "requested_deadline_text",
    "requested_working_days",
    "commercial_register_text",
    "primary_service_id",
    "secondary_service_id",
    "classification_state",
    "classification_reason",
    "contact_person_and_role",
    "primary_service",
    "secondary_service",
    "commercial_register",
    "requested_deadline",
    "policy_status",
    "missing_data",
    "alerts",
    "next_step",
    "review_status",
)

FIELDNAMES = (
    "request_id",
    "review_status",
    "created_at",
    "updated_at",
    "organization_name",
    "contact_person_and_role",
    "contact_method",
    "need_summary",
    "primary_service",
    "secondary_service",
    "commercial_register",
    "requested_deadline",
    "policy_status",
    "missing_data",
    "alerts",
    "next_step",
    "classification_reason",
    "input_source",
    "raw_request",
    "contact_name",
    "contact_role",
    "requested_deadline_text",
    "requested_working_days",
    "commercial_register_text",
    "primary_service_id",
    "secondary_service_id",
    "classification_state",
)

COLUMN_HEADERS = {
    "request_id": "رقم الطلب",
    "review_status": "حالة المراجعة",
    "created_at": "تاريخ الإنشاء (UTC)",
    "updated_at": "آخر تحديث (UTC)",
    "organization_name": "اسم الجهة",
    "contact_person_and_role": "شخص التواصل وصفته",
    "contact_method": "وسيلة التواصل",
    "need_summary": "ملخص الاحتياج",
    "primary_service": "الخدمة الأساسية المقترحة",
    "secondary_service": "الخدمة الثانوية",
    "commercial_register": "حالة السجل التجاري",
    "requested_deadline": "الموعد المطلوب",
    "policy_status": "تقييم السياسات",
    "missing_data": "البيانات الناقصة",
    "alerts": "التنبيهات المهمة",
    "next_step": "الخطوة التالية المقترحة",
    "classification_reason": "سبب التصنيف",
    "input_source": "مصدر الإدخال",
    "raw_request": "نص الطلب الأصلي",
    "contact_name": "اسم شخص التواصل",
    "contact_role": "صفة شخص التواصل",
    "requested_deadline_text": "نص الموعد الأصلي",
    "requested_working_days": "عدد أيام العمل المطلوبة",
    "commercial_register_text": "تفاصيل السجل التجاري",
    "primary_service_id": "معرف الخدمة الأساسية",
    "secondary_service_id": "معرف الخدمة الثانوية",
    "classification_state": "حالة التصنيف التقنية",
}

CSV_HEADERS = tuple(COLUMN_HEADERS[field] for field in FIELDNAMES)


class StorageError(RuntimeError):
    """Raised when stored audit data cannot be safely read or updated."""


def _optional(value: object | None) -> object:
    return "" if value is None else value


def _readable_list(values: list[str]) -> str:
    return " • ".join(values) if values else "لا توجد"


def _read_legacy_list(value: str) -> str:
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value
    if not isinstance(parsed, list):
        return value
    return _readable_list([str(item) for item in parsed])


def _to_row(request: ProcessedRequest) -> dict[str, object]:
    analysis = request.analysis
    summary = request.summary
    return {
        "request_id": request.request_id,
        "created_at": request.created_at.isoformat(),
        "updated_at": request.updated_at.isoformat(),
        "input_source": request.input_source,
        "raw_request": request.raw_request,
        "organization_name": _optional(analysis.organization_name),
        "contact_name": _optional(analysis.contact_name),
        "contact_role": _optional(analysis.contact_role),
        "contact_method": _optional(analysis.contact_method),
        "need_summary": analysis.need_summary,
        "requested_deadline_text": _optional(analysis.requested_deadline_text),
        "requested_working_days": _optional(analysis.requested_working_days),
        "commercial_register_text": _optional(analysis.commercial_register_text),
        "primary_service_id": _optional(analysis.primary_service_id),
        "secondary_service_id": _optional(analysis.secondary_service_id),
        "classification_state": analysis.classification_state,
        "classification_reason": analysis.classification_reason,
        "contact_person_and_role": summary.contact_person_and_role,
        "primary_service": summary.primary_service,
        "secondary_service": summary.secondary_service,
        "commercial_register": summary.commercial_register,
        "requested_deadline": summary.requested_deadline,
        "policy_status": summary.policy_status,
        "missing_data": _readable_list(summary.missing_data),
        "alerts": _readable_list(summary.alerts),
        "next_step": summary.next_step,
        "review_status": summary.review_status,
    }


def _normalize_row(row: dict[str, str], *, legacy: bool) -> dict[str, str]:
    normalized = {field: row.get(field, "") for field in FIELDNAMES}
    if legacy:
        normalized["missing_data"] = _read_legacy_list(row.get("missing_data", ""))
        normalized["alerts"] = _read_legacy_list(row.get("alerts", ""))
    return normalized


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames == list(LEGACY_FIELDNAMES):
                return [_normalize_row(row, legacy=True) for row in reader]
            if reader.fieldnames == list(CSV_HEADERS):
                return [
                    _normalize_row(
                        {
                            field: row.get(COLUMN_HEADERS[field], "")
                            for field in FIELDNAMES
                        },
                        legacy=False,
                    )
                    for row in reader
                ]
            if reader.fieldnames is None:
                return []
            else:
                raise StorageError("Stored CSV columns do not match the expected schema.")
    except StorageError:
        raise
    except OSError as exc:
        raise StorageError("تعذر قراءة ملف النتائج المحلي.") from exc


def append_request(
    request: ProcessedRequest, path: Path = DEFAULT_RESULTS_PATH
) -> None:
    rows = _read_rows(path)
    if any(row["request_id"] == request.request_id for row in rows):
        raise StorageError(f"Request ID already exists: {request.request_id}")

    _write_rows(path, [*rows, _to_row(request)])


def _write_rows(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS)
            writer.writeheader()
            writer.writerows(
                {
                    COLUMN_HEADERS[field]: row.get(field, "")
                    for field in FIELDNAMES
                }
                for row in rows
            )
        temporary_path.replace(path)
    except PermissionError as exc:
        raise StorageError(
            f"تعذر تحديث {path.name}. أغلق الملف إذا كان مفتوحًا في Excel "
            "أو برنامج آخر، ثم أعد المحاولة."
        ) from exc
    except OSError as exc:
        raise StorageError("تعذر تحديث نتيجة الطلب محليًا.") from exc
    finally:
        if temporary_path is not None and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError:
                pass


def update_request(
    request: ProcessedRequest, path: Path = DEFAULT_RESULTS_PATH
) -> None:
    rows = _read_rows(path)
    replacement = _to_row(request)
    matches = 0
    updated_rows: list[dict[str, object]] = []
    for row in rows:
        if row["request_id"] == request.request_id:
            updated_rows.append(replacement)
            matches += 1
        else:
            updated_rows.append(row)

    if matches != 1:
        raise StorageError(f"Expected one stored row for request ID: {request.request_id}")
    _write_rows(path, updated_rows)


def migrate_results_file(path: Path = DEFAULT_RESULTS_PATH) -> None:
    """Rewrite an existing legacy/new CSV with the current readable schema."""

    if not path.exists():
        return
    _write_rows(path, _read_rows(path))

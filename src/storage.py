"""UTF-8-SIG CSV persistence for processed customer requests."""

from collections.abc import Iterable
from pathlib import Path
import csv
import json

from src.models import ProcessedRequest


DEFAULT_RESULTS_PATH = Path(__file__).resolve().parents[1] / "data" / "results.csv"

FIELDNAMES = (
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


class StorageError(RuntimeError):
    """Raised when stored audit data cannot be safely read or updated."""


def _optional(value: object | None) -> object:
    return "" if value is None else value


def _json_list(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


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
        "missing_data": _json_list(summary.missing_data),
        "alerts": _json_list(summary.alerts),
        "next_step": summary.next_step,
        "review_status": summary.review_status,
    }


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != list(FIELDNAMES):
                raise StorageError("Stored CSV columns do not match the expected schema.")
            return list(reader)
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

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            if not rows:
                writer.writeheader()
            writer.writerow(_to_row(request))
    except OSError as exc:
        raise StorageError("تعذر حفظ نتيجة الطلب محليًا.") from exc


def _write_rows(path: Path, rows: Iterable[dict[str, object]]) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        temporary_path.replace(path)
    except OSError as exc:
        raise StorageError("تعذر تحديث نتيجة الطلب محليًا.") from exc


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

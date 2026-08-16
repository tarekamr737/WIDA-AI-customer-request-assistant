"""Load authoritative Horizon references from disk on every processing run."""

from dataclasses import dataclass
from pathlib import Path
import re

from pydantic import ValidationError

from src.models import ServiceDefinition


DEFAULT_REFERENCE_DIR = Path(__file__).resolve().parents[1] / "references"


class ReferenceLoadError(RuntimeError):
    """Raised when a required reference cannot be safely loaded."""


@dataclass(frozen=True)
class RawReferences:
    service_catalog: str
    operating_policies: str
    output_template: str


_SERVICE_HEADER = re.compile(r"(?m)^(?P<id>\d+)\.\s+(?P<name>[^\r\n]+?)\s*$")
_DURATION_RANGE = re.compile(r"(?P<min>\d+)\s+إلى\s+(?P<max>\d+)\s+(?:يوم|أيام)")


def _service_field(block: str, label: str, service_id: int) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(label)}:\s*(.+?)\s*$", block)
    if match is None:
        raise ReferenceLoadError(
            f"Service {service_id} is missing the required '{label}' field"
        )
    return match.group(1).strip()


def parse_service_catalog(text: str) -> tuple[ServiceDefinition, ...]:
    """Parse the current Arabic service catalog into validated definitions."""

    headers = list(_SERVICE_HEADER.finditer(text))
    if not headers:
        raise ReferenceLoadError("Service catalog contains no recognizable services")

    services: list[ServiceDefinition] = []
    for index, header in enumerate(headers):
        service_id = int(header.group("id"))
        block_end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        block = text[header.end() : block_end]
        duration_text = _service_field(block, "زمن التنفيذ القياسي", service_id)
        duration_match = _DURATION_RANGE.search(duration_text)

        try:
            services.append(
                ServiceDefinition(
                    id=service_id,
                    name=header.group("name"),
                    description=_service_field(block, "الوصف", service_id),
                    use_when=_service_field(block, "تستخدم عندما", service_id),
                    exclusions=_service_field(block, "لا تشمل", service_id),
                    min_days=(int(duration_match.group("min")) if duration_match else None),
                    max_days=(int(duration_match.group("max")) if duration_match else None),
                )
            )
        except ValidationError as exc:
            raise ReferenceLoadError(f"Service {service_id} is invalid: {exc}") from exc

    parsed_ids = {service.id for service in services}
    expected_ids = set(range(1, 9))
    if parsed_ids != expected_ids or len(services) != len(expected_ids):
        raise ReferenceLoadError("Service catalog must contain each service ID from 1 to 8 once")
    return tuple(services)


def _read_required_text(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReferenceLoadError(f"Required reference file is missing: {path.name}") from exc
    except (OSError, UnicodeError) as exc:
        raise ReferenceLoadError(f"Required reference file is unreadable: {path.name}") from exc

    if not content.strip():
        raise ReferenceLoadError(f"Required reference file is empty: {path.name}")
    return content


def load_reference_texts(reference_dir: Path = DEFAULT_REFERENCE_DIR) -> RawReferences:
    """Read current source text without caching so edits apply on the next run."""

    return RawReferences(
        service_catalog=_read_required_text(reference_dir / "02_Service_Catalog.txt"),
        operating_policies=_read_required_text(reference_dir / "03_Operating_Policies.txt"),
        output_template=_read_required_text(reference_dir / "04_Output_Template.txt"),
    )

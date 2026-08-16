"""Load authoritative Horizon references from disk on every processing run."""

from dataclasses import dataclass
from pathlib import Path


DEFAULT_REFERENCE_DIR = Path(__file__).resolve().parents[1] / "references"


class ReferenceLoadError(RuntimeError):
    """Raised when a required reference cannot be safely loaded."""


@dataclass(frozen=True)
class RawReferences:
    service_catalog: str
    operating_policies: str
    output_template: str


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

from pathlib import Path

import pytest

from src.reference_loader import ReferenceLoadError, load_reference_texts


def _write_references(directory: Path, *, catalog: str = "catalog") -> None:
    (directory / "02_Service_Catalog.txt").write_text(catalog, encoding="utf-8")
    (directory / "03_Operating_Policies.txt").write_text("policies", encoding="utf-8")
    (directory / "04_Output_Template.txt").write_text("template", encoding="utf-8")


def test_reference_texts_are_reloaded_after_an_edit(tmp_path: Path) -> None:
    _write_references(tmp_path, catalog="first")
    assert load_reference_texts(tmp_path).service_catalog == "first"

    (tmp_path / "02_Service_Catalog.txt").write_text("second", encoding="utf-8")

    assert load_reference_texts(tmp_path).service_catalog == "second"


def test_missing_reference_has_an_actionable_error(tmp_path: Path) -> None:
    with pytest.raises(ReferenceLoadError, match="02_Service_Catalog.txt"):
        load_reference_texts(tmp_path)


def test_empty_reference_is_rejected(tmp_path: Path) -> None:
    _write_references(tmp_path, catalog="  \n")

    with pytest.raises(ReferenceLoadError, match="empty"):
        load_reference_texts(tmp_path)

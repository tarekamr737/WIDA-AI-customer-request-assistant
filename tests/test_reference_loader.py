from pathlib import Path

import pytest

from src.reference_loader import (
    DEFAULT_REFERENCE_DIR,
    ReferenceLoadError,
    load_reference_texts,
    parse_service_catalog,
)


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


def test_catalog_parser_extracts_all_service_fields_and_durations() -> None:
    catalog = load_reference_texts(DEFAULT_REFERENCE_DIR).service_catalog

    services = parse_service_catalog(catalog)

    assert [service.id for service in services] == list(range(1, 9))
    assert services[0].name == "الاستشارات الإدارية والتحول التشغيلي"
    assert services[0].min_days == 10
    assert services[0].max_days == 15
    assert "تحسين عملية" in services[0].use_when
    assert "الاستشارات القانونية" in services[0].exclusions
    assert services[7].min_days is None
    assert services[7].max_days is None


def test_catalog_parser_rejects_an_incomplete_catalog() -> None:
    with pytest.raises(ReferenceLoadError, match="1 to 8"):
        parse_service_catalog(
            """1. خدمة واحدة
   الوصف: وصف
   تستخدم عندما: حالة
   لا تشمل: استثناء
   زمن التنفيذ القياسي: 3 إلى 5 أيام عمل.
"""
        )

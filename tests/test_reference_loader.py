from pathlib import Path
import shutil

import pytest

from src.reference_loader import (
    DEFAULT_REFERENCE_DIR,
    ReferenceLoadError,
    load_references,
    load_reference_texts,
    parse_global_min_execution_days,
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


def test_policy_parser_extracts_current_global_minimum() -> None:
    references = load_references(DEFAULT_REFERENCE_DIR)

    assert references.global_min_execution_days == 3
    assert len(references.services) == 8


def test_policy_parser_uses_current_text() -> None:
    policy = "الحد الأدنى لأي تنفيذ هو 6 أيام عمل من تاريخ الاعتماد."

    assert parse_global_min_execution_days(policy) == 6


def test_policy_parser_rejects_missing_minimum() -> None:
    with pytest.raises(ReferenceLoadError, match="minimum execution duration"):
        parse_global_min_execution_days("لا توجد مدة معرفة هنا.")


def test_catalog_and_policy_edits_apply_on_the_next_load(tmp_path: Path) -> None:
    reference_dir = tmp_path / "references"
    shutil.copytree(DEFAULT_REFERENCE_DIR, reference_dir)
    before = load_references(reference_dir)

    catalog_path = reference_dir / "02_Service_Catalog.txt"
    catalog_path.write_text(
        catalog_path.read_text(encoding="utf-8").replace(
            "تحليل البيانات ولوحات ذكاء الأعمال",
            "تحليل البيانات والتقارير التنفيذية",
        ),
        encoding="utf-8",
    )
    policy_path = reference_dir / "03_Operating_Policies.txt"
    policy_path.write_text(
        policy_path.read_text(encoding="utf-8").replace(
            "الحد الأدنى لأي تنفيذ هو 3 أيام عمل",
            "الحد الأدنى لأي تنفيذ هو 4 أيام عمل",
        ),
        encoding="utf-8",
    )

    after = load_references(reference_dir)

    assert before.services[4].name == "تحليل البيانات ولوحات ذكاء الأعمال"
    assert after.services[4].name == "تحليل البيانات والتقارير التنفيذية"
    assert before.global_min_execution_days == 3
    assert after.global_min_execution_days == 4

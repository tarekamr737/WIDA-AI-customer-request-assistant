import pytest
from pydantic import ValidationError

from src.models import AIAnalysis, ServiceDefinition, validate_analysis_service_ids


def test_service_duration_must_be_a_complete_ordered_range() -> None:
    with pytest.raises(ValidationError):
        ServiceDefinition(
            id=1,
            name="خدمة",
            description="وصف",
            use_when="حالة استخدام",
            exclusions="استثناء",
            min_days=5,
            max_days=3,
        )


def test_matched_analysis_requires_a_primary_service() -> None:
    with pytest.raises(ValidationError):
        AIAnalysis(
            need_summary="احتياج واضح",
            classification_state="matched",
            classification_reason="الطلب يطابق الخدمة.",
        )


def test_unclear_analysis_rejects_service_selection() -> None:
    with pytest.raises(ValidationError):
        AIAnalysis(
            need_summary="احتياج غير واضح",
            primary_service_id=1,
            classification_state="unclear",
            classification_reason="المعلومات غير كافية.",
        )


def test_optional_unknown_markers_normalize_to_none() -> None:
    analysis = AIAnalysis(
        organization_name="غير مذكور",
        contact_method="  ",
        requested_deadline_text="unknown",
        need_summary="طلب غير مكتمل",
        classification_state="unclear",
        classification_reason="لا توجد معلومات كافية.",
    )

    assert analysis.organization_name is None
    assert analysis.contact_method is None
    assert analysis.requested_deadline_text is None


def test_service_ids_must_exist_in_the_current_catalog() -> None:
    analysis = AIAnalysis(
        need_summary="احتياج واضح",
        primary_service_id=8,
        classification_state="matched",
        classification_reason="تطابق واضح.",
    )
    catalog = [
        ServiceDefinition(
            id=1,
            name="خدمة",
            description="وصف",
            use_when="حالة استخدام",
            exclusions="استثناء",
            min_days=3,
            max_days=5,
        )
    ]

    with pytest.raises(ValueError, match="8"):
        validate_analysis_service_ids(analysis, catalog)

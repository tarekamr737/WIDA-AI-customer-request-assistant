import pytest
from pydantic import ValidationError

from src.models import AIAnalysis, ServiceDefinition


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

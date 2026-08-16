from src.models import AIAnalysis
from src.policy_engine import commercial_register_status, find_missing_data


def _analysis(**overrides: object) -> AIAnalysis:
    values: dict[str, object] = {
        "organization_name": "شركة الاختبار",
        "contact_name": "سارة",
        "contact_role": "مديرة العمليات",
        "contact_method": "sara@example.com",
        "need_summary": "إنشاء لوحة بيانات",
        "commercial_register_text": "سجل تجاري ساري رقم 123",
        "primary_service_id": 5,
        "classification_state": "matched",
        "classification_reason": "المخرج لوحة بيانات.",
    }
    values.update(overrides)
    return AIAnalysis.model_validate(values)


def test_complete_request_does_not_require_a_deadline() -> None:
    assert find_missing_data(_analysis(requested_deadline_text=None)) == []


def test_missing_basic_fields_are_reported_in_stable_order() -> None:
    missing = find_missing_data(
        _analysis(
            organization_name=None,
            contact_name=None,
            contact_role=None,
            contact_method=None,
            commercial_register_text=None,
        )
    )

    assert missing == [
        "اسم الجهة",
        "اسم شخص التواصل",
        "صفة شخص التواصل",
        "وسيلة التواصل",
        "السجل التجاري",
    ]


def test_unclear_need_is_reported_without_inventing_scope() -> None:
    missing = find_missing_data(
        _analysis(
            primary_service_id=None,
            classification_state="unclear",
            classification_reason="التفاصيل غير كافية.",
        )
    )

    assert "وصف احتياج كافٍ للتصنيف" in missing


def test_explicitly_absent_register_is_missing_for_execution() -> None:
    analysis = _analysis(commercial_register_text="لا يوجد سجل تجاري حاليًا")

    assert commercial_register_status(analysis.commercial_register_text) == "غير متوفر"
    assert "السجل التجاري" in find_missing_data(analysis)

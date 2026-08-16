from src.models import AIAnalysis, ServiceDefinition
from src.policy_engine import (
    commercial_register_status,
    evaluate_policies,
    find_missing_data,
)


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


def _service(
    service_id: int = 5, name: str = "تحليل البيانات", min_days: int = 4
) -> ServiceDefinition:
    return ServiceDefinition(
        id=service_id,
        name=name,
        description="وصف",
        use_when="حالة استخدام",
        exclusions="استثناء",
        min_days=min_days,
        max_days=min_days + 4,
    )


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


def test_missing_commercial_register_blocks_execution() -> None:
    result = evaluate_policies(
        _analysis(commercial_register_text=None), [_service()], 3
    )

    assert result.status == "مخالف"
    assert "السجل التجاري" in result.next_step


def test_duration_below_global_minimum_takes_precedence() -> None:
    result = evaluate_policies(
        _analysis(requested_working_days=2, commercial_register_text=None),
        [_service()],
        3,
    )

    assert result.status == "مخالف"
    assert any("الحد الأدنى" in alert for alert in result.alerts)


def test_duration_between_global_and_service_minimum_is_urgent() -> None:
    result = evaluate_policies(
        _analysis(requested_working_days=3), [_service(min_days=4)], 3
    )

    assert result.status == "عاجل ويتطلب موافقة"
    assert "مدير العمليات" in result.next_step


def test_normal_duration_is_compliant() -> None:
    result = evaluate_policies(
        _analysis(requested_working_days=5), [_service(min_days=4)], 3
    )

    assert result.status == "متوافق"


def test_out_of_scope_is_not_force_classified() -> None:
    result = evaluate_policies(
        _analysis(
            primary_service_id=None,
            classification_state="out_of_scope",
            classification_reason="الطلب تسويقي.",
        ),
        [_service()],
        3,
    )

    assert result.status == "خارج النطاق"
    assert "المبيعات" in result.next_step


def test_secondary_and_commercial_requests_add_independent_alerts() -> None:
    services = [_service(), _service(7, "التكامل بين الأنظمة", 5)]
    result = evaluate_policies(
        _analysis(secondary_service_id=7),
        services,
        3,
        raw_request="نريد خصمًا خاصًا على السعر",
    )

    assert result.status == "متوافق"
    assert any("خدمة ثانوية" in alert for alert in result.alerts)
    assert any("خصم" in alert for alert in result.alerts)

from src.models import InternalSummary
from src.reference_loader import DEFAULT_REFERENCE_DIR, load_reference_texts
from src.renderer import RenderError, render_internal_summary


def _summary() -> InternalSummary:
    return InternalSummary(
        organization_name="شركة الاختبار",
        contact_person_and_role="سارة - مديرة العمليات",
        contact_method="sara@example.com",
        need_summary="إنشاء لوحة مؤشرات",
        primary_service="5. تحليل البيانات ولوحات ذكاء الأعمال",
        secondary_service="لا توجد",
        commercial_register="متوفر",
        requested_deadline="5 أيام عمل",
        policy_status="متوافق",
        missing_data=[],
        alerts=["تلزم المراجعة البشرية."],
        next_step="مراجعة الملخص.",
    )


def test_renderer_preserves_template_order_and_populates_every_field() -> None:
    template = load_reference_texts(DEFAULT_REFERENCE_DIR).output_template

    rendered = render_internal_summary(_summary(), template)

    labels = [
        "اسم الجهة",
        "شخص التواصل وصفته",
        "وسيلة التواصل",
        "ملخص الاحتياج",
        "الخدمة الأساسية المقترحة",
        "الخدمة الثانوية إن وجدت",
        "السجل التجاري",
        "الموعد المطلوب",
        "تقييم السياسات",
        "البيانات الناقصة",
        "التنبيهات المهمة",
        "الخطوة التالية المقترحة",
        "حالة المراجعة البشرية",
    ]
    positions = [rendered.index(f"- {label}:") for label in labels]
    assert positions == sorted(positions)
    assert "- اسم الجهة: شركة الاختبار" in rendered
    assert "- البيانات الناقصة: لا توجد" in rendered
    assert "- حالة المراجعة البشرية: بانتظار المراجعة" in rendered
    assert "{" not in rendered


def test_renderer_rejects_an_incomplete_template() -> None:
    try:
        render_internal_summary(_summary(), "- اسم الجهة: {قيمة}")
    except RenderError as exc:
        assert "شخص التواصل وصفته" in str(exc)
    else:
        raise AssertionError("Expected an incomplete template to be rejected")

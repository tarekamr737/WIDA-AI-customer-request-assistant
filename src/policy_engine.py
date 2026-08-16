"""Deterministic policy and missing-data rules."""

from collections.abc import Sequence

from src.models import AIAnalysis, CommercialRegisterStatus, PolicyResult, ServiceDefinition


_REGISTER_ABSENCE_MARKERS = (
    "غير متوفر",
    "غير متاح",
    "غير مرفق",
    "لا يوجد",
    "لا نملك",
    "بدون سجل",
)
_COMMERCIAL_REQUEST_MARKERS = (
    "مجاني",
    "مجاناً",
    "مجانا",
    "خصم",
    "سعر",
    "تكلفة",
    "free",
    "discount",
)


def commercial_register_status(text: str | None) -> CommercialRegisterStatus:
    if text is None:
        return "غير واضح"
    normalized = text.strip().lower()
    if any(marker in normalized for marker in _REGISTER_ABSENCE_MARKERS):
        return "غير متوفر"
    return "متوفر"


def find_missing_data(analysis: AIAnalysis) -> list[str]:
    """Return missing execution/review fields in stable template-friendly order."""

    fields = (
        ("اسم الجهة", analysis.organization_name),
        ("اسم شخص التواصل", analysis.contact_name),
        ("صفة شخص التواصل", analysis.contact_role),
        ("وسيلة التواصل", analysis.contact_method),
    )
    missing = [label for label, value in fields if value is None]

    if analysis.classification_state == "unclear":
        missing.append("وصف احتياج كافٍ للتصنيف")
    if commercial_register_status(analysis.commercial_register_text) != "متوفر":
        missing.append("السجل التجاري")
    return missing


def evaluate_policies(
    analysis: AIAnalysis,
    services: Sequence[ServiceDefinition],
    global_min_execution_days: int,
    *,
    raw_request: str = "",
    missing_data: list[str] | None = None,
) -> PolicyResult:
    """Apply documented policy precedence and collect independent alerts."""

    if global_min_execution_days < 1:
        raise ValueError("global minimum execution days must be positive")

    service_by_id = {service.id: service for service in services}
    primary = service_by_id.get(analysis.primary_service_id)
    secondary = service_by_id.get(analysis.secondary_service_id)
    missing = list(missing_data if missing_data is not None else find_missing_data(analysis))
    alerts: list[str] = []

    basic_missing = [field for field in missing if field != "السجل التجاري"]
    if basic_missing:
        alerts.append(f"بيانات أساسية ناقصة: {', '.join(basic_missing)}.")
    if secondary is not None:
        alerts.append(f"يتضمن الطلب خدمة ثانوية: {secondary.id}. {secondary.name}.")
    if any(marker in raw_request.lower() for marker in _COMMERCIAL_REQUEST_MARKERS):
        alerts.append(
            "يتضمن الطلب سعرًا أو خصمًا أو عملًا مجانيًا؛ يلزم اعتماد المبيعات دون اختراع التزام."
        )

    register = commercial_register_status(analysis.commercial_register_text)
    requested_days = analysis.requested_working_days

    if analysis.classification_state in {"out_of_scope", "unclear"}:
        if analysis.classification_state == "unclear":
            alerts.append("نطاق الطلب غير واضح ولا يسمح بتصنيف موثوق.")
            next_step = "طلب استيضاح نطاق الاحتياج من العميل ثم إعادة التحليل."
        else:
            alerts.append("الطلب لا يطابق أي خدمة موثقة في الدليل الحالي.")
            next_step = "إحالة الطلب إلى المبيعات للاستفسار أو المعالجة خارج نطاق الخدمات."
        status = "خارج النطاق"
    elif requested_days is not None and requested_days < global_min_execution_days:
        alerts.append(
            f"المدة المطلوبة ({requested_days} أيام عمل) أقل من الحد الأدنى "
            f"للتنفيذ ({global_min_execution_days} أيام عمل)."
        )
        next_step = "إيقاف التحويل للتنفيذ وطلب موعد يلتزم بالحد الأدنى للسياسة."
        status = "مخالف"
    elif register != "متوفر":
        if register == "غير متوفر":
            alerts.append("السجل التجاري غير متوفر، لذلك لا يمكن بدء التنفيذ الرسمي.")
        else:
            alerts.append("حالة السجل التجاري غير واضحة، لذلك لا يمكن بدء التنفيذ الرسمي.")
        next_step = "استكمال السجل التجاري الساري قبل تحويل الطلب إلى التنفيذ."
        status = "مخالف"
    elif (
        requested_days is not None
        and primary is not None
        and primary.min_days is not None
        and requested_days < primary.min_days
    ):
        alerts.append(
            f"المدة المطلوبة ({requested_days} أيام عمل) أقل من الحد القياسي الأدنى "
            f"للخدمة ({primary.min_days} أيام عمل)."
        )
        next_step = "طلب موافقة مدير العمليات وتسعير الاستعجال قبل أي التزام."
        status = "عاجل ويتطلب موافقة"
    else:
        status = "متوافق"
        if basic_missing:
            next_step = "استكمال البيانات الناقصة ثم إجراء المراجعة البشرية قبل التنفيذ."
        else:
            next_step = "إجراء المراجعة البشرية ثم تحويل الطلب إلى فريق العمليات."

    alerts.append("يلزم اعتماد موظف مخول قبل إرسال أي التزام أو رد نهائي إلى العميل.")
    return PolicyResult(status=status, alerts=alerts, next_step=next_step)

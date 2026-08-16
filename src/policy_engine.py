"""Deterministic policy and missing-data rules."""

from src.models import AIAnalysis, CommercialRegisterStatus


_REGISTER_ABSENCE_MARKERS = (
    "غير متوفر",
    "غير متاح",
    "لا يوجد",
    "لا نملك",
    "بدون سجل",
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

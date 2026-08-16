"""Render validated output through the current supplied Arabic template."""

import re

from src.models import InternalSummary


class RenderError(RuntimeError):
    """Raised when the supplied output template cannot be safely rendered."""


_TEMPLATE_FIELDS = (
    ("اسم الجهة", "organization_name"),
    ("شخص التواصل وصفته", "contact_person_and_role"),
    ("وسيلة التواصل", "contact_method"),
    ("ملخص الاحتياج", "need_summary"),
    ("الخدمة الأساسية المقترحة", "primary_service"),
    ("الخدمة الثانوية إن وجدت", "secondary_service"),
    ("السجل التجاري", "commercial_register"),
    ("الموعد المطلوب", "requested_deadline"),
    ("تقييم السياسات", "policy_status"),
    ("البيانات الناقصة", "missing_data"),
    ("التنبيهات المهمة", "alerts"),
    ("الخطوة التالية المقترحة", "next_step"),
    ("حالة المراجعة البشرية", "review_status"),
)


def _display_value(value: object) -> str:
    if isinstance(value, list):
        return "، ".join(value) if value else "لا توجد"
    return str(value)


def render_internal_summary(summary: InternalSummary, template_text: str) -> str:
    """Replace template values while retaining the supplied structure and order."""

    rendered = template_text
    for label, attribute in _TEMPLATE_FIELDS:
        pattern = re.compile(rf"(?m)^(?P<prefix>-\s*{re.escape(label)}:\s*).*$")
        value = _display_value(getattr(summary, attribute))
        rendered, replacements = pattern.subn(
            lambda match, replacement=value: f"{match.group('prefix')}{replacement}",
            rendered,
            count=1,
        )
        if replacements != 1:
            raise RenderError(f"Output template is missing the required field: {label}")
    return rendered.strip()

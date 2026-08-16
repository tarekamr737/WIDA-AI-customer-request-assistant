from collections.abc import Sequence
from pathlib import Path

import pytest

from src.models import AIAnalysis, ServiceDefinition
from src.processor import process_request
from src.reference_loader import DEFAULT_REFERENCE_DIR


class SemanticSampleFakeLLM:
    """Test double keyed by request meaning, never by sample filename or ID."""

    def analyze(
        self, request_text: str, services: Sequence[ServiceDefinition]
    ) -> AIAnalysis:
        if "لوحة مؤشرات" in request_text:
            return AIAnalysis(
                organization_name="شركة روافد التجزئة الافتراضية",
                contact_name="نورة السالم",
                contact_role="مديرة التخطيط",
                contact_method="nora.salem@example.test | 0500000101",
                need_summary="بناء لوحة لمؤشرات المبيعات والطلبات والمرتجعات من ملفات Excel.",
                requested_deadline_text="خلال 12 يوم عمل",
                requested_working_days=12,
                commercial_register_text="سجل افتراضي رقم 9900001001",
                primary_service_id=5,
                classification_state="matched",
                classification_reason="المخرج المطلوب لوحة مؤشرات تحليلية.",
            )
        if "طلبات الشراء الواردة بالبريد" in request_text:
            return AIAnalysis(
                organization_name="شركة مسارات التموين الافتراضية",
                contact_name="ليان",
                need_summary="أتمتة استخراج بيانات طلبات الشراء وإرسالها إلى ERP عبر API.",
                requested_deadline_text="خلال 8 أيام عمل",
                requested_working_days=8,
                commercial_register_text="غير مرفق",
                primary_service_id=2,
                secondary_service_id=7,
                classification_state="matched",
                classification_reason="أتمتة أساسية مع تكامل مستقل مع ERP.",
            )
        if "إدارة حسابات التواصل الاجتماعي" in request_text:
            return AIAnalysis(
                organization_name="مصنع المدار الافتراضي",
                contact_name="عمر الحربي",
                contact_role="مدير التسويق",
                contact_method="omar.harbi@example.test | 0500000103",
                need_summary="إدارة تواصل اجتماعي ومحتوى ومؤثرين وإعلانات.",
                requested_deadline_text="بدء الحملة خلال 15 يوم عمل",
                requested_working_days=15,
                commercial_register_text="سجل افتراضي رقم 9900001003",
                classification_state="out_of_scope",
                classification_reason="خدمات التسويق والإعلانات غير موجودة في الدليل.",
            )
        if "توحيد خطوات الاعتماد" in request_text:
            return AIAnalysis(
                organization_name="مجموعة البناء الحديث الافتراضية",
                contact_name="د. فهد العمر",
                contact_role="مدير العمليات",
                contact_method="fahad.omar@example.test | 0500000104",
                need_summary="مراجعة وتوحيد اعتماد طلبات المواد وتحديد الأدوار ومؤشرات الأداء.",
                requested_deadline_text="خلال 6 أيام عمل",
                requested_working_days=6,
                commercial_register_text="سجل افتراضي رقم 9900001004",
                primary_service_id=1,
                classification_state="matched",
                classification_reason="الطلب يركز على إجراء تشغيلي دون تطوير نظام.",
            )
        return AIAnalysis(
            need_summary="طلب حل ذكي عام يربط كل شيء ويسرّع العمل.",
            requested_deadline_text="قريبًا",
            classification_state="unclear",
            classification_reason="النطاق والأنظمة والمخرجات غير محددة.",
        )


@pytest.mark.parametrize(
    ("filename", "expected_primary", "expected_secondary", "expected_policy"),
    [
        ("05_Request_A.txt", 5, None, "متوافق"),
        ("06_Request_B.txt", 2, 7, "مخالف"),
        ("07_Request_C.txt", None, None, "خارج النطاق"),
        ("08_Request_D.txt", 1, None, "عاجل ويتطلب موافقة"),
        ("09_Request_E.txt", None, None, "خارج النطاق"),
    ],
)
def test_supplied_request_regressions_without_production_branching(
    tmp_path: Path,
    filename: str,
    expected_primary: int | None,
    expected_secondary: int | None,
    expected_policy: str,
) -> None:
    request_text = (DEFAULT_REFERENCE_DIR / filename).read_text(encoding="utf-8")

    outcome = process_request(
        request_text,
        f"ملف مرفوع: {filename}",
        SemanticSampleFakeLLM(),
        reference_dir=DEFAULT_REFERENCE_DIR,
        results_path=tmp_path / "results.csv",
    )

    assert outcome.request.analysis.primary_service_id == expected_primary
    assert outcome.request.analysis.secondary_service_id == expected_secondary
    assert outcome.request.summary.policy_status == expected_policy


def test_request_b_discloses_missing_register_and_contact_data(tmp_path: Path) -> None:
    request_text = (DEFAULT_REFERENCE_DIR / "06_Request_B.txt").read_text(
        encoding="utf-8"
    )
    outcome = process_request(
        request_text,
        "ملف مرفوع",
        SemanticSampleFakeLLM(),
        results_path=tmp_path / "results.csv",
    )

    assert "السجل التجاري" in outcome.request.summary.missing_data
    assert "صفة شخص التواصل" in outcome.request.summary.missing_data
    assert "وسيلة التواصل" in outcome.request.summary.missing_data


def test_request_e_requests_clarification_and_flags_commercial_language(
    tmp_path: Path,
) -> None:
    request_text = (DEFAULT_REFERENCE_DIR / "09_Request_E.txt").read_text(
        encoding="utf-8"
    )
    outcome = process_request(
        request_text,
        "ملف مرفوع",
        SemanticSampleFakeLLM(),
        results_path=tmp_path / "results.csv",
    )

    assert "استيضاح" in outcome.request.summary.next_step
    assert any("سعرًا أو خصمًا" in alert for alert in outcome.request.summary.alerts)

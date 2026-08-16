from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.models import AIAnalysis, ServiceDefinition
from src.processor import process_request
from src.reference_loader import DEFAULT_REFERENCE_DIR


class FakeLLM:
    def __init__(self, analysis: AIAnalysis) -> None:
        self.analysis = analysis
        self.calls = 0

    def analyze(
        self, request_text: str, services: Sequence[ServiceDefinition]
    ) -> AIAnalysis:
        self.calls += 1
        return self.analysis


def _analysis(service_id: int = 5) -> AIAnalysis:
    return AIAnalysis(
        organization_name="شركة الاختبار",
        contact_name="سارة",
        contact_role="مديرة العمليات",
        contact_method="sara@example.com",
        need_summary="إنشاء لوحة بيانات",
        requested_deadline_text="خلال 5 أيام عمل",
        requested_working_days=5,
        commercial_register_text="سجل ساري رقم 123",
        primary_service_id=service_id,
        classification_state="matched",
        classification_reason="المخرج المطلوب لوحة بيانات.",
    )


def test_processing_auto_saves_a_pending_result(tmp_path: Path) -> None:
    client = FakeLLM(_analysis())
    results_path = tmp_path / "results.csv"

    outcome = process_request(
        "نحتاج إلى لوحة بيانات خلال 5 أيام عمل.",
        "نص ملصق",
        client,
        reference_dir=DEFAULT_REFERENCE_DIR,
        results_path=results_path,
        now=lambda: datetime(2026, 8, 16, 9, 0, tzinfo=UTC),
        new_request_id=lambda: "request-1",
    )

    assert client.calls == 1
    assert outcome.request.summary.review_status == "بانتظار المراجعة"
    assert outcome.request.summary.policy_status == "متوافق"
    assert "5. تحليل البيانات ولوحات ذكاء الأعمال" in outcome.rendered_summary
    assert results_path.exists()
    assert "بانتظار المراجعة" in results_path.read_text(encoding="utf-8-sig")


def test_invalid_fake_llm_service_id_is_not_persisted(tmp_path: Path) -> None:
    results_path = tmp_path / "results.csv"

    with pytest.raises(ValueError, match="99"):
        process_request(
            "طلب",
            "نص ملصق",
            FakeLLM(_analysis(99)),
            reference_dir=DEFAULT_REFERENCE_DIR,
            results_path=results_path,
        )

    assert not results_path.exists()


def test_empty_request_does_not_call_model_or_persist(tmp_path: Path) -> None:
    client = FakeLLM(_analysis())
    results_path = tmp_path / "results.csv"

    with pytest.raises(ValueError, match="فارغ"):
        process_request(
            "  ",
            "نص ملصق",
            client,
            results_path=results_path,
        )

    assert client.calls == 0
    assert not results_path.exists()

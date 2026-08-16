from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.models import AIAnalysis
from src.processor import process_request as real_process_request
from src.review import approve_request as real_approve_request


APP_PATH = Path(__file__).parents[1] / "app.py"


def test_initial_app_renders_input_without_running_the_model() -> None:
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)

    assert not app.exception
    assert app.title[0].value == "مساعد معالجة طلبات العملاء"
    assert app.segmented_control[0].value == "نص ملصق"
    assert app.text_area[0].label == "نص طلب العميل"
    assert any(button.label == "معالجة الطلب" for button in app.button)


def test_file_mode_exposes_supported_upload_control() -> None:
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)

    app.segmented_control[0].set_value("ملف مرفوع").run(timeout=20)

    assert not app.exception
    assert app.file_uploader[0].label == "ملف الطلب"


def test_missing_api_key_shows_setup_message(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr("src.llm_client.load_dotenv", lambda: None)
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.text_area[0].input("نحتاج إلى لوحة بيانات.")

    next(button for button in app.button if button.label == "معالجة الطلب").click().run(
        timeout=20
    )

    assert not app.exception
    assert any("LLM_API_KEY" in error.value for error in app.error)


def test_full_pasted_request_to_approval_flow(monkeypatch, tmp_path: Path) -> None:
    results_path = tmp_path / "results.csv"

    class FakeLLM:
        def analyze(self, request_text, services):
            return AIAnalysis(
                organization_name="شركة التدفق الافتراضية",
                contact_name="مها",
                contact_role="مديرة التدريب",
                contact_method="maha@example.test",
                need_summary="ورشة تدريب على أدوات الذكاء الاصطناعي.",
                requested_deadline_text="خلال 5 أيام عمل",
                requested_working_days=5,
                commercial_register_text="سجل افتراضي رقم 123",
                primary_service_id=6,
                classification_state="matched",
                classification_reason="المخرج الأساسي ورشة تدريب.",
            )

    def process_for_test(raw_request, input_source, llm_client):
        return real_process_request(
            raw_request,
            input_source,
            llm_client,
            results_path=results_path,
            new_request_id=lambda: "ui-flow-request",
        )

    def approve_for_test(outcome, edited_analysis):
        return real_approve_request(
            outcome,
            edited_analysis,
            results_path=results_path,
        )

    monkeypatch.setattr(
        "src.llm_client.OpenAICompatibleLLM.from_env",
        classmethod(lambda cls: FakeLLM()),
    )
    monkeypatch.setattr("src.processor.process_request", process_for_test)
    monkeypatch.setattr("src.review.approve_request", approve_for_test)

    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.text_area[0].input("نحتاج ورشة تدريبية خلال 5 أيام عمل.")
    next(button for button in app.button if button.label == "معالجة الطلب").click().run(
        timeout=20
    )

    assert not app.exception
    assert any(header.value == "نتيجة المعالجة" for header in app.header)
    next(button for button in app.button if button.label == "اعتماد").click().run(
        timeout=20
    )

    assert not app.exception
    assert any("تم اعتماد الطلب" in success.value for success in app.success)
    csv_text = results_path.read_text(encoding="utf-8-sig")
    assert csv_text.count("ui-flow-request") == 1
    assert "تمت المراجعة" in csv_text

from pathlib import Path

from streamlit.testing.v1 import AppTest


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

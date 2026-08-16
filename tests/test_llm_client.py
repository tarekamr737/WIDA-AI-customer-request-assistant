from pathlib import Path
from types import SimpleNamespace

import pytest

from src.llm_client import LLMProviderError, LLMResponseError, OpenAICompatibleLLM
from src.models import ServiceDefinition


VALID_RESPONSE = """{
  "organization_name": null,
  "contact_name": null,
  "contact_role": null,
  "contact_method": null,
  "need_summary": "إنشاء لوحة بيانات",
  "requested_deadline_text": null,
  "requested_working_days": null,
  "commercial_register_text": null,
  "primary_service_id": 5,
  "secondary_service_id": null,
  "classification_state": "matched",
  "classification_reason": "المخرج المطلوب لوحة بيانات"
}"""

INVALID_SERVICE_RESPONSE = VALID_RESPONSE.replace(
    '"primary_service_id": 5', '"primary_service_id": 99'
)


class FakeCompletions:
    def __init__(self, responses: list[str | Exception]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=response))]
        )


def _service() -> ServiceDefinition:
    return ServiceDefinition(
        id=5,
        name="تحليل البيانات",
        description="وصف",
        use_when="لوحة بيانات",
        exclusions="تطبيق كامل",
        min_days=4,
        max_days=8,
    )


def _adapter(
    tmp_path: Path, responses: list[str | Exception]
) -> tuple[OpenAICompatibleLLM, FakeCompletions]:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("Return JSON only.", encoding="utf-8")
    completions = FakeCompletions(responses)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    adapter = OpenAICompatibleLLM(
        api_key="test-key",
        model="test-model",
        prompt_path=prompt_path,
        client=client,
    )
    return adapter, completions


def test_valid_response_uses_exactly_one_call(tmp_path: Path) -> None:
    adapter, completions = _adapter(tmp_path, [VALID_RESPONSE])

    analysis = adapter.analyze("طلب لوحة بيانات", [_service()])

    assert analysis.primary_service_id == 5
    assert len(completions.calls) == 1


def test_invalid_json_gets_one_successful_repair_retry(tmp_path: Path) -> None:
    adapter, completions = _adapter(tmp_path, ["not-json", VALID_RESPONSE])

    adapter.analyze("طلب لوحة بيانات", [_service()])

    assert len(completions.calls) == 2
    assert "خطأ التحقق" in completions.calls[1]["messages"][-1]["content"]


def test_unknown_service_id_gets_one_repair_retry(tmp_path: Path) -> None:
    adapter, completions = _adapter(tmp_path, [INVALID_SERVICE_RESPONSE, VALID_RESPONSE])

    analysis = adapter.analyze("طلب لوحة بيانات", [_service()])

    assert analysis.primary_service_id == 5
    assert len(completions.calls) == 2


def test_invalid_repair_stops_after_two_calls(tmp_path: Path) -> None:
    adapter, completions = _adapter(tmp_path, ["not-json", "still-not-json"])

    with pytest.raises(LLMResponseError, match="محاولة إصلاح واحدة"):
        adapter.analyze("طلب لوحة بيانات", [_service()])

    assert len(completions.calls) == 2


def test_provider_exception_is_replaced_with_safe_message(tmp_path: Path) -> None:
    adapter, _ = _adapter(tmp_path, [RuntimeError("secret-bearing provider detail")])

    with pytest.raises(LLMProviderError) as caught:
        adapter.analyze("طلب لوحة بيانات", [_service()])

    assert "secret-bearing" not in str(caught.value)


def test_prompt_edit_applies_on_the_next_analysis_call(tmp_path: Path) -> None:
    adapter, completions = _adapter(tmp_path, [VALID_RESPONSE, VALID_RESPONSE])

    adapter.analyze("الطلب الأول", [_service()])
    adapter.prompt_path.write_text("Updated prompt rules.", encoding="utf-8")
    adapter.analyze("الطلب الثاني", [_service()])

    assert completions.calls[0]["messages"][0]["content"] == "Return JSON only."
    assert completions.calls[1]["messages"][0]["content"] == "Updated prompt rules."

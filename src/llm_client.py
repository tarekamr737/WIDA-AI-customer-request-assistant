"""Small OpenAI-compatible adapter for request extraction and classification."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol
import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from src.models import AIAnalysis, ServiceDefinition


DEFAULT_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "analyze_request.md"


class LLMError(RuntimeError):
    """Base class for safe, user-facing LLM errors."""


class LLMConfigurationError(LLMError):
    pass


class LLMProviderError(LLMError):
    pass


class LLMResponseError(LLMError):
    pass


class AnalysisClient(Protocol):
    def analyze(self, request_text: str, services: Sequence[ServiceDefinition]) -> AIAnalysis: ...


class OpenAICompatibleLLM:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        prompt_path: Path = DEFAULT_PROMPT_PATH,
        client: Any | None = None,
    ) -> None:
        if not api_key.strip():
            raise LLMConfigurationError("LLM_API_KEY غير مضبوط. أضفه إلى ملف .env.")
        if not model.strip():
            raise LLMConfigurationError("LLM_MODEL غير مضبوط. أضفه إلى ملف .env.")
        self.model = model.strip()
        self.prompt_path = prompt_path
        self._client = client or OpenAI(api_key=api_key, base_url=base_url or None)

    @classmethod
    def from_env(cls, *, prompt_path: Path = DEFAULT_PROMPT_PATH) -> "OpenAICompatibleLLM":
        load_dotenv()
        return cls(
            api_key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", ""),
            base_url=os.getenv("LLM_BASE_URL") or None,
            prompt_path=prompt_path,
        )

    def _load_prompt(self) -> str:
        try:
            prompt = self.prompt_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as exc:
            raise LLMConfigurationError("تعذر قراءة ملف تعليمات التحليل.") from exc
        if not prompt:
            raise LLMConfigurationError("ملف تعليمات التحليل فارغ.")
        return prompt

    def _complete(self, messages: list[dict[str, str]]) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0,
            )
            content = response.choices[0].message.content
        except Exception as exc:
            raise LLMProviderError(
                "تعذر الاتصال بمزود النموذج. تحقق من الإعدادات والاتصال ثم أعد المحاولة."
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMResponseError("أعاد مزود النموذج استجابة فارغة.")
        return content

    @staticmethod
    def _parse(content: str) -> tuple[AIAnalysis | None, str | None]:
        try:
            payload = json.loads(content)
            return AIAnalysis.model_validate(payload), None
        except json.JSONDecodeError as exc:
            return None, f"JSON syntax error at position {exc.pos}"
        except ValidationError as exc:
            compact_errors = exc.errors(include_input=False, include_url=False)
            return None, json.dumps(compact_errors, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _request_payload(request_text: str, services: Sequence[ServiceDefinition]) -> str:
        payload = {
            "customer_request": request_text,
            "service_catalog": [service.model_dump() for service in services],
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def analyze(self, request_text: str, services: Sequence[ServiceDefinition]) -> AIAnalysis:
        if not request_text.strip():
            raise LLMResponseError("نص الطلب فارغ.")
        prompt = self._load_prompt()
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": self._request_payload(request_text, services)},
        ]

        first_content = self._complete(messages)
        analysis, validation_error = self._parse(first_content)
        if analysis is not None:
            return analysis

        repair_messages = [
            *messages,
            {"role": "assistant", "content": first_content},
            {
                "role": "user",
                "content": (
                    "أصلح كائن JSON فقط ليتوافق مع المخطط. لا تضف شرحًا. "
                    f"خطأ التحقق: {validation_error}"
                ),
            },
        ]
        repaired_content = self._complete(repair_messages)
        repaired_analysis, _ = self._parse(repaired_content)
        if repaired_analysis is None:
            raise LLMResponseError(
                "تعذر التحقق من استجابة النموذج بعد محاولة إصلاح واحدة. أعد المحاولة."
            )
        return repaired_analysis

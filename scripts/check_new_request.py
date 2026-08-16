"""Live smoke check using a fictional request that is not in the supplied samples."""

from pathlib import Path
import sys

from src.llm_client import OpenAICompatibleLLM
from src.processor import process_request


SYNTHETIC_REQUEST = """الجهة: شركة التجربة الافتراضية الجديدة
شخص التواصل: مها أحمد - مديرة الموارد البشرية
وسيلة التواصل: maha@example.test
الاحتياج: نحتاج ورشة تدريبية لموظفي الإدارة عن الاستخدام العملي لأدوات الذكاء الاصطناعي ونقل المعرفة إلى الفريق.
الموعد المطلوب: خلال 5 أيام عمل.
السجل التجاري: سجل افتراضي رقم 1000000000.
"""


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    outcome = process_request(
        SYNTHETIC_REQUEST,
        "اختبار يدوي بطلب افتراضي جديد",
        OpenAICompatibleLLM.from_env(),
        results_path=Path("data") / "manual_new_request_results.csv",
    )
    analysis = outcome.request.analysis
    print(
        "Synthetic request result: "
        f"primary={analysis.primary_service_id} "
        f"secondary={analysis.secondary_service_id} "
        f"policy={outcome.request.summary.policy_status}"
    )
    if analysis.primary_service_id != 6:
        print("Expected training service ID 6.")
        return 1
    print("Brand-new fictional request passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Optional live regression check for the five supplied customer requests."""

from pathlib import Path
import sys

from src.llm_client import OpenAICompatibleLLM
from src.processor import process_request
from src.reference_loader import DEFAULT_REFERENCE_DIR


EXPECTED = {
    "05_Request_A.txt": (5, None, "متوافق"),
    "06_Request_B.txt": (2, 7, "مخالف"),
    "07_Request_C.txt": (None, None, "خارج النطاق"),
    "08_Request_D.txt": (1, None, "عاجل ويتطلب موافقة"),
    "09_Request_E.txt": (None, None, "خارج النطاق"),
}


def main() -> int:
    client = OpenAICompatibleLLM.from_env()
    results_path = Path("data") / "manual_regression_results.csv"
    failures: list[str] = []

    for filename, expected in EXPECTED.items():
        request_text = (DEFAULT_REFERENCE_DIR / filename).read_text(encoding="utf-8")
        outcome = process_request(
            request_text,
            f"اختبار يدوي: {filename}",
            client,
            results_path=results_path,
        )
        actual = (
            outcome.request.analysis.primary_service_id,
            outcome.request.analysis.secondary_service_id,
            outcome.request.summary.policy_status,
        )
        passed = actual == expected
        print(f"{filename}: {'PASS' if passed else 'FAIL'} actual={actual}")
        if not passed:
            failures.append(filename)

    if failures:
        print(f"Regression mismatches: {', '.join(failures)}", file=sys.stderr)
        return 1
    print("All supplied request regressions passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

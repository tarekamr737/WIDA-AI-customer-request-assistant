from pathlib import Path


def test_analysis_prompt_defines_the_complete_external_contract() -> None:
    prompt = (Path(__file__).parents[1] / "prompts" / "analyze_request.md").read_text(
        encoding="utf-8"
    )
    expected_keys = {
        "organization_name",
        "contact_name",
        "contact_role",
        "contact_method",
        "need_summary",
        "requested_deadline_text",
        "requested_working_days",
        "commercial_register_text",
        "primary_service_id",
        "secondary_service_id",
        "classification_state",
        "classification_reason",
    }

    assert all(f'"{key}"' in prompt for key in expected_keys)
    assert "null" in prompt
    assert "out_of_scope" in prompt
    assert "لا تقيّم السياسات" in prompt

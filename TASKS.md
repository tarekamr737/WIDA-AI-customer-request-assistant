# TASKS.md — WIDA AI Customer Request Assistant

## Must
- [x] Extract supplied package into `references/`; preserve source files unchanged.
- [x] Create Python project, `requirements.txt`, `.env.example`, `.gitignore`.
- [x] Implement Pydantic domain models.
- [x] Implement runtime service/policy reference loader.
- [ ] Parse catalog IDs/names/use-cases/exclusions/standard durations.
- [ ] Parse global minimum-execution days from current policy text.
- [ ] Implement TXT/PDF/DOCX request text extraction.
- [ ] Create compact `prompts/analyze_request.md`.
- [ ] Implement one-call OpenAI-compatible LLM adapter + one JSON repair retry.
- [ ] Validate service IDs and unknown/null behavior.
- [ ] Implement deterministic missing-data checks.
- [ ] Implement deterministic policy precedence and alerts.
- [ ] Implement exact internal-summary renderer.
- [ ] Implement UTF-8-SIG CSV append/update persistence.
- [ ] Auto-save processed result as `بانتظار المراجعة`.
- [ ] Build Streamlit input + result + editable review UI.
- [ ] Implement `اعتماد` -> update row to `تمت المراجعة`.
- [ ] Implement `يحتاج استيضاح` behavior.
- [ ] Add fake-LLM unit tests for policy/processor/storage.
- [ ] Regression-check Requests A–E without hardcoded request IDs.
- [ ] Verify a brand-new request can be processed.
- [ ] Verify changing catalog/policy/prompt takes effect after rerun.
- [ ] Create concise one-page `README.md`.
- [ ] Run `pytest -q`; fix all failures.
- [ ] Run `streamlit run app.py`; complete one full review flow.
- [ ] Confirm no API keys/secrets are committed.

## Only if time remains
- [ ] Add export/download of the reviewed summary.
- [ ] Add a tiny CLI runner for debugging.

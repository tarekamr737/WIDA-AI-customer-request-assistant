# ARCHITECTURE.md — WIDA AI Customer Request Assistant

## 1. Architecture decision
Use a small hybrid system:

`Input -> text extraction -> LLM extraction/classification -> deterministic validation/policies -> template renderer -> CSV -> human review`

The LLM handles semantic work only. Business rules remain deterministic and testable.

## 2. Stack
- Python 3.11+
- Streamlit
- Pydantic
- `openai` Python SDK used through a tiny OpenAI-compatible adapter
- `python-dotenv`
- `pypdf`
- `python-docx`
- Pytest
- Python `csv`/standard library for persistence

No LangChain, agent framework, RAG, vector DB, or external database.

## 3. Proposed repository
```text
.
├── app.py
├── src/
│   ├── models.py
│   ├── reference_loader.py
│   ├── file_parser.py
│   ├── llm_client.py
│   ├── processor.py
│   ├── policy_engine.py
│   ├── renderer.py
│   └── storage.py
├── prompts/
│   └── analyze_request.md
├── references/
│   ├── 01_Company_Profile.txt
│   ├── 02_Service_Catalog.txt
│   ├── 03_Operating_Policies.txt
│   ├── 04_Output_Template.txt
│   └── request samples...
├── tests/
│   ├── test_policy_engine.py
│   ├── test_reference_loader.py
│   └── test_processor.py
├── data/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 4. Runtime reference loading
Read reference files on every processing run; do not cache them.

`reference_loader.py` should:
- Parse the eight services into typed objects:
  - `id`
  - `name`
  - `description`
  - `use_when`
  - `exclusions`
  - `min_days`
  - `max_days`
- Parse the current global minimum-execution days from the policy text.
- Expose raw policy/template text for traceability.
- Fail clearly if required references are missing or malformed.

This makes live edits visible after rerun.

## 5. File input
`file_parser.py`:
- TXT: UTF-8 text.
- PDF: extract text with `pypdf`.
- DOCX: join paragraph text with `python-docx`.
- Reject unsupported types.
- Reject empty extraction.
- For scanned/image-only PDFs, show a clear unsupported/OCR-needed message; never guess.

## 6. Structured LLM contract
One LLM call receives:
- the customer request text;
- a compact JSON representation of the currently loaded service catalog;
- the compact prompt rules.

Do **not** send policies or output-template text to the LLM; Python owns those steps.

Expected validated model:
```python
class AIAnalysis(BaseModel):
    organization_name: str | None
    contact_name: str | None
    contact_role: str | None
    contact_method: str | None
    need_summary: str
    requested_deadline_text: str | None
    requested_working_days: int | None
    commercial_register_text: str | None
    primary_service_id: int | None
    secondary_service_id: int | None
    classification_state: Literal["matched", "out_of_scope", "unclear"]
    classification_reason: str
```

Validation rules:
- Service IDs must exist in the loaded catalog.
- Primary and secondary cannot be equal.
- `unclear`/`out_of_scope` may have no service IDs.
- Missing facts stay `None`.
- Need summary cannot introduce facts absent from the request.

If JSON is invalid:
1. one compact repair retry using the validation error;
2. otherwise fail visibly and do not persist fabricated output.

## 7. Prompt design
`prompts/analyze_request.md` should be short and explicit:

- Extract only facts present in the request.
- Use `null` when absent.
- Classify only using supplied catalog entries.
- Respect `use_when` and `exclusions`.
- Do not force a match.
- Secondary service only with clear independent evidence.
- Do not evaluate policy, pricing, or commercial approval.
- Output JSON only matching the requested schema.

This keeps model tokens and responsibilities small.

## 8. Deterministic post-processing
`processor.py`:
1. Load current references.
2. Parse input text/file.
3. Call LLM once.
4. Validate `AIAnalysis`.
5. Resolve selected service IDs to exact catalog names/durations.
6. Compute missing required data.
7. Run policy engine.
8. Build exact internal-output model.
9. Save pending result.
10. Return result to UI.

## 9. Missing-data logic
Core fields from policy:
- organization name;
- contact name;
- contact role/title;
- at least one contact method;
- need description;
- requested date/deadline when applicable;
- commercial register for execution.

Use deterministic checks over the validated fields.

## 10. Policy engine
Input:
- validated analysis;
- selected service(s);
- parsed policy configuration.

Output:
```python
class PolicyResult(BaseModel):
    status: Literal[
        "متوافق",
        "عاجل ويتطلب موافقة",
        "مخالف",
        "خارج النطاق",
    ]
    alerts: list[str]
    next_step: str
```

Recommended precedence:
1. `out_of_scope` or no defensible classification -> `خارج النطاق`; ask for clarification/sales review.
2. Explicit requested duration below global minimum -> `مخالف`.
3. Missing commercial register -> `مخالف` for execution; classification may still be shown.
4. Requested duration >= global minimum but below primary service standard minimum -> `عاجل ويتطلب موافقة`.
5. Otherwise -> `متوافق`.

Always add separate alerts for:
- missing contact/basic data;
- secondary-service involvement;
- requested free/discount/pricing promises;
- ambiguous scope;
- any other documented policy issue.

Never invent a price or approval.

## 11. Internal output model
Create a Pydantic model matching the supplied template fields.

Commercial-register display:
- present text -> `متوفر`
- explicitly absent -> `غير متوفر`
- ambiguous -> `غير واضح`

Review status:
- initial: `بانتظار المراجعة`
- after approval: `تمت المراجعة`

`renderer.py` renders the fields in the exact supplied template order.

## 12. Storage
`storage.py` uses `data/results.csv`.

Behavior:
- Generate `request_id` with UUID.
- On processing, append a pending row automatically.
- On human edit/approval, update by `request_id`.
- Preserve raw request and input source.
- Use UTF-8-SIG so Arabic opens cleanly in Excel.
- Avoid duplicate rows when approving.

## 13. Streamlit UI
Minimal single-page layout:

1. Title + short reference-grounding note.
2. Input tabs:
   - pasted text;
   - uploaded file.
3. `معالجة الطلب` button.
4. Result section:
   - editable extracted fields;
   - proposed primary/secondary service;
   - policy status;
   - alerts;
   - next step;
   - rendered internal summary.
5. Human review actions:
   - `اعتماد`
   - `يحتاج استيضاح`
6. Small expander for classification reason/source service details.
7. Clear success/error messages.

Keep UI functional, not decorative.

## 14. Environment
`.env.example`:
```env
LLM_API_KEY=
LLM_MODEL=
LLM_BASE_URL=
```

`LLM_BASE_URL` is optional so the same adapter can work with compatible providers.
Never commit `.env`.

## 15. Testing strategy
Do not call a live model in unit tests.

Use a fake LLM client returning typed `AIAnalysis`.

Must test:
- commercial register missing blocks execution;
- requested duration below global minimum is `مخالف`;
- duration between global minimum and service minimum is `عاجل ويتطلب موافقة`;
- normal duration is `متوافق`;
- out-of-scope is not force-classified;
- invalid service ID is rejected;
- primary/secondary cannot duplicate;
- CSV append/update works;
- reference parser extracts service durations and policy minimum.

Add a small optional manual/integration script for Requests A–E only after unit tests pass.

## 16. Error handling
Show actionable errors for:
- missing API config;
- provider/network failure;
- invalid model JSON after retry;
- missing reference file;
- unreadable upload;
- unsupported file type;
- empty request.

Never persist a fabricated successful result after a failed AI call.

## 17. Why this design
- Small reference set: RAG adds complexity without benefit.
- One LLM call: lower latency/cost/tokens.
- Deterministic policies: predictable and easy to test.
- External prompt/references: easy live modification.
- Streamlit: fastest reliable demo path.
- CSV: satisfies persistence with minimal setup.
- Separation of concerns: easy to explain and edit during the 30-minute review.

## 18. README requirements
Keep README about one page:
- what the solution does;
- architecture in one paragraph;
- setup/install;
- `.env` variables;
- run command;
- where references/prompts live;
- how to change services/policies/prompts;
- tests command;
- known limitations (notably scanned-PDF OCR and production hardening).

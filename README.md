# WIDA AI customer request assistant

A small Arabic-first internal assistant for Horizon B2B Services. It accepts pasted text or a TXT/PDF/DOCX request, extracts only stated facts, classifies against the eight supplied services, applies operating policies deterministically, saves a pending audit row, and lets a reviewer correct, approve, or request clarification. It never sends a customer message.

## Architecture and tools

The flow is `input → text extraction → one LLM extraction/classification call → Pydantic validation → Python policy checks → supplied template → UTF-8-SIG CSV → human review`. The implementation uses Python 3.11+, Streamlit, Pydantic, the OpenAI SDK through a small OpenAI-compatible adapter, `pypdf`, `python-docx`, standard-library CSV, and Pytest. There is no agent framework, database, vector store, RAG, or embedding call; the catalog is small enough to send directly with each request.

## Setup on Windows

```powershell
Set-Location D:\WIDA
python -m venv .venv
$env:PIP_CACHE_DIR="$PWD\.pip-cache"
$env:TEMP="$PWD\.tmp"
$env:TMP="$PWD\.tmp"
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```env
LLM_API_KEY=your_openrouter_key
LLM_MODEL=google/gemma-4-26b-a4b-it:free
LLM_BASE_URL=https://openrouter.ai/api/v1
```

`.env` and generated CSV files are ignored by Git. Start the app with:

```powershell
.venv\Scripts\streamlit.exe run app.py
```

Open the shown local URL, submit a request, review the editable fields, then choose `اعتماد` or `يحتاج استيضاح`. Results are written to `data/results.csv` with readable Arabic, reviewer-first columns; approval updates the same row to `تمت المراجعة`.

## Tests and checks

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m scripts.check_new_request
```

The test suite uses fake LLM clients and makes no network calls. `check_new_request` is an optional live check with fictional data. `python -m scripts.check_samples` sends the supplied A–E request contents—including their contact details—to the configured provider; run it only when that data export is explicitly authorized.

## Updating behavior

- Services and standard durations: `references/02_Service_Catalog.txt`
- Operating rules and global minimum duration: `references/03_Operating_Policies.txt`
- Internal summary layout: `references/04_Output_Template.txt`
- Extraction/classification instructions: `prompts/analyze_request.md`

These files are read at request time, so edits apply on the next Streamlit rerun without rebuilding. Keep the documented Arabic labels and parseable duration wording intact.

## Limitations

- Scanned/image-only PDFs require OCR and are rejected clearly.
- The LLM provider receives the submitted request and compact service catalog; use only data approved for that provider.
- CSV storage is local and intended for a single-reviewer demo, not concurrent production use.
- There is no authentication, outbound messaging, pricing generation, OCR, deployment hardening, or production database.
- Model availability and free-tier rate limits are controlled by OpenRouter.

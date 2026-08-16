# PRODUCT.md — WIDA AI Customer Request Assistant

## 1. Product goal
Build a small, runnable assistant for Horizon B2B Services that converts an incoming customer request into a trustworthy internal processing summary.

The assistant must reduce the current manual workflow while staying grounded in the supplied service catalog, operating policies, and output template.

## 2. Primary user
An internal sales/operations employee reviewing a new B2B customer request before any commitment is sent to the customer.

## 3. Core user flow
1. User pastes request text or uploads a request file.
2. System extracts the request facts.
3. System classifies the request against the eight documented services only.
4. System applies operating policies.
5. System shows a structured internal summary plus alerts/missing data.
6. System auto-saves the result as `بانتظار المراجعة`.
7. Human reviewer can correct fields.
8. Reviewer approves; stored result becomes `تمت المراجعة`.

## 4. Required extracted fields
- Organization name.
- Contact name.
- Contact role/title.
- At least one contact method.
- Precise need summary.
- Requested deadline text.
- Requested number of working days when explicitly derivable.
- Commercial-register status/details.
- Missing required data.

Unknown information must remain unknown; never infer it.

## 5. Service classification
Classify only against `02_Service_Catalog.txt`.

Output:
- Primary service: service ID + exact catalog name, or `غير محدد` / `خارج النطاق`.
- Secondary service: only when there is clear evidence.
- Short classification reason for the review UI.

Rules:
- Never create a ninth service.
- Never merge two services into a new label.
- Never force an ambiguous request into the nearest service.

## 6. Policy enforcement
Use `03_Operating_Policies.txt` as the authority.

At minimum enforce:
- Commercial register required before official execution.
- Minimum execution duration.
- Urgent deadline rule relative to the selected service's standard minimum.
- Missing contact/basic data disclosure.
- Out-of-scope handling.
- Multi-service handling.
- No invented pricing, discount, or free-work approval.
- Human review before any final commitment.

Policy status shown in the supplied template must use its documented values:
- `متوافق`
- `عاجل ويتطلب موافقة`
- `مخالف`
- `خارج النطاق`

## 7. Output
Render the fields in the same order and meaning as `04_Output_Template.txt`:

- اسم الجهة
- شخص التواصل وصفته
- وسيلة التواصل
- ملخص الاحتياج
- الخدمة الأساسية المقترحة
- الخدمة الثانوية إن وجدت
- السجل التجاري
- الموعد المطلوب
- تقييم السياسات
- البيانات الناقصة
- التنبيهات المهمة
- الخطوة التالية المقترحة
- حالة المراجعة البشرية

The need summary must be faithful to the request and add no facts.

## 8. Storage
Persist each processed result to `data/results.csv`.

Minimum metadata:
- `request_id`
- `created_at`
- `updated_at`
- `input_source`
- `raw_request`
- all structured output fields
- `review_status`

Processing creates/updates a row with `بانتظار المراجعة`.
Approval updates the same row to `تمت المراجعة`.

## 9. Human-in-the-loop
Before approval, show editable structured fields.

Reviewer actions:
- `اعتماد` → validate, update stored row, mark reviewed.
- `يحتاج استيضاح` → keep pending and make the next step explicit.

No customer email/message sending is required.

## 10. Ground-truth regression expectations
These are behavioral checks, not hardcoded branches:

| Request | Expected core behavior |
|---|---|
| A | Primary service 5 (تحليل البيانات ولوحات ذكاء الأعمال); timing not urgent; commercial register present. |
| B | Primary 2 (أتمتة العمليات والحلول الذكية), secondary 7 (التكامل والربط بين الأنظمة); flag missing commercial register and incomplete contact data. |
| C | Marketing/social-media request is outside the eight documented services; do not force a classification. |
| D | Primary service 1 (الاستشارات الإدارية والتحول التشغيلي); 6 working days is below its 10-day standard minimum but above the global minimum, so flag urgent/approval. |
| E | Too vague for a reliable service commitment; preserve unknowns, flag missing data, and request clarification rather than inventing scope/cost/date. |

## 11. Must acceptance criteria
- Runnable locally during live review.
- Handles pasted Arabic request text.
- Handles at least TXT upload; PDF/DOCX support should also be included.
- Uses supplied references, not model general knowledge.
- Produces structured, validated output.
- Does not hallucinate missing facts.
- Correctly enforces timing and commercial-register rules.
- Supports out-of-scope/ambiguous requests.
- Supports primary/secondary services.
- Auto-saves results.
- Provides a real human approval step.
- Service/policy/prompt edits are easy and do not require rebuilding.
- No API key or secret in source control.
- Tests cover deterministic policy behavior.
- README is concise and sufficient to run the project.

## 12. Out of scope
- Authentication.
- Multi-user roles.
- Production cloud deployment.
- Email/WhatsApp sending.
- Google Sheets/Airtable integration.
- OCR for scanned PDFs.
- Embeddings/vector databases/RAG.
- Long-term analytics dashboard.
- Pricing generation.
- Full workflow orchestration platform.

## 13. Success definition
A reviewer can launch the app, submit a brand-new request, inspect why it was classified, see policy alerts, edit/approve the result, verify persistence, then change a reference/prompt and rerun without changing the application architecture.

"""Streamlit interface for the Horizon customer request assistant."""

import streamlit as st

from src.file_parser import FileParseError, extract_request_text
from src.llm_client import LLMError, OpenAICompatibleLLM
from src.models import AIAnalysis
from src.processor import ProcessingOutcome, process_request
from src.reference_loader import ReferenceLoadError
from src.renderer import RenderError
from src.review import approve_request
from src.storage import StorageError


st.set_page_config(
    page_title="مساعد معالجة طلبات هورايزون",
    page_icon=":material/assignment:",
    layout="centered",
)

st.session_state.setdefault("processing_outcome", None)
review_notice = st.session_state.pop("review_notice", None)

st.title("مساعد معالجة طلبات العملاء")
st.caption(
    "أداة داخلية تستخرج بيانات الطلب، وتقترح الخدمة من دليل هورايزون فقط، "
    "ثم تطبق السياسات قبل المراجعة البشرية."
)
if review_notice:
    st.success(review_notice, icon=":material/check_circle:")

with st.container(border=True):
    st.subheader("طلب جديد", anchor=False)
    input_mode = st.segmented_control(
        "طريقة إدخال الطلب",
        options=["نص ملصق", "ملف مرفوع"],
        default="نص ملصق",
        required=True,
        key="input_mode",
        width="stretch",
    )

    with st.form("request_input_form", border=False):
        if input_mode == "ملف مرفوع":
            uploaded_file = st.file_uploader(
                "ملف الطلب",
                type=["txt", "pdf", "docx"],
                max_upload_size=10,
                help="ملفات PDF الممسوحة ضوئيًا تحتاج OCR وغير مدعومة حاليًا.",
            )
            pasted_text = None
        else:
            pasted_text = st.text_area(
                "نص طلب العميل",
                height=190,
                placeholder="الصق نص الطلب العربي هنا كما ورد من العميل…",
                key="pasted_request",
            )
            uploaded_file = None

        submitted = st.form_submit_button(
            "معالجة الطلب",
            type="primary",
            icon=":material/auto_awesome:",
            width="stretch",
        )

if submitted:
    try:
        if input_mode == "ملف مرفوع":
            if uploaded_file is None:
                raise FileParseError("اختر ملف طلب قبل بدء المعالجة.")
            raw_request = extract_request_text(uploaded_file.name, uploaded_file.getvalue())
            input_source = f"ملف مرفوع: {uploaded_file.name}"
        else:
            raw_request = pasted_text or ""
            input_source = "نص ملصق"

        with st.spinner("جارٍ تحليل الطلب وتطبيق السياسات…"):
            llm_client = OpenAICompatibleLLM.from_env()
            st.session_state.processing_outcome = process_request(
                raw_request,
                input_source,
                llm_client,
            )
    except (FileParseError, LLMError, ReferenceLoadError, RenderError, StorageError, ValueError) as exc:
        st.error(str(exc), icon=":material/error:")

outcome: ProcessingOutcome | None = st.session_state.processing_outcome
if outcome is not None:
    request = outcome.request
    analysis = request.analysis
    summary = request.summary
    service_by_id = {service.id: service for service in outcome.references.services}
    service_options = [None, *service_by_id]

    st.header("نتيجة المعالجة", anchor=False)
    with st.container(horizontal=True, vertical_alignment="center"):
        policy_colors = {
            "متوافق": "green",
            "عاجل ويتطلب موافقة": "orange",
            "مخالف": "red",
            "خارج النطاق": "gray",
        }
        st.badge(summary.policy_status, color=policy_colors[summary.policy_status])
        st.badge(summary.review_status, color="orange")
        st.caption(f"رقم الطلب: {request.request_id}")

    if summary.alerts:
        with st.container(border=True):
            st.subheader("تنبيهات المعالجة", anchor=False)
            for alert in summary.alerts:
                st.warning(alert, icon=":material/warning:")

    with st.form(f"review_form_{request.request_id}"):
        st.subheader("مراجعة الحقول", anchor=False)
        organization_name = st.text_input(
            "اسم الجهة",
            value=analysis.organization_name or "",
            key=f"organization_{request.request_id}",
        )
        contact_columns = st.columns(2)
        with contact_columns[0]:
            contact_name = st.text_input(
                "اسم شخص التواصل",
                value=analysis.contact_name or "",
                key=f"contact_name_{request.request_id}",
            )
        with contact_columns[1]:
            contact_role = st.text_input(
                "صفة شخص التواصل",
                value=analysis.contact_role or "",
                key=f"contact_role_{request.request_id}",
            )
        contact_method = st.text_input(
            "وسيلة التواصل",
            value=analysis.contact_method or "",
            key=f"contact_method_{request.request_id}",
        )
        need_summary = st.text_area(
            "ملخص الاحتياج",
            value=analysis.need_summary,
            height=120,
            key=f"need_{request.request_id}",
        )
        deadline_columns = st.columns(2)
        with deadline_columns[0]:
            requested_deadline_text = st.text_input(
                "الموعد المطلوب كما ورد",
                value=analysis.requested_deadline_text or "",
                key=f"deadline_{request.request_id}",
            )
        with deadline_columns[1]:
            requested_working_days = st.number_input(
                "عدد أيام العمل القابل للاشتقاق",
                min_value=1,
                value=analysis.requested_working_days,
                step=1,
                placeholder="غير محدد",
                key=f"days_{request.request_id}",
            )
        commercial_register_text = st.text_input(
            "حالة/تفاصيل السجل التجاري",
            value=analysis.commercial_register_text or "",
            key=f"register_{request.request_id}",
        )

        service_columns = st.columns(2)
        service_label = lambda service_id: (
            "لا توجد" if service_id is None else f"{service_id}. {service_by_id[service_id].name}"
        )
        with service_columns[0]:
            primary_service_id = st.selectbox(
                "الخدمة الأساسية",
                options=service_options,
                index=service_options.index(analysis.primary_service_id),
                format_func=service_label,
                key=f"primary_{request.request_id}",
            )
        with service_columns[1]:
            secondary_service_id = st.selectbox(
                "الخدمة الثانوية",
                options=service_options,
                index=service_options.index(analysis.secondary_service_id),
                format_func=service_label,
                key=f"secondary_{request.request_id}",
            )
        classification_state = st.selectbox(
            "حالة التصنيف",
            options=["matched", "out_of_scope", "unclear"],
            index=["matched", "out_of_scope", "unclear"].index(
                analysis.classification_state
            ),
            format_func={
                "matched": "مطابق لخدمة موثقة",
                "out_of_scope": "خارج النطاق",
                "unclear": "غير واضح",
            }.get,
            key=f"classification_state_{request.request_id}",
        )
        classification_reason = st.text_area(
            "سبب التصنيف",
            value=analysis.classification_reason,
            height=100,
            key=f"reason_{request.request_id}",
        )

        with st.container(horizontal=True, horizontal_alignment="right"):
            needs_clarification = st.form_submit_button(
                "يحتاج استيضاح",
                icon=":material/help:",
                disabled=True,
            )
            approved = st.form_submit_button(
                "اعتماد",
                type="primary",
                icon=":material/check_circle:",
            )

    if approved:
        try:
            edited_analysis = AIAnalysis(
                organization_name=organization_name,
                contact_name=contact_name,
                contact_role=contact_role,
                contact_method=contact_method,
                need_summary=need_summary,
                requested_deadline_text=requested_deadline_text,
                requested_working_days=(
                    int(requested_working_days)
                    if requested_working_days is not None
                    else None
                ),
                commercial_register_text=commercial_register_text,
                primary_service_id=primary_service_id,
                secondary_service_id=secondary_service_id,
                classification_state=classification_state,
                classification_reason=classification_reason,
            )
            st.session_state.processing_outcome = approve_request(
                outcome,
                edited_analysis,
            )
        except (ValueError, RenderError, StorageError) as exc:
            st.error(str(exc), icon=":material/error:")
        else:
            st.session_state.review_notice = "تم اعتماد الطلب وحفظ تعديلات المراجع."
            st.rerun()

    st.subheader("الملخص الداخلي المحفوظ", anchor=False)
    st.code(outcome.rendered_summary, language=None, wrap_lines=True)

    with st.expander("تفاصيل التصنيف والمصدر", icon=":material/info:"):
        st.write(analysis.classification_reason)
        for service_id in (analysis.primary_service_id, analysis.secondary_service_id):
            if service_id is not None:
                service = service_by_id[service_id]
                st.markdown(f"**{service.id}. {service.name}**")
                st.caption(f"تستخدم عندما: {service.use_when}")
                st.caption(f"لا تشمل: {service.exclusions}")

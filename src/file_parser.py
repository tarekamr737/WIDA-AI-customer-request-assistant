"""Extract request text from supported uploaded file formats."""

from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


class FileParseError(ValueError):
    """A user-correctable uploaded-file error."""


def _require_text(text: str, *, empty_message: str) -> str:
    normalized = text.strip()
    if not normalized:
        raise FileParseError(empty_message)
    return normalized


def _extract_txt(content: bytes) -> str:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FileParseError("تعذر قراءة ملف TXT. يرجى حفظه بترميز UTF-8.") from exc
    return _require_text(text, empty_message="ملف TXT فارغ.")


def _extract_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise FileParseError("تعذر قراءة ملف PDF المرفوع.") from exc
    return _require_text(
        text,
        empty_message=(
            "لم يُستخرج نص من ملف PDF. قد يكون ممسوحًا ضوئيًا ويحتاج إلى OCR، "
            "وهو غير مدعوم حاليًا."
        ),
    )


def _extract_docx(content: bytes) -> str:
    try:
        document = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:
        raise FileParseError("تعذر قراءة ملف DOCX المرفوع.") from exc
    return _require_text(text, empty_message="ملف DOCX لا يحتوي على نص قابل للقراءة.")


def extract_request_text(filename: str, content: bytes) -> str:
    """Extract non-empty request text based on a safe extension allowlist."""

    if not content:
        raise FileParseError("الملف المرفوع فارغ.")

    extension = Path(filename).suffix.lower()
    extractors = {
        ".txt": _extract_txt,
        ".pdf": _extract_pdf,
        ".docx": _extract_docx,
    }
    extractor = extractors.get(extension)
    if extractor is None:
        raise FileParseError("نوع الملف غير مدعوم. الأنواع المتاحة: TXT وPDF وDOCX.")
    return extractor(content)

"""
Document extractor — pluggable extraction backends.

ACTIVE APPROACH: Approach A (EasyOCR + GPT-4o)

─────────────────────────────────────────────────────────────────
APPROACH A — EasyOCR (free) + GPT-4o text call  ← ACTIVE
  Step 1: EasyOCR reads image/PDF → raw text (free, local, no API)
  Step 2: GPT-4o structures raw text → ExtractedDocument
  Cost: ~$0.003/doc (text tokens only, no vision tokens)
  Accuracy: 10/10 test cases passing

APPROACH B — EasyOCR (free) + GPT-4o-mini text call
  Same as A but cheaper. 9/10 passing — TC007 routes to MANUAL_REVIEW
  instead of REJECTED due to lower confidence scores from mini.
  Cost: ~$0.0003/doc
─────────────────────────────────────────────────────────────────
"""

from functools import lru_cache
from pathlib import Path

import easyocr
import fitz  # PyMuPDF
from openai import OpenAI

from config import settings
from models import ExtractedDocument, ExtractionResult

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ═══════════════════════════════════════════════════════════════
# APPROACH A/B — EasyOCR + LLM text call
# ═══════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def _get_reader() -> easyocr.Reader:
    print("[Extractor] Initialising EasyOCR (first call only)...")
    return easyocr.Reader(["en"], gpu=False, verbose=False)


def _image_to_text(file_path: str) -> str:
    reader = _get_reader()
    results = reader.readtext(file_path, detail=0, paragraph=True)
    return "\n".join(results)


def _pdf_to_text(file_path: str) -> str:
    doc = fitz.open(file_path)
    lines = []
    for page_num in range(min(len(doc), 3)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        png_bytes = pix.tobytes("png")
        reader = _get_reader()
        results = reader.readtext(png_bytes, detail=0, paragraph=True)
        lines.extend(results)
    doc.close()
    return "\n".join(lines)


def _file_to_text(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return _pdf_to_text(file_path)
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return _image_to_text(file_path)
    return ""


_EXTRACTION_PROMPT = """
You are a medical document parser. Extract all visible information from the
OCR text below and return it as a structured ExtractedDocument.

Rules:
- Set doc_type to one of: prescription, bill, diagnostic_report, pharmacy_bill
- Set treatment_date as 'YYYY-MM-DD' if a date is visible, otherwise null
- Return null for any field not present in the text — do not guess
- For line_items: each entry must have a "description" field (string) and
  an "amount" field (number). Example: description="Consultation Fee", amount=1000.
  Skip header rows like "DESCRIPTION OF SERVICES" or "AMOUNT" — only include
  actual charge line items with a numeric rupee value.
- Set extraction_confidence based on how complete and readable the text is
  (1.0 = all key fields present and clear, 0.5 = partial, 0.2 = very noisy)

OCR TEXT:
{ocr_text}
"""


def _extract_approach_a(file_path: str) -> ExtractedDocument:
    """Approach A: EasyOCR + GPT-4o. 10/10 passing. ~$0.003/doc."""
    ocr_text = _file_to_text(file_path)
    if not ocr_text.strip():
        raise ValueError(f"Could not extract any text from: {file_path}")

    response = openai_client.beta.chat.completions.parse(
        model="gpt-4o",          # Approach A
        # model="gpt-4o-mini",   # Approach B — 9/10, TC007 MANUAL_REVIEW instead of REJECTED
        messages=[{"role": "user", "content": _EXTRACTION_PROMPT.format(ocr_text=ocr_text)}],
        response_format=ExtractedDocument,
        max_tokens=1500,
    )
    result = response.choices[0].message.parsed
    if result is None:
        raise ValueError(f"LLM could not structure OCR text. Refusal: {response.choices[0].message.refusal}")
    return result


# ═══════════════════════════════════════════════════════════════
# ACTIVE ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def extract_document(file_path: str) -> ExtractedDocument:
    return _extract_approach_a(file_path)


# ═══════════════════════════════════════════════════════════════
# MERGE — unchanged across all approaches
# ═══════════════════════════════════════════════════════════════

def merge_extractions(
    documents: list[ExtractedDocument],
    member_name: str,
    treatment_date: str,
    claim_amount: float,
) -> ExtractionResult:
    """Consolidate multiple extracted documents into a single ExtractionResult."""

    diagnosis = ""
    for doc in documents:
        if doc.doc_type == "prescription" and doc.diagnosis:
            diagnosis = doc.diagnosis
            break
    if not diagnosis:
        for doc in documents:
            if doc.diagnosis:
                diagnosis = doc.diagnosis
                break

    date_consistent = True
    for doc in documents:
        if doc.treatment_date and doc.treatment_date != treatment_date:
            date_consistent = False
            break

    patient_name_consistent = True
    first_name = member_name.split()[0].lower()
    for doc in documents:
        if doc.patient_name and first_name not in doc.patient_name.lower():
            patient_name_consistent = False
            break

    doc_types = {doc.doc_type for doc in documents}
    missing_docs: list[str] = []
    if "prescription" not in doc_types:
        missing_docs.append("Prescription from registered doctor")
    if "bill" not in doc_types and "pharmacy_bill" not in doc_types:
        missing_docs.append("Medical bill or receipt")

    return ExtractionResult(
        documents=documents,
        merged_diagnosis=diagnosis or "Unknown",
        merged_total=claim_amount,
        date_consistent=date_consistent,
        patient_name_consistent=patient_name_consistent,
        all_required_docs_present=len(missing_docs) == 0,
        missing_docs=missing_docs,
    )

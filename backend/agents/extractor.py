"""
Document extractor — pluggable extraction backends.

ACTIVE APPROACH: Approach A (EasyOCR + GPT-4o)
To switch, comment/uncomment the relevant section in extract_document().

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

APPROACH C — Gemini 2.0 Flash vision  ← TODO (pending API key)
  Single vision call: image/PDF → ExtractedDocument directly.
  No EasyOCR needed. Free tier: 1500 req/day.
  Better handwriting + multilingual support.
  Requires: GOOGLE_API_KEY in .env
─────────────────────────────────────────────────────────────────
"""

from functools import lru_cache
from pathlib import Path

import easyocr
import fitz  # PyMuPDF
from openai import OpenAI

from config import settings
from models import ExtractedDocument, ExtractionResult

# ── Approach A/B: OpenAI client ───────────────────────────────────────────────
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# ── Approach C: Gemini client ─────────────────────────────────────────────────
import google.generativeai as genai
genai.configure(api_key=settings.GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")


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
# APPROACH C — Gemini 2.0 Flash vision  (TODO: pending API key)
# ═══════════════════════════════════════════════════════════════

_GEMINI_PROMPT = """
You are a medical document parser. Extract all visible information from this
medical document image and return a JSON object with these exact fields:

{
  "doc_type": "prescription" | "bill" | "diagnostic_report" | "pharmacy_bill",
  "doctor_name": string or null,
  "doctor_reg": string or null,
  "patient_name": string or null,
  "diagnosis": string or null,
  "medicines": [string],
  "tests_prescribed": [string],
  "procedures": [string],
  "treatment_date": "YYYY-MM-DD" or null,
  "consultation_fee": number or null,
  "total_amount": number or null,
  "line_items": [{"description": string, "amount": number}],
  "extraction_confidence": 0.0-1.0
}

Rules:
- Return null for any field not visible in the document — do not guess
- extraction_confidence: 1.0 = all fields clear, 0.5 = partial, 0.2 = very noisy
- For line_items include only actual charge rows with numeric amounts
- Return only valid JSON, no explanation
"""


def _file_to_image_parts(file_path: str) -> list:
    """Convert image or PDF pages to PIL Images (accepted directly by google-generativeai)."""
    import PIL.Image
    import io
    suffix = Path(file_path).suffix.lower()
    images = []
    if suffix == ".pdf":
        doc = fitz.open(file_path)
        for page_num in range(min(len(doc), 3)):
            pix = doc[page_num].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            images.append(PIL.Image.open(io.BytesIO(pix.tobytes("png"))))
        doc.close()
    else:
        images.append(PIL.Image.open(file_path))
    return images


def _extract_approach_c(file_path: str) -> ExtractedDocument:
    """Approach C: Gemini 2.0 Flash vision. Free tier 1500 req/day. No EasyOCR needed."""
    import json
    image_parts = _file_to_image_parts(file_path)
    response = gemini_model.generate_content(
        image_parts + [_GEMINI_PROMPT],
        generation_config={"response_mime_type": "application/json"},
    )
    data = json.loads(response.text)
    return ExtractedDocument(**data)


# ═══════════════════════════════════════════════════════════════
# ACTIVE ENTRY POINT — swap the function call to change approach
# ═══════════════════════════════════════════════════════════════

def extract_document(file_path: str) -> ExtractedDocument:
    return _extract_approach_a(file_path)   # Approach A: EasyOCR + GPT-4o  ← ACTIVE
    # return _extract_approach_c(file_path) # Approach C: Gemini Flash       — pending key


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

import base64
from pathlib import Path

import fitz  # PyMuPDF
from openai import OpenAI

from config import settings
from models import ExtractedDocument, ExtractionResult

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _file_to_base64_images(file_path: str) -> list[str]:
    """Convert image or PDF file to list of base64-encoded PNG strings."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        with open(file_path, "rb") as f:
            return [base64.b64encode(f.read()).decode("utf-8")]

    if suffix == ".pdf":
        doc = fitz.open(file_path)
        images = []
        for page_num in range(min(len(doc), 3)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            images.append(base64.b64encode(pix.tobytes("png")).decode("utf-8"))
        doc.close()
        return images

    return []


def extract_document(file_path: str) -> ExtractedDocument:
    """Extract structured medical data from a single uploaded document."""
    images = _file_to_base64_images(file_path)
    if not images:
        raise ValueError(f"Unsupported or unreadable file: {file_path}")

    content: list[dict] = [
        {
            "type": "text",
            "text": (
                "Extract all medical information visible in this document.\n"
                "Set doc_type to one of: prescription, bill, diagnostic_report, pharmacy_bill.\n"
                "Set treatment_date as 'YYYY-MM-DD' if visible, otherwise null.\n"
                "Return null for any field that is not visible or not applicable — do not guess.\n"
                "Set extraction_confidence between 0.0 (unreadable) and 1.0 (perfectly clear and complete)."
            ),
        }
    ]

    for img_b64 in images:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_b64}",
                "detail": "high",
            },
        })

    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        response_format=ExtractedDocument,
        max_tokens=1500,
    )
    return response.choices[0].message.parsed


def merge_extractions(
    documents: list[ExtractedDocument],
    member_name: str,
    treatment_date: str,
    claim_amount: float,
) -> ExtractionResult:
    """Consolidate multiple extracted documents into a single ExtractionResult."""

    # Prefer prescription for diagnosis; fall back to any doc that has it
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

    # Date consistency — all doc dates must match submitted treatment date
    date_consistent = True
    for doc in documents:
        if doc.treatment_date and doc.treatment_date != treatment_date:
            date_consistent = False
            break

    # Patient name consistency — first name must appear somewhere in extracted name
    patient_name_consistent = True
    first_name = member_name.split()[0].lower()
    for doc in documents:
        if doc.patient_name and first_name not in doc.patient_name.lower():
            patient_name_consistent = False
            break

    # Required document check
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

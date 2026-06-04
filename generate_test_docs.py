#!/usr/bin/env python3
"""
Generate realistic medical document images for all 10 Plum test cases.

Each document contains exactly the data from test_cases.json so GPT-4o Vision
can extract the right fields and feed them into the real adjudication pipeline.

Run from project root:
    uv run generate_test_docs.py

Output:
    test_documents/
        TC001/  prescription.png  bill.png
        TC002/  prescription.png  bill.png
        TC003/  prescription.png  bill.png
        TC004/  bill.png                      ← no prescription (MISSING_DOCUMENTS test)
        TC005/  prescription.png  bill.png
        TC006/  prescription.png  bill.png
        TC007/  prescription.png  bill.pdf    ← PDF bill (tests PDF rendering)
        TC008/  prescription.png  bill.png
        TC009/  prescription.png  bill.png
        TC010/  prescription.png  bill.png    ← Apollo Hospitals header
"""

import json
import os
import random
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Paths ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent
TEST_CASES: list[dict] = []
for _fname in ("test_cases.json", "test_cases_new.json"):
    _p = ROOT / _fname
    if _p.exists():
        with open(_p) as _f:
            TEST_CASES.extend(json.load(_f)["test_cases"])

OUT = ROOT / "test_documents"

# ── Canvas constants ───────────────────────────────────────────────────────────

W, H = 900, 1250
WHITE  = (255, 255, 255)
BLACK  = (20,  20,  20)
GREY   = (100, 100, 100)
LGREY  = (240, 240, 240)
PLUM   = (88,  28,  135)
NAVY   = (15,  52,  96)
GREEN  = (0,   110, 60)
GOLD   = (180, 140, 0)
RED    = (180, 30,  30)

# ── Font loader ────────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        if bold else
        [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# ── Drawing helpers ────────────────────────────────────────────────────────────

def hline(d: ImageDraw.ImageDraw, y: int, x1=40, x2=860,
          color=(180, 180, 180), width=1):
    d.line([(x1, y), (x2, y)], fill=color, width=width)


def stamp(d: ImageDraw.ImageDraw, cx: int, cy: int,
          line1: str, line2: str = "", color=GREEN):
    r = 42
    d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=color, width=3)
    d.ellipse([cx-r+6, cy-r+6, cx+r-6, cy+r-6], outline=color, width=1)
    d.text((cx, cy - 7), line1, fill=color,
           font=_font(10, bold=True), anchor="mm")
    if line2:
        d.text((cx, cy + 8), line2, fill=color,
               font=_font(10, bold=True), anchor="mm")


def scribble_signature(d: ImageDraw.ImageDraw, x: int, y: int):
    """Draw a hand-wavy signature scribble."""
    pts = [
        (x,      y),
        (x+20,  y-14),
        (x+45,  y+8),
        (x+70,  y-10),
        (x+100, y+5),
        (x+130, y-8),
        (x+155, y),
    ]
    d.line(pts, fill=BLACK, width=2)
    d.line([(x, y+4), (x+155, y+4)], fill=(80, 80, 80), width=1)


def fmt_date(s: str) -> str:
    return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")


def fmt_inr(amount: float) -> str:
    return f"Rs. {int(amount):,}"


# ── Prescription generator ─────────────────────────────────────────────────────

def make_prescription(tc: dict, out_path: Path, as_pdf: bool = False):
    inp  = tc["input_data"]
    rx   = inp["documents"]["prescription"]
    date = inp["treatment_date"]

    img  = Image.new("RGB", (W, H), WHITE)
    d    = ImageDraw.Draw(img)

    # ── Header band ──────────────────────────────────────────
    d.rectangle([0, 0, W, 145], fill=PLUM)

    clinic = "City Medical Centre & Diagnostics"
    d.text((W//2, 18), clinic,
           fill=WHITE, font=_font(20, bold=True), anchor="mt")

    d.text((W//2, 55), rx["doctor_name"],
           fill=(210, 180, 255), font=_font(16, bold=True), anchor="mt")

    d.text((W//2, 82), f"Reg. No: {rx['doctor_reg']}",
           fill=(200, 200, 240), font=_font(13), anchor="mt")

    d.text((W//2, 108), "456 Wellness Road, Healthcare Nagar  |  Tel: 080-55566677",
           fill=(180, 180, 220), font=_font(11), anchor="mt")

    # ── Patient / date row ───────────────────────────────────
    y = 163
    d.rectangle([40, y, 860, y+52], fill=(248, 245, 255), outline=(180, 150, 220))
    d.text((55,  y+8),  f"Patient Name : {inp.get('dependent_name') or inp['member_name']}",
           fill=BLACK, font=_font(13, bold=True))
    d.text((530, y+8),  f"Date : {fmt_date(date)}",
           fill=BLACK, font=_font(13))
    d.text((55,  y+30), f"Member ID    : {inp['member_id']}",
           fill=GREY,  font=_font(12))
    d.text((530, y+30), "Age/Sex : —",
           fill=GREY,  font=_font(12))
    y += 68

    # ── Diagnosis box ────────────────────────────────────────
    d.rectangle([40, y, 860, y+44], fill=(255, 250, 220),
                outline=(200, 170, 0))
    d.text((55, y+6),   "DIAGNOSIS :", fill=GOLD, font=_font(12, bold=True))
    d.text((185, y+6),  rx.get("diagnosis", ""),
           fill=(60, 40, 0), font=_font(14, bold=True))
    y += 58

    # ── Rx section ────────────────────────────────────────────
    d.text((52, y), "℞", fill=PLUM, font=_font(28, bold=True))
    d.text((85, y+6), "(Prescription)", fill=GREY, font=_font(11))
    y += 42

    medicines  = rx.get("medicines_prescribed", [])
    procedures = rx.get("procedures", [])
    treatment  = rx.get("treatment")

    items = medicines + procedures + ([treatment] if treatment else [])

    for i, item in enumerate(items, 1):
        d.text((62,  y), f"{i}.", fill=PLUM, font=_font(13, bold=True))
        d.text((88,  y), item,    fill=BLACK, font=_font(13))
        if item in medicines:
            d.text((88, y+20), "    Sig: 1 tab TID × 5 days (after meals)",
                   fill=GREY, font=_font(11))
            y += 48
        else:
            y += 32

    # ── Tests / investigations ───────────────────────────────
    tests = rx.get("tests_prescribed", [])
    if tests:
        y += 6
        hline(d, y, color=(200, 200, 200))
        y += 14
        d.text((52, y), "Investigations Advised:", fill=BLACK,
               font=_font(13, bold=True))
        y += 28
        for t in tests:
            d.ellipse([62, y+4, 70, y+12], fill=PLUM)
            d.text((82, y), t, fill=BLACK, font=_font(13))
            y += 28

    # ── Notes ────────────────────────────────────────────────
    y += 10
    hline(d, y, color=(200, 200, 200))
    y += 16
    d.text((52, y), "Advice:", fill=BLACK, font=_font(12, bold=True))
    d.text((120, y), "Adequate rest. Plenty of fluids. Review after 5 days.",
           fill=GREY, font=_font(12))
    y += 24
    d.text((52, y), "Follow-up:", fill=BLACK, font=_font(12, bold=True))
    d.text((145, y), f"{fmt_date(date)} + 7 days",
           fill=GREY, font=_font(12))

    # ── Signature + stamp ────────────────────────────────────
    sig_y = H - 140
    hline(d, sig_y, color=(160, 160, 160), width=1)
    scribble_signature(d, 60, sig_y + 38)
    d.text((60, sig_y + 58), rx["doctor_name"],
           fill=GREY, font=_font(11))
    d.text((60, sig_y + 75), "Doctor's Signature",
           fill=(150, 150, 150), font=_font(10))
    stamp(d, 770, sig_y + 52, "CLINIC", "STAMP")

    # ── Footer ───────────────────────────────────────────────
    d.rectangle([0, H-32, W, H], fill=(230, 220, 245))
    d.text((W//2, H-18),
           "Valid for 30 days  |  Original Prescription  |  Not valid without doctor's stamp",
           fill=(100, 80, 130), font=_font(10), anchor="mm")

    _save(img, out_path, as_pdf)


# ── Bill generator ─────────────────────────────────────────────────────────────

BILL_LABEL = {
    "consultation_fee":        "Consultation Fee",
    "diagnostic_tests":        "Diagnostic Tests",
    "medicines":               "Medicines / Pharmacy",
    "root_canal":              "Root Canal Treatment",
    "teeth_whitening":         "Teeth Whitening Procedure",
    "mri_scan":                "MRI Lumbar Spine (with contrast)",
    "therapy_charges":         "Panchakarma Therapy Charges",
    "diet_plan":               "Diet Plan & Bariatric Consultation",
    "teleconsultation_fee":    "Teleconsultation Fee",
    "azithromycin":            "Azithromycin 500mg (Rx)",
    "paracetamol":             "Paracetamol 650mg (OTC)",
    "antacid":                 "Antacid Syrup (OTC)",
    "anomaly_scan":            "Anomaly Scan (Ultrasound)",
    "physiotherapy_sessions":  "Physiotherapy Sessions",
}


def make_bill(tc: dict, out_path: Path, as_pdf: bool = False):
    inp      = tc["input_data"]
    bill     = inp["documents"]["bill"]
    hospital = inp.get("hospital", "City Specialty Hospital")
    # TC019: bill has its own date (mismatch test) — use bill_date if present
    date     = inp.get("bill_date") or inp["treatment_date"]
    # TC013: claim is for a dependent — show dependent's name on bill
    patient_name = inp.get("dependent_name") or inp["member_name"]

    img = Image.new("RGB", (W, H), WHITE)
    d   = ImageDraw.Draw(img)

    # ── Header ───────────────────────────────────────────────
    d.rectangle([0, 0, W, 150], fill=NAVY)
    d.text((W//2, 16), hospital,
           fill=WHITE, font=_font(22, bold=True), anchor="mt")
    d.text((W//2, 54), "789 Health Avenue, Medical District, Bangalore - 560001",
           fill=(160, 190, 230), font=_font(12), anchor="mt")
    d.text((W//2, 78), "GST No: 29ZZZZZ9999Z1ZZ  |  Ph: 080-44455566  |  helpdesk@hospital.in",
           fill=(140, 170, 210), font=_font(11), anchor="mt")
    d.text((W//2, 106), "NABH Accredited  |  ISO 9001:2015 Certified",
           fill=(120, 155, 200), font=_font(10), anchor="mt")
    d.text((W//2, 124), "CASH RECEIPT / INVOICE",
           fill=(220, 220, 100), font=_font(13, bold=True), anchor="mt")

    # ── Bill meta ────────────────────────────────────────────
    y = 162
    bill_no = f"BL{random.randint(10000, 99999)}"
    d.rectangle([40, y, 860, y+54], fill=(245, 248, 255),
                outline=(180, 190, 220))
    d.text((55,  y+8),  f"Bill No   : {bill_no}",
           fill=BLACK, font=_font(12, bold=True))
    d.text((420, y+8),  f"Date       : {fmt_date(date)}",
           fill=BLACK, font=_font(12))
    d.text((55,  y+30), f"Patient    : {patient_name}",
           fill=BLACK, font=_font(12))
    d.text((420, y+30), f"Member ID  : {inp['member_id']}",
           fill=GREY,  font=_font(12))
    y += 66

    # ── Table header ─────────────────────────────────────────
    d.rectangle([40, y, 860, y+32], fill=NAVY)
    d.text((55,  y+8), "DESCRIPTION OF SERVICES",
           fill=WHITE, font=_font(12, bold=True))
    d.text((820, y+8), "AMOUNT",
           fill=WHITE, font=_font(12, bold=True), anchor="rt")
    y += 32

    # ── Line items ───────────────────────────────────────────
    subtotal  = 0
    shade     = [(255, 255, 255), (247, 248, 255)]
    row       = 0

    # TC018-style: physiotherapy_sessions + cost_per_session → render as session lines
    if inp.get("sessions_claimed") and bill.get("cost_per_session"):
        n_sessions = inp["sessions_claimed"]
        cost       = bill["cost_per_session"]
        synth_bill = {f"Session {i}": cost for i in range(1, n_sessions + 1)}
    else:
        synth_bill = bill

    for key, amount in synth_bill.items():
        if key in ("test_names", "total") or not isinstance(amount, (int, float)):
            continue
        label = BILL_LABEL.get(key, key.replace("_", " ").title())
        d.rectangle([40, y, 860, y+32], fill=shade[row % 2])
        hline(d, y+32, color=(220, 220, 230))
        d.text((55,  y+8), label,              fill=BLACK, font=_font(12))
        d.text((820, y+8), fmt_inr(amount),    fill=BLACK,
               font=_font(12), anchor="rt")
        subtotal += amount
        row += 1
        y    += 32

    # sub-items for test names (original bill only)
    test_names = bill.get("test_names", [])
    for t in test_names:
        d.rectangle([40, y, 860, y+26], fill=shade[row % 2])
        hline(d, y+26, color=(220, 220, 230))
        d.text((75,  y+5), f"    ↳ {t}", fill=GREY, font=_font(11))
        row += 1
        y   += 26

    y += 8
    hline(d, y, color=(120, 120, 180), width=2)
    y += 6

    # ── Totals ───────────────────────────────────────────────
    d.rectangle([40, y, 860, y+30], fill=(240, 242, 255))
    d.text((55,  y+7), "Sub Total",     fill=GREY, font=_font(12))
    d.text((820, y+7), fmt_inr(subtotal),
           fill=GREY, font=_font(12), anchor="rt")
    y += 30

    gst = round(subtotal * 0.05)
    d.text((55,  y+7), "GST @ 5%",      fill=GREY, font=_font(12))
    d.text((820, y+7), fmt_inr(gst),
           fill=GREY, font=_font(12), anchor="rt")
    y += 30

    hline(d, y, color=(80, 80, 180), width=2)
    y += 6

    grand = subtotal + gst
    d.rectangle([40, y, 860, y+40], fill=NAVY)
    d.text((55,  y+10), "TOTAL AMOUNT DUE",
           fill=WHITE, font=_font(14, bold=True))
    d.text((820, y+10), fmt_inr(grand),
           fill=(220, 220, 100), font=_font(14, bold=True), anchor="rt")
    y += 52

    # ── Amount in words ──────────────────────────────────────
    d.text((55, y), f"Amount (before GST) : Rupees {subtotal:,} only",
           fill=GREY, font=_font(11))
    y += 22
    d.text((55, y), "Mode of Payment : Cash / Card / UPI",
           fill=GREY, font=_font(11))

    # ── Signature + stamp ────────────────────────────────────
    sig_y = H - 145
    hline(d, sig_y, color=(160, 160, 160))
    scribble_signature(d, 60, sig_y + 38)
    d.text((60,  sig_y + 60), "Authorised Signatory",
           fill=GREY, font=_font(11))
    stamp(d, 770, sig_y + 55, "HOSPITAL", "STAMP", color=NAVY)

    # ── Footer ───────────────────────────────────────────────
    d.rectangle([0, H-35, W, H], fill=NAVY)
    d.text((W//2, H-20),
           "Original Bill  |  Goods once sold will not be taken back  |  Subject to local jurisdiction",
           fill=(150, 180, 220), font=_font(10), anchor="mm")

    _save(img, out_path, as_pdf)


# ── Save helper ────────────────────────────────────────────────────────────────

def _save(img: Image.Image, path: Path, as_pdf: bool):
    path.parent.mkdir(parents=True, exist_ok=True)
    if as_pdf:
        img.save(str(path), "PDF", resolution=150)
    else:
        img.save(str(path), "PNG")
    print(f"  OK  {path.relative_to(ROOT)}")


# ── Per-case document plan ─────────────────────────────────────────────────────

def generate_all():
    print(f"\n=== Generating test documents ({len(TEST_CASES)} cases) ===\n")

    for tc in TEST_CASES:
        cid  = tc["case_id"]
        docs = tc["input_data"]["documents"]
        case_dir = OUT / cid
        print(f"[{cid}] {tc['case_name']}")

        has_rx   = "prescription" in docs
        has_bill = "bill" in docs

        if has_rx:
            # TC007 bill is a PDF to exercise the PDF rendering path
            make_prescription(tc, case_dir / "prescription.png")

        if has_bill:
            if cid == "TC007":
                make_bill(tc, case_dir / "bill.pdf", as_pdf=True)
            else:
                make_bill(tc, case_dir / "bill.png")

        # TC019: generate a second bill with the later bill_date clearly shown
        if cid == "TC019":
            print(f"         note: bill uses bill_date={tc['input_data'].get('bill_date')} (mismatch test)")

        # TC004 intentionally has no prescription — only bill is generated above

    print(f"\nDone - documents saved to: {OUT}\n")
    print("How to use:")
    print("  1. Start the backend:  cd backend && uv run uvicorn main:app --reload")
    print("  2. Open http://localhost:3000/claims/new")
    print("  3. For each test case, upload the files from test_documents/TCxxx/")
    print("  4. Fill in the claim form using the data from test_cases.json")
    print()
    print("Form values per case:")
    print("-" * 60)
    for tc in TEST_CASES:
        inp = tc["input_data"]
        print(f"\n{tc['case_id']} — {tc['case_name']}")
        print(f"  Member ID        : {inp['member_id']}")
        print(f"  Member Name      : {inp['member_name']}")
        print(f"  Policy Join      : {inp.get('member_join_date', '2024-01-01')}")
        print(f"  Treatment Date   : {inp['treatment_date']}")
        print(f"  Claim Amount     : Rs. {inp['claim_amount']}")
        print(f"  Hospital         : {inp.get('hospital', '(leave blank)')}")
        print(f"  Cashless         : {inp.get('cashless_request', False)}")
        print(f"  Same-day claims  : {inp.get('previous_claims_same_day', 0)}")
        print(f"  YTD claimed      : {inp.get('annual_limit_used', 0)}")
        if inp.get("dependent_name"):
            print(f"  Dependent Name   : {inp['dependent_name']} (age {inp.get('dependent_age')}, {inp.get('dependent_relation')})")
        if inp.get("previous_claim_id"):
            print(f"  Duplicate of     : {inp['previous_claim_id']}")
        if inp.get("sessions_claimed"):
            print(f"  Sessions Claimed : {inp['sessions_claimed']} (cap: {inp.get('annual_session_cap')})")
        if inp.get("bill_date"):
            print(f"  Bill Date        : {inp['bill_date']} (differs from treatment date — mismatch test)")
        print(f"  Expected         : {tc['expected_output']['decision']}")
        docs = list(tc["input_data"]["documents"].keys())
        note = " (TC007 bill is .pdf)" if tc["case_id"] == "TC007" else ""
        print(f"  Upload files     : {', '.join(f'{d}.png' for d in docs)}{note}")


if __name__ == "__main__":
    generate_all()

"""
Full pipeline test — GPT-4o Vision extraction + adjudication.

Uses the generated document images in test_documents/ (run generate_test_docs.py first).
Submits each test case via POST /claims (real multipart file upload) and compares
the AI decision against the expected output in test_cases.json.

Usage:
    1. uv run generate_test_docs.py          (only needed once)
    2. cd backend && uv run uvicorn main:app --reload
    3. uv run test_full_pipeline.py

Each case costs ~2 OpenAI API calls (extraction + adjudication) and takes 15-40s.
Full suite: ~5-7 minutes.
"""

import json
import sys
import time
from pathlib import Path

import requests

BASE   = "http://localhost:8000"
ROOT   = Path(__file__).parent
DOCS   = ROOT / "test_documents"
CASES: list[dict] = []
for _fname in ("test_cases.json", "test_cases_new.json"):
    _p = ROOT / _fname
    if _p.exists():
        CASES.extend(json.loads(_p.read_text())["test_cases"])

# ── Console colours (skip on Windows if no ANSI support) ─────────────────────

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m"

PASS = _c("92", "PASS")
FAIL = _c("91", "FAIL")
SKIP = _c("93", "SKIP")
INFO = _c("94", "INFO")


def banner(text: str):
    print(f"\n{'=' * 64}")
    print(f"  {text}")
    print(f"{'=' * 64}")


def log(tag: str, msg: str):
    print(f"  [{tag}] {msg}")


# ── Form data per test case (mirrors test_cases.json exactly) ─────────────────

def _form_data(tc: dict) -> dict:
    inp = tc["input_data"]
    return {
        "member_id":                inp["member_id"],
        "member_name":              inp["member_name"],
        "member_join_date":         inp.get("member_join_date", "2024-01-01"),
        "treatment_date":           inp["treatment_date"],
        "claim_amount":             float(inp["claim_amount"]),
        "hospital_name":            inp.get("hospital"),
        "cashless_request":         inp.get("cashless_request", False),
        "ytd_claimed_amount":       float(inp.get("annual_limit_used", 0.0)),
        "annual_limit_total":       float(inp["annual_limit_total"]) if inp.get("annual_limit_total") else None,
        "previous_claims_same_day": inp.get("previous_claims_same_day", 0),
        "dependent_name":           inp.get("dependent_name"),
        "dependent_age":            inp.get("dependent_age"),
        "dependent_relation":       inp.get("dependent_relation"),
        "is_duplicate_claim":       bool(inp.get("previous_claim_id")),
        "previous_claim_id":        inp.get("previous_claim_id"),
        "sessions_claimed":         inp.get("sessions_claimed"),
        "annual_session_cap":       inp.get("annual_session_cap"),
    }


# ── Amount tolerance check ────────────────────────────────────────────────────

def _amount_ok(actual: float, expected: float, pct: float = 0.20) -> bool:
    return abs(actual - expected) <= expected * pct


# ── Single case runner ────────────────────────────────────────────────────────

def run_case(tc: dict) -> dict:
    cid      = tc["case_id"]
    name     = tc["case_name"]
    expected = tc["expected_output"]["decision"]
    exp_amt  = tc["expected_output"].get("approved_amount")
    case_dir = DOCS / cid

    print(f"\n  [{cid}] {name}")
    print(f"         expected: {expected}" + (f"  amount: Rs.{exp_amt}" if exp_amt else ""))

    # ── Locate files ─────────────────────────────────────────
    if not case_dir.exists():
        log(SKIP, f"test_documents/{cid}/ not found — run generate_test_docs.py first")
        return {"case_id": cid, "name": name, "status": "SKIP", "expected": expected}

    files_found = sorted(case_dir.iterdir())
    if not files_found:
        log(SKIP, "No files in directory")
        return {"case_id": cid, "name": name, "status": "SKIP", "expected": expected}

    # ── Build multipart payload ───────────────────────────────
    open_handles = []
    multipart    = []
    try:
        for fp in files_found:
            if fp.suffix.lower() not in {".png", ".jpg", ".jpeg", ".pdf"}:
                continue
            mime = "application/pdf" if fp.suffix.lower() == ".pdf" else "image/png"
            fh   = open(fp, "rb")
            open_handles.append(fh)
            multipart.append(("files", (fp.name, fh, mime)))
            log(INFO, f"  uploading: {fp.name}")

        if not multipart:
            log(SKIP, "No uploadable files found")
            return {"case_id": cid, "name": name, "status": "SKIP", "expected": expected}

        form_data = _form_data(tc)
        log(INFO, f"  form: member={form_data['member_name']}  amount=Rs.{form_data['claim_amount']}"
                  f"  date={form_data['treatment_date']}"
                  + (f"  hospital={form_data['hospital_name']}" if form_data["hospital_name"] else "")
                  + (f"  cashless={form_data['cashless_request']}" if form_data["cashless_request"] else "")
                  + (f"  same_day={form_data['previous_claims_same_day']}" if form_data["previous_claims_same_day"] else ""))

        # ── POST /claims ──────────────────────────────────────
        t0 = time.time()
        resp = requests.post(
            f"{BASE}/claims",
            files=multipart,
            data={"data": json.dumps(form_data)},
            timeout=180,
        )
        elapsed = time.time() - t0

    finally:
        for fh in open_handles:
            fh.close()

    # ── Parse response ────────────────────────────────────────
    if resp.status_code != 200:
        log(FAIL, f"HTTP {resp.status_code}: {resp.text[:300]}")
        return {
            "case_id": cid, "name": name, "status": "ERROR",
            "expected": expected, "http_status": resp.status_code,
        }

    data    = resp.json()
    dec     = data["decision"]
    actual  = dec["decision"]
    amount  = dec["approved_amount"]
    conf    = dec["confidence_score"]
    diag    = data["extracted_data"]["merged_diagnosis"]
    missing = data["extracted_data"]["missing_docs"]
    reasons = dec.get("rejection_reasons", [])

    log(INFO, f"  extracted diagnosis : {diag}")
    if missing:
        log(INFO, f"  missing docs        : {missing}")
    log(INFO, f"  decision            : {actual}  amount=Rs.{amount}  conf={conf:.2f}  ({elapsed:.1f}s)")
    if reasons:
        log(INFO, f"  rejection reasons   : {reasons}")
    log(INFO, f"  notes               : {dec['notes'][:120]}")

    # ── Pass / fail ───────────────────────────────────────────
    decision_ok = actual == expected
    amount_ok   = True
    if exp_amt is not None and decision_ok:
        amount_ok = _amount_ok(amount, exp_amt)

    overall = decision_ok and amount_ok

    tag = PASS if overall else FAIL
    log(tag, f"  decision {'matches' if decision_ok else 'MISMATCH'} "
             f"(expected {expected}, got {actual})"
             + (f"  |  amount {'OK' if amount_ok else 'OUT OF RANGE'} "
                f"(expected Rs.{exp_amt}, got Rs.{amount})" if exp_amt else ""))

    return {
        "case_id":     cid,
        "name":        name,
        "status":      "PASS" if overall else "FAIL",
        "expected":    expected,
        "actual":      actual,
        "exp_amount":  exp_amt,
        "act_amount":  amount,
        "confidence":  conf,
        "diagnosis":   diag,
        "elapsed":     round(elapsed, 1),
        "claim_id":    data["claim_id"],
    }


# ── Summary printer ───────────────────────────────────────────────────────────

def print_summary(results: list[dict]):
    banner("RESULTS SUMMARY")

    passed  = sum(1 for r in results if r["status"] == "PASS")
    failed  = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] in ("SKIP", "ERROR"))
    total   = len(results)

    print(f"\n  {'Case':<8} {'Name':<38} {'Expected':<14} {'Got':<14} {'Conf':>6}  {'Time':>6}  Status")
    print(f"  {'-'*8} {'-'*38} {'-'*14} {'-'*14} {'-'*6}  {'-'*6}  {'-'*6}")

    for r in results:
        tag = PASS if r["status"] == "PASS" else (SKIP if r["status"] in ("SKIP","ERROR") else FAIL)
        got  = r.get("actual", r["status"])
        conf = f"{r['confidence']*100:.0f}%" if r.get("confidence") else "—"
        secs = f"{r['elapsed']}s" if r.get("elapsed") else "—"
        print(f"  {r['case_id']:<8} {r['name'][:38]:<38} {r['expected']:<14} {got:<14} {conf:>6}  {secs:>6}  {tag}")

    print(f"\n  Passed : {passed}/{total}")
    print(f"  Failed : {failed}/{total}")
    if skipped:
        print(f"  Skipped: {skipped}/{total}")

    total_time = sum(r.get("elapsed", 0) for r in results)
    print(f"  Total elapsed: {total_time:.1f}s\n")

    if failed > 0:
        print("  Failed cases:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"    {r['case_id']}: expected {r['expected']}, got {r.get('actual', '?')}")
        print()

    return passed, failed


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", help="Comma-separated case IDs to run, e.g. TC015,TC016", default="")
    args = parser.parse_args()

    filter_ids = {c.strip().upper() for c in args.cases.split(",") if c.strip()}
    cases_to_run = [tc for tc in CASES if not filter_ids or tc["case_id"] in filter_ids]

    banner("PLUM FULL PIPELINE TEST  (GPT-4o Vision + Adjudication)")
    print(f"\n  Backend : {BASE}")
    print(f"  Docs    : {DOCS}")
    if filter_ids:
        print(f"  Cases   : {len(cases_to_run)} selected — {', '.join(filter_ids)}")
    else:
        print(f"  Cases   : {len(cases_to_run)}  (TC001–TC010 original + TC011–TC020 extended)")
    print(f"\n  NOTE: Each case takes 15-40s (2 GPT-4o calls).")
    print(f"  TC014 expected MANUAL_REVIEW (no MCI registry — known limitation).")

    # Preflight check
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        assert r.status_code == 200 and r.json()["status"] == "ok"
        log(INFO, "Backend health check passed")
    except Exception as e:
        print(f"\n  ERROR: Backend not reachable at {BASE}")
        print(f"  Make sure to run: cd backend && uv run uvicorn main:app --reload")
        sys.exit(1)

    if not DOCS.exists():
        print(f"\n  ERROR: test_documents/ folder not found.")
        print(f"  Run: uv run generate_test_docs.py")
        sys.exit(1)

    # Run selected cases
    results = []
    for tc in cases_to_run:
        result = run_case(tc)
        results.append(result)
        if result["status"] not in ("SKIP", "ERROR"):
            time.sleep(2)

    passed, failed = print_summary(results)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

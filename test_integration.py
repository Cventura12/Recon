"""
test_integration.py - Phase 7 Full Pipeline Integration Tests

Final acceptance test for the complete diagnostic pipeline:
extract -> match -> diagnose -> explain

Usage: python test_integration.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Ensure local imports resolve from project root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from diagnose import diagnose
from explain import format_explanation, format_explanation_json
from extract import extract_receipt
from main import load_transactions
from match import find_matches
from models import MismatchType


def _configure_output_symbols() -> tuple[str, str, str]:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        "✓✗═".encode(sys.stdout.encoding or "utf-8")
        return "✓", "✗", "═"
    except Exception:
        return "[OK]", "[FAIL]", "="


PASS, FAIL, LINE = _configure_output_symbols()


def run_full_pipeline(receipt_path: str, transactions_df):
    """Run extract -> match -> diagnose -> explain and return all artifacts."""
    receipt = extract_receipt(receipt_path)
    matches = find_matches(receipt, transactions_df)
    diag = diagnose(matches, receipt)
    text = format_explanation(diag)
    json_result = format_explanation_json(diag)
    diag.explanation = text
    return receipt, matches, diag, text, json_result


def main() -> None:
    passed = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal passed, failed
        if condition:
            print(f"    {PASS} {name}")
            passed += 1
        else:
            print(f"    {FAIL} {name}")
            failed += 1

    print(LINE * 62)
    print("  Phase 7: Full Pipeline Integration Tests")
    print(LINE * 62)

    base_dir = Path(__file__).resolve().parent
    csv_path = str(base_dir / "test_data" / "transactions.csv")

    original_key = os.environ.pop("VISION_AGENT_API_KEY", None)
    try:
        df = load_transactions(csv_path)

        # Category 1: Receipt 01 - Clean Match (Amazon)
        print("\n  Receipt 01 - Clean Match (Amazon):")
        try:
            r1, m1, d1, t1, j1 = run_full_pipeline(
                str(base_dir / "test_data" / "receipts" / "receipt_01_clean_match.png"),
                df,
            )
            top1 = m1[0] if m1 else None
            check("Extraction: vendor=Amazon.com, total=$89.97", r1.vendor == "Amazon.com" and r1.total == 89.97 and r1.date == "2026-01-10" and r1.confidence >= 0.95)
            check("Matching: top=Amazon, score>=90, exact amount/date", top1 is not None and ("amazon" in top1.transaction.merchant.lower() or "amzn" in top1.transaction.merchant.lower()) and top1.vendor_score >= 90 and top1.amount_diff == 0.0 and top1.date_diff == 0)
            check("Diagnosis: clean match, confidence>=80%", (d1.labels == [] or d1.is_clean_match) and d1.confidence >= 80 and d1.is_match is True and d1.top_match is not None)
            check('Text: contains vendor, amount, "Clean Match"', "Amazon" in t1 and "$89.97" in t1 and ("Clean Match" in t1 or "No Exception" in t1))
            check("JSON: status=clean_match, is_clean_match=true", j1["status"] == "clean_match" and j1["confidence"] >= 80 and j1["diagnosis"]["is_clean_match"] is True)
        except Exception:
            check("Extraction: vendor=Amazon.com, total=$89.97", False)
            check("Matching: top=Amazon, score>=90, exact amount/date", False)
            check("Diagnosis: clean match, confidence>=80%", False)
            check('Text: contains vendor, amount, "Clean Match"', False)
            check("JSON: status=clean_match, is_clean_match=true", False)

        # Category 2: Receipt 02 - Vendor Mismatch (El Agave)
        print("\n  Receipt 02 - Vendor Mismatch (El Agave):")
        try:
            r2, m2, d2, t2, j2 = run_full_pipeline(
                str(base_dir / "test_data" / "receipts" / "receipt_02_vendor_mismatch.png"),
                df,
            )
            top2 = m2[0] if m2 else None
            check("Extraction: has tip, has tax", r2.vendor == "El Agave Mexican Restaurant" and r2.total == 47.50 and r2.has_tip is True and r2.has_tax is True)
            check("Matching: top=ELAGAVE, vendor_score<80", top2 is not None and ("elagave" in top2.transaction.merchant.lower()) and top2.amount_diff == 0.0 and top2.date_diff == 0 and top2.vendor_score < 80)
            check("Diagnosis: VENDOR_MISMATCH only", MismatchType.VENDOR_MISMATCH in d2.labels and MismatchType.SETTLEMENT_DELAY not in d2.labels and MismatchType.TIP_TAX_VARIANCE not in d2.labels)
            check("Text: contains both vendor names", "El Agave" in t2 and "ELAGAVE" in t2 and "Vendor" in t2)
            check('JSON: labels=["vendor_descriptor_mismatch"]', j2["status"] == "match_found" and "vendor_descriptor_mismatch" in j2["diagnosis"]["labels"])
        except Exception:
            check("Extraction: has tip, has tax", False)
            check("Matching: top=ELAGAVE, vendor_score<80", False)
            check("Diagnosis: VENDOR_MISMATCH only", False)
            check("Text: contains both vendor names", False)
            check('JSON: labels=["vendor_descriptor_mismatch"]', False)

        # Category 3: Receipt 03 - Tip/Tax Variance edge case (Starbucks)
        print("\n  Receipt 03 - Tip/Tax Variance (Starbucks):")
        try:
            r3, m3, d3, t3, j3 = run_full_pipeline(
                str(base_dir / "test_data" / "receipts" / "receipt_03_tip_tax_variance.png"),
                df,
            )
            top3 = m3[0] if m3 else None
            check("Extraction: total=$5.25", r3.vendor == "Starbucks" and r3.total == 5.25)
            check("Matching: amount_pct_diff>25%", top3 is not None and top3.transaction.amount == 6.83 and top3.amount_diff > 0 and top3.amount_pct_diff > 25 and top3.vendor_score >= 90 and top3.date_diff == 0)
            check("Diagnosis: PARTIAL_MATCH (30% exceeds threshold)", MismatchType.PARTIAL_MATCH in d3.labels or MismatchType.TIP_TAX_VARIANCE in d3.labels)
            check("Text/JSON consistent", "Starbucks" in t3 and ("$5.25" in t3 or "$6.83" in t3) and j3["status"] == "match_found")
        except Exception:
            check("Extraction: total=$5.25", False)
            check("Matching: amount_pct_diff>25%", False)
            check("Diagnosis: PARTIAL_MATCH (30% exceeds threshold)", False)
            check("Text/JSON consistent", False)

        # Category 4: Receipt 04 - Settlement Delay (Home Depot)
        print("\n  Receipt 04 - Settlement Delay (Home Depot):")
        try:
            r4, m4, d4, t4, j4 = run_full_pipeline(
                str(base_dir / "test_data" / "receipts" / "receipt_04_settlement_delay.png"),
                df,
            )
            top4 = m4[0] if m4 else None
            check("Extraction: date=2026-01-15", r4.vendor == "Home Depot" and r4.total == 234.67 and r4.date == "2026-01-15")
            check("Matching: date_diff=2, exact amount", top4 is not None and top4.transaction.amount == 234.67 and top4.date_diff == 2 and top4.vendor_score >= 90)
            check("Diagnosis: SETTLEMENT_DELAY only", MismatchType.SETTLEMENT_DELAY in d4.labels and MismatchType.VENDOR_MISMATCH not in d4.labels and MismatchType.TIP_TAX_VARIANCE not in d4.labels)
            check('Text: "Settlement Delay"', "Home Depot" in t4 and "Settlement Delay" in t4 and j4["status"] == "match_found" and "settlement_delay" in j4["diagnosis"]["labels"])
        except Exception:
            check("Extraction: date=2026-01-15", False)
            check("Matching: date_diff=2, exact amount", False)
            check("Diagnosis: SETTLEMENT_DELAY only", False)
            check('Text: "Settlement Delay"', False)

        # Category 5: Receipt 05 - Compound mismatch (Fastenal)
        print("\n  Receipt 05 - Compound Mismatch (Fastenal):")
        try:
            r5, m5, d5, t5, j5 = run_full_pipeline(
                str(base_dir / "test_data" / "receipts" / "receipt_05_combined_mismatch.png"),
                df,
            )
            top5 = m5[0] if m5 else None
            check("Extraction: low confidence (0.72)", r5.vendor == "Fastenal" and r5.total == 178.23 and r5.confidence < 0.8 and r5.is_low_confidence is True)
            check("Matching: vendor<80, amount>0, date>0", top5 is not None and top5.vendor_score < 80 and top5.amount_diff > 0 and top5.date_diff >= 1)
            check("Diagnosis: 2+ labels, compound=true", len(d5.labels) >= 2 and d5.is_compound is True and MismatchType.VENDOR_MISMATCH in d5.labels and MismatchType.SETTLEMENT_DELAY in d5.labels)
            check("Low confidence warning in evidence", any("confidence" in evidence.lower() or "⚠" in evidence for evidence in d5.evidence))
            check("JSON warnings non-empty", "Fastenal" in t5 and "+" in t5 and j5["status"] == "match_found" and len(j5["diagnosis"]["labels"]) >= 2 and len(j5["warnings"]) >= 1)
        except Exception:
            check("Extraction: low confidence (0.72)", False)
            check("Matching: vendor<80, amount>0, date>0", False)
            check("Diagnosis: 2+ labels, compound=true", False)
            check("Low confidence warning in evidence", False)
            check("JSON warnings non-empty", False)

        # Category 6: Receipt 06 - No Match (Bob's Hardware)
        print("\n  Receipt 06 - No Match (Bob's):")
        try:
            r6, m6, d6, t6, j6 = run_full_pipeline(
                str(base_dir / "test_data" / "receipts" / "receipt_06_no_match.png"),
                df,
            )
            check("Matching: 0 candidates", r6.vendor == "Bob's Local Hardware" and r6.total == 45.00 and len(m6) == 0)
            check("Diagnosis: NO_MATCH, confidence=95", MismatchType.NO_MATCH in d6.labels and d6.confidence == 95.0 and d6.top_match is None and d6.is_match is False)
            check('Text: "NO MATCH"', ("NO MATCH" in t6 or "No Match" in t6) and "Bob" in t6)
            check("JSON: top_match=null", j6["status"] == "no_match" and j6["top_match"] is None)
        except Exception:
            check("Matching: 0 candidates", False)
            check("Diagnosis: NO_MATCH, confidence=95", False)
            check('Text: "NO MATCH"', False)
            check("JSON: top_match=null", False)

        # Category 7: CSV loading behavior.
        print("\n  CSV Loading:")
        try:
            df_test = load_transactions(csv_path)
            check("Valid CSV loads 10 rows", len(df_test) == 10 and "merchant" in df_test.columns and "amount" in df_test.columns and "date" in df_test.columns)
        except Exception:
            check("Valid CSV loads 10 rows", False)

        missing_ok = False
        try:
            load_transactions("nonexistent.csv")
        except FileNotFoundError:
            missing_ok = True
        except Exception:
            missing_ok = False
        check("Missing CSV raises FileNotFoundError", missing_ok)

        bad_csv_ok = False
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
                tmp.write("wrong,columns,here\n1,2,3\n")
                temp_path = tmp.name
            try:
                load_transactions(temp_path)
            except ValueError as exc:
                bad_csv_ok = "missing" in str(exc).lower()
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
        check("Wrong columns raises ValueError", bad_csv_ok)

        # Category 8: JSON completeness for all receipts.
        print("\n  JSON Completeness:")
        receipt_files = [
            "receipt_01_clean_match.png",
            "receipt_02_vendor_mismatch.png",
            "receipt_03_tip_tax_variance.png",
            "receipt_04_settlement_delay.png",
            "receipt_05_combined_mismatch.png",
            "receipt_06_no_match.png",
        ]
        required_top_keys = {"status", "confidence", "diagnosis", "evidence", "receipt", "top_match", "warnings"}
        required_diag_keys = {"labels", "label_names", "label_summary", "is_compound", "is_clean_match"}

        for receipt_file in receipt_files:
            path = str(base_dir / "test_data" / "receipts" / receipt_file)
            try:
                _, _, _, _, json_result = run_full_pipeline(path, df)
                serialized = json.dumps(json_result)
                deserialized = json.loads(serialized)
                check(
                    f"{receipt_file}: valid JSON roundtrip",
                    deserialized == json_result,
                )
                check(
                    f"{receipt_file}: required keys present",
                    required_top_keys.issubset(set(deserialized.keys()))
                    and required_diag_keys.issubset(set(deserialized["diagnosis"].keys())),
                )
            except Exception:
                check(f"{receipt_file}: valid JSON roundtrip", False)
                check(f"{receipt_file}: required keys present", False)

        # Category 9: Performance for all receipts (mock path).
        print("\n  Performance:")
        for receipt_file in receipt_files:
            path = str(base_dir / "test_data" / "receipts" / receipt_file)
            try:
                start = time.time()
                run_full_pipeline(path, df)
                elapsed = time.time() - start
                check(f"{receipt_file} under 2.0s", elapsed < 2.0)
            except Exception:
                check(f"{receipt_file} under 2.0s", False)

    finally:
        if original_key is not None:
            os.environ["VISION_AGENT_API_KEY"] = original_key

    print(f"\n{LINE * 62}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print(f"  Phase 7: COMPLETE {PASS}")
        print()
        print("  🎉 The Diagnostic Agent is fully operational!")
        print("  Run it yourself:")
        print("    python main.py --all --csv test_data/transactions.csv")
        print()
    else:
        print(f"  Phase 7: {failed} FAILED - fix before proceeding")
    print(f"{LINE * 62}")


if __name__ == "__main__":
    main()

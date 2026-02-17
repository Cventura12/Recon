"""
test_diagnose.py - Phase 5 Diagnosis Engine Tests

End-to-end checks for:
- deterministic archetype classification
- compound label behavior
- threshold boundaries
- evidence quality/properties
- integration across extract -> match -> diagnose

Usage: python test_diagnose.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure local imports resolve from project root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from diagnose import diagnose
from extract import extract_receipt
from match import find_matches
from models import MatchCandidate, MismatchType, ReceiptData, Transaction


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


def make_candidate(
    vendor_score: float = 90.0,
    amount_diff: float = 0.0,
    amount_pct_diff: float = 0.0,
    date_diff: int = 0,
    overall_confidence: float = 85.0,
    merchant: str = "Test Merchant",
    amount: float = 100.0,
    date: str = "2026-01-15",
) -> MatchCandidate:
    return MatchCandidate(
        transaction=Transaction(
            merchant=merchant,
            amount=amount,
            date=date,
        ),
        vendor_score=vendor_score,
        amount_diff=amount_diff,
        amount_pct_diff=amount_pct_diff,
        date_diff=date_diff,
        overall_confidence=overall_confidence,
        evidence=[
            f"Vendor score: {vendor_score}",
            f"Amount diff: ${amount_diff:.2f} ({amount_pct_diff:.1f}%)",
            f"Date diff: {date_diff} days",
        ],
    )


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
    print("  Phase 5: Diagnosis Engine Tests")
    print(LINE * 62)

    # Category 1: Unit tests - single archetype behaviors.
    print("\n  Unit - Individual Archetypes:")
    diag_vendor = diagnose(
        [make_candidate(vendor_score=55.0, amount_diff=0, amount_pct_diff=0, date_diff=0, overall_confidence=75.0)]
    )
    check(
        "Pure VENDOR_MISMATCH",
        MismatchType.VENDOR_MISMATCH in diag_vendor.labels
        and MismatchType.SETTLEMENT_DELAY not in diag_vendor.labels
        and MismatchType.TIP_TAX_VARIANCE not in diag_vendor.labels
        and len(diag_vendor.labels) == 1,
    )

    diag_delay = diagnose(
        [make_candidate(vendor_score=95.0, amount_diff=0, amount_pct_diff=0, date_diff=2, overall_confidence=88.0)]
    )
    check(
        "Pure SETTLEMENT_DELAY",
        MismatchType.SETTLEMENT_DELAY in diag_delay.labels
        and MismatchType.VENDOR_MISMATCH not in diag_delay.labels
        and len(diag_delay.labels) == 1,
    )

    diag_tip_tax = diagnose(
        [make_candidate(vendor_score=100.0, amount_diff=5.0, amount_pct_diff=10.0, date_diff=0, overall_confidence=82.0)]
    )
    check(
        "Pure TIP_TAX_VARIANCE",
        MismatchType.TIP_TAX_VARIANCE in diag_tip_tax.labels and len(diag_tip_tax.labels) == 1,
    )

    diag_none = diagnose([])
    check(
        "NO_MATCH (empty list)",
        MismatchType.NO_MATCH in diag_none.labels and diag_none.confidence == 95.0 and diag_none.top_match is None,
    )

    diag_clean = diagnose(
        [make_candidate(vendor_score=100.0, amount_diff=0, amount_pct_diff=0, date_diff=0, overall_confidence=92.0)]
    )
    check(
        "CLEAN MATCH (all align)",
        diag_clean.labels == [] and diag_clean.is_clean_match is True and diag_clean.confidence == 92.0,
    )

    diag_partial = diagnose(
        [make_candidate(vendor_score=100.0, amount_diff=30.0, amount_pct_diff=30.0, date_diff=0, overall_confidence=65.0)]
    )
    check(
        "PARTIAL_MATCH (low confidence)",
        MismatchType.PARTIAL_MATCH in diag_partial.labels and len(diag_partial.labels) == 1,
    )

    # Category 2: Compound labels.
    print("\n  Unit - Compound Labels:")
    d_vendor_delay = diagnose(
        [make_candidate(vendor_score=55.0, amount_diff=0, amount_pct_diff=0, date_diff=2, overall_confidence=70.0)]
    )
    check(
        "VENDOR + DELAY (2 labels)",
        MismatchType.VENDOR_MISMATCH in d_vendor_delay.labels
        and MismatchType.SETTLEMENT_DELAY in d_vendor_delay.labels
        and len(d_vendor_delay.labels) == 2
        and d_vendor_delay.is_compound is True,
    )

    d_vendor_tip = diagnose(
        [make_candidate(vendor_score=60.0, amount_diff=5.0, amount_pct_diff=8.0, date_diff=0, overall_confidence=72.0)]
    )
    check(
        "VENDOR + TIP_TAX (2 labels)",
        MismatchType.VENDOR_MISMATCH in d_vendor_tip.labels
        and MismatchType.TIP_TAX_VARIANCE in d_vendor_tip.labels
        and len(d_vendor_tip.labels) == 2,
    )

    d_all_three = diagnose(
        [make_candidate(vendor_score=59.0, amount_diff=4.36, amount_pct_diff=2.4, date_diff=2, overall_confidence=70.0)]
    )
    check(
        "ALL THREE (3 labels)",
        MismatchType.VENDOR_MISMATCH in d_all_three.labels
        and MismatchType.SETTLEMENT_DELAY in d_all_three.labels
        and MismatchType.TIP_TAX_VARIANCE in d_all_three.labels
        and len(d_all_three.labels) == 3
        and d_all_three.is_compound is True,
    )

    # Category 3: Threshold boundaries.
    print("\n  Threshold Boundaries:")
    check(
        "Vendor at 80 -> no mismatch",
        MismatchType.VENDOR_MISMATCH
        not in diagnose([make_candidate(vendor_score=80.0, amount_pct_diff=0, date_diff=0, overall_confidence=85.0)]).labels,
    )
    check(
        "Vendor at 79.9 -> mismatch",
        MismatchType.VENDOR_MISMATCH
        in diagnose([make_candidate(vendor_score=79.9, amount_pct_diff=0, date_diff=0, overall_confidence=84.0)]).labels,
    )
    check(
        "Date at 3 -> delay",
        MismatchType.SETTLEMENT_DELAY
        in diagnose([make_candidate(vendor_score=95.0, amount_pct_diff=0, date_diff=3, overall_confidence=80.0)]).labels,
    )
    check(
        "Date at 4 -> no delay",
        MismatchType.SETTLEMENT_DELAY
        not in diagnose([make_candidate(vendor_score=95.0, amount_pct_diff=0, date_diff=4, overall_confidence=75.0)]).labels,
    )
    check(
        "Amount at 25% -> tip/tax",
        MismatchType.TIP_TAX_VARIANCE
        in diagnose([make_candidate(vendor_score=100.0, amount_diff=25.0, amount_pct_diff=25.0, date_diff=0, overall_confidence=65.0)]).labels,
    )
    check(
        "Amount at 25.1% -> no tip/tax",
        MismatchType.TIP_TAX_VARIANCE
        not in diagnose([make_candidate(vendor_score=100.0, amount_diff=25.1, amount_pct_diff=25.1, date_diff=0, overall_confidence=60.0)]).labels,
    )
    check(
        "Amount at 2% -> amounts match",
        MismatchType.TIP_TAX_VARIANCE
        not in diagnose([make_candidate(vendor_score=100.0, amount_diff=2.0, amount_pct_diff=2.0, date_diff=0, overall_confidence=90.0)]).labels,
    )
    check(
        "Amount at 2.1% -> amounts differ",
        MismatchType.TIP_TAX_VARIANCE
        in diagnose([make_candidate(vendor_score=100.0, amount_diff=2.1, amount_pct_diff=2.1, date_diff=0, overall_confidence=88.0)]).labels,
    )

    # Category 4: Evidence quality.
    print("\n  Evidence Quality:")
    check("Diagnosis always has evidence", len(diag_vendor.evidence) >= 4)
    check("NO_MATCH has evidence", len(diag_none.evidence) >= 2)
    check(
        "Vendor diagnosis includes mismatch language",
        any("vendor" in e.lower() or "mismatch" in e.lower() for e in diag_vendor.evidence),
    )
    check(
        "Evidence strings are non-trivial",
        all(isinstance(ev, str) and len(ev) > 10 for d in [diag_vendor, diag_none] for ev in d.evidence),
    )
    check(
        "Evidence order keeps match evidence first",
        len(diag_vendor.evidence) >= 3 and diag_vendor.evidence[0].lower().startswith("vendor score"),
    )

    # Category 5: Diagnosis properties.
    print("\n  Diagnosis Properties:")
    check(
        "is_match works",
        diagnose([make_candidate(overall_confidence=85)]).is_match is True and diagnose([]).is_match is False,
    )
    check(
        "is_clean_match works",
        diag_clean.is_clean_match is True and diag_clean.label_summary == "Clean Match",
    )
    check(
        "is_compound works",
        d_vendor_delay.is_compound is True and "+" in d_vendor_delay.label_summary,
    )
    check("label_summary correct", diagnose([]).label_summary == "No Match Found")

    # Category 6: Receipt context.
    print("\n  Receipt Context:")
    receipt_low = ReceiptData(vendor="Fast3nal", total=178.23, confidence=0.65)
    diag_low = diagnose(
        [make_candidate(vendor_score=59, amount_diff=4.36, amount_pct_diff=2.4, date_diff=2, overall_confidence=70)],
        receipt=receipt_low,
    )
    check(
        "Low confidence warning present",
        any(("confidence" in e.lower()) or ("⚠" in e) for e in diag_low.evidence),
    )

    receipt_tip = ReceiptData(vendor="El Agave", total=47.50, tip=7.00, tax=3.50)
    diag_tip_ctx = diagnose(
        [make_candidate(vendor_score=100, amount_diff=5.00, amount_pct_diff=10.5, date_diff=0, overall_confidence=83, amount=52.50)],
        receipt=receipt_tip,
    )
    check("Receipt with tip preserved", diag_tip_ctx.receipt is not None and diag_tip_ctx.receipt.has_tip is True)
    check(
        "Tip context appears in evidence",
        any("receipt includes a $7.00 tip" in e.lower() for e in diag_tip_ctx.evidence),
    )

    # Category 7: Integration - extract -> match -> diagnose on all 6 receipts.
    print("\n  Integration - Full Pipeline:")
    base_dir = Path(__file__).resolve().parent
    csv_path = base_dir / "test_data" / "transactions.csv"
    df = pd.read_csv(csv_path)

    original_key = os.environ.pop("VISION_AGENT_API_KEY", None)
    try:
        r01 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_01_clean_match.png"))
        d01 = diagnose(find_matches(r01, df), r01)
        check("Receipt 01: clean match", (d01.labels == [] or d01.is_clean_match) and d01.confidence > 80)

        r02 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_02_vendor_mismatch.png"))
        d02 = diagnose(find_matches(r02, df), r02)
        check("Receipt 02: VENDOR_MISMATCH", MismatchType.VENDOR_MISMATCH in d02.labels)

        r03 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_03_tip_tax_variance.png"))
        d03 = diagnose(find_matches(r03, df), r03)
        check(
            "Receipt 03: PARTIAL_MATCH or TIP_TAX_VARIANCE",
            MismatchType.PARTIAL_MATCH in d03.labels or MismatchType.TIP_TAX_VARIANCE in d03.labels,
        )

        r04 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_04_settlement_delay.png"))
        d04 = diagnose(find_matches(r04, df), r04)
        check("Receipt 04: SETTLEMENT_DELAY", MismatchType.SETTLEMENT_DELAY in d04.labels)

        r05 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_05_combined_mismatch.png"))
        d05 = diagnose(find_matches(r05, df), r05)
        check("Receipt 05: compound (2+ labels)", len(d05.labels) >= 2 and d05.is_compound is True)

        r06 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_06_no_match.png"))
        d06 = diagnose(find_matches(r06, df), r06)
        check("Receipt 06: NO_MATCH", MismatchType.NO_MATCH in d06.labels and d06.top_match is None)
    finally:
        if original_key is not None:
            os.environ["VISION_AGENT_API_KEY"] = original_key

    print(f"\n{LINE * 62}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print(f"  Phase 5: COMPLETE {PASS}")
    else:
        print(f"  Phase 5: {failed} FAILED - fix before proceeding")
    print(f"{LINE * 62}")


if __name__ == "__main__":
    main()

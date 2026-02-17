"""
test_normalize.py - Phase 3 Normalization Module Tests

Comprehensive validation for:
- normalize_vendor
- normalize_date
- normalize_amount
- normalize_receipt_data
- normalize_transaction_data
- normalize_for_comparison

Usage: python test_normalize.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Ensure we can import from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from models import ReceiptData
from normalize import (
    normalize_amount,
    normalize_date,
    normalize_for_comparison,
    normalize_receipt_data,
    normalize_transaction_data,
    normalize_vendor,
)


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


def _nearly_equal(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


def main() -> None:
    passed = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal passed, failed
        if condition:
            print(f"    {PASS} {name}")
            passed += 4
        else:
            print(f"    {FAIL} {name}")
            failed += 1

    print(LINE * 42)
    print("  Phase 3: Normalization Module Tests")
    print(LINE * 42)

    # Category 1: normalize_vendor
    vendor_test_cases: list[tuple[Any, str, str]] = [
        ("", "", "empty string"),
        (None, "", "None input"),
        ("   ", "", "whitespace only"),
        ("STARBUCKS", "starbucks", "all caps"),
        ("Starbucks", "starbucks", "mixed case"),
        ("SQ *JOE'S PIZZA GRILL", "joes pizza grill", "Square prefix"),
        ("PP*JOHNDEEREFINAN", "johndeerefinan", "PayPal prefix"),
        ("TST*GREENVILLE COFFEE", "greenville coffee", "Toast prefix"),
        ("AMZN MKTP US*2K4RF83J0", "amazon", "Amazon with txn code -> alias"),
        ("ELAGAVE*1847 CHATT TN", "elagave", "El Agave bank descriptor"),
        ("ELAGAVE*1847", "elagave", "El Agave without city"),
        ("Starbucks #14892", "starbucks", "store number stripped"),
        ("THE HOME DEPOT #4821", "home depot", "Home Depot store number + alias"),
        ("TARGET # 2847", "target", "Target with space before number"),
        ("McDonald's", "mcdonalds", "apostrophe removed"),
        ("Bob's Local Hardware", "bobs local hardware", "possessive removed"),
        ("El Agave Mexican Restaurant", "el agave mexican", "restaurant stripped"),
        ("Greenville Supply Inc", "greenville supply", "inc stripped"),
        ("ABC Services LLC", "abc", "services + llc stripped"),
        ("Amazon.com", "amazon", "amazon.com alias"),
        ("Amazon", "amazon", "amazon direct alias"),
        ("AMZN", "amazon", "amzn alias"),
        ("SBUX", "starbucks", "sbux alias"),
        ("WMT", "walmart", "wmt alias"),
        ("Home Depot", "home depot", "already canonical"),
        ("THE HOME DEPOT", "home depot", "the home depot alias"),
        ("AMZN MKTP US*2K4RF83J0", "amazon", "full Amazon bank descriptor"),
        ("SQ *GREENVILLE SUPPLY INC", "greenville supply", "Square + suffix"),
        ("THE HOME DEPOT #4821", "home depot", "store number + alias"),
        ("Amazon.com", "amazon", "Receipt 01 vendor -> normalized"),
        ("El Agave Mexican Restaurant", "el agave mexican", "Receipt 02 vendor -> normalized"),
        ("Starbucks", "starbucks", "Receipt 03 vendor -> normalized"),
        ("Home Depot", "home depot", "Receipt 04 vendor -> normalized"),
        ("Fastenal", "fastenal", "Receipt 05 vendor -> normalized"),
        ("Bob's Local Hardware", "bobs local hardware", "Receipt 06 vendor -> normalized"),
        ("ELAGAVE*1847 CHATT TN", "elagave", "TXN002 merchant -> normalized"),
        ("THE HOME DEPOT #4821", "home depot", "TXN004 merchant -> normalized"),
        ("FASTENAL CO01 CHATT", "fastenal co01 chatt", "TXN005 merchant -> normalized"),
        ("AMZN MKTP US*2K4RF", "amazon", "TXN010 merchant -> normalized"),
        ("SYSCO 4823847", "sysco 4823847", "TXN008 - no alias, digits preserved"),
        ("PP*JOHNDEEREFINAN", "johndeerefinan", "TXN009 - PayPal prefix stripped"),
    ]
    print(f"\n  normalize_vendor ({len(vendor_test_cases)} cases):")
    for raw, expected, desc in vendor_test_cases:
        got = normalize_vendor(raw)  # type: ignore[arg-type]
        check(f"{desc} -> '{expected}'", got == expected)

    # Category 2: normalize_date
    date_test_cases: list[tuple[Any, str, str]] = [
        ("2026-01-15", "2026-01-15", "ISO format"),
        ("01/15/2026", "2026-01-15", "US format MM/DD/YYYY"),
        ("1/15/2026", "2026-01-15", "US format no leading zero"),
        ("01/15/26", "2026-01-15", "US format 2-digit year"),
        ("Jan 15, 2026", "2026-01-15", "month name"),
        ("January 15, 2026", "2026-01-15", "full month name"),
        ("15 Jan 2026", "2026-01-15", "European day-first with month name"),
        ("15-Jan-2026", "2026-01-15", "dashed European"),
        ("01-15-2026", "2026-01-15", "dashed US"),
        ("01/15/2026 14:23:05", "2026-01-15", "date with time"),
        ("Jan 15, 2026 2:23 PM", "2026-01-15", "date with 12-hour time"),
        ("2026-01-15T14:23:05", "2026-01-15", "ISO with T separator"),
        ("", "", "empty string"),
        (None, "", "None input"),
        ("   ", "", "whitespace only"),
        ("not a date", "", "unparseable text"),
        ("N/A", "", "N/A string"),
        ("2026-01-10", "2026-01-10", "TXN001 date"),
        ("2026-01-12", "2026-01-12", "TXN002 date"),
        ("2026-01-14", "2026-01-14", "TXN003 date"),
        ("2026-01-15", "2026-01-15", "Receipt 04 date"),
        ("2026-01-17", "2026-01-17", "TXN004 date (settlement)"),
        ("2026-01-18", "2026-01-18", "Receipt 05 date"),
        ("2026-01-20", "2026-01-20", "TXN005 date (settlement)"),
    ]
    print(f"\n  normalize_date ({len(date_test_cases)} cases):")
    for raw, expected, desc in date_test_cases:
        got = normalize_date(raw)  # type: ignore[arg-type]
        check(f"{desc} -> '{expected}'", got == expected)

    # Category 3: normalize_amount
    amount_test_cases: list[tuple[Any, float, str]] = [
        ("$89.97", 89.97, "dollar sign"),
        ("$1,247.83", 1247.83, "dollar + commas"),
        ("\u20ac47.50", 47.50, "euro sign"),
        ("\u00a3234.67", 234.67, "pound sign"),
        (" $89.97 ", 89.97, "whitespace"),
        ("89.97", 89.97, "plain string"),
        ("1,247.83", 1247.83, "commas no currency"),
        (89.97, 89.97, "float passthrough"),
        (89, 89.0, "int to float"),
        (0, 0.0, "zero int"),
        (0.0, 0.0, "zero float"),
        ("", 0.0, "empty string"),
        (None, 0.0, "None"),
        ("N/A", 0.0, "N/A string"),
        ("five dollars", 0.0, "words"),
        ("-$5.00", 0.0, "negative dollar"),
        (-5.0, 0.0, "negative float"),
        ("($5.00)", 0.0, "accounting negative notation"),
        (47.499999999, 47.5, "floating point rounding"),
        (47.505, 47.51, "round to 2 decimals"),
        (89.97, 89.97, "TXN001 amount"),
        (47.50, 47.5, "TXN002 amount"),
        (6.83, 6.83, "TXN003 amount"),
        (234.67, 234.67, "TXN004 amount"),
        (182.59, 182.59, "TXN005 amount"),
    ]
    print(f"\n  normalize_amount ({len(amount_test_cases)} cases):")
    for raw, expected, desc in amount_test_cases:
        got = normalize_amount(raw)  # type: ignore[arg-type]
        check(f"{desc} -> {expected}", _nearly_equal(got, expected))

    # Category 4: Convenience wrappers
    print("\n  Convenience Wrappers:")
    receipt = ReceiptData(
        vendor="El Agave Mexican Restaurant",
        total=47.50,
        date="01/12/2026",
    )
    vendor, date, amount = normalize_receipt_data(receipt)
    check(
        "normalize_receipt_data correct",
        vendor == "el agave mexican" and date == "2026-01-12" and _nearly_equal(amount, 47.5),
    )
    vendor, date, amount = normalize_transaction_data(
        "ELAGAVE*1847 CHATT TN",
        "2026-01-12",
        "$47.50",
    )
    check(
        "normalize_transaction_data correct",
        vendor == "elagave" and date == "2026-01-12" and _nearly_equal(amount, 47.5),
    )

    # Category 5: normalize_for_comparison with real CSV
    print("\n  Full CSV Normalization:")
    base_dir = Path(__file__).resolve().parent
    csv_path = base_dir / "test_data" / "transactions.csv"
    df = pd.read_csv(csv_path)
    receipt = ReceiptData(vendor="El Agave Mexican Restaurant", total=47.50, date="2026-01-12")
    receipt_norm, df_norm = normalize_for_comparison(receipt, df)
    check(
        "Receipt normalized correctly",
        receipt_norm[0] == "el agave mexican"
        and receipt_norm[1] == "2026-01-12"
        and _nearly_equal(receipt_norm[2], 47.5),
    )
    check(
        "DataFrame has new columns",
        {"norm_merchant", "norm_date", "norm_amount"}.issubset(set(df_norm.columns)),
    )
    check(
        "Specific merchants normalized correctly",
        df_norm.iloc[0]["norm_merchant"] == "amazon"
        and df_norm.iloc[1]["norm_merchant"] == "elagave"
        and df_norm.iloc[3]["norm_merchant"] == "home depot",
    )
    check("Original DataFrame not modified", "norm_merchant" not in df.columns)

    # Category 6: Cross-side consistency
    print("\n  Cross-Side Consistency:")
    check(
        "Same vendor -> same output both sides",
        normalize_vendor("Amazon.com") == normalize_vendor("Amazon.com"),
    )
    receipt = ReceiptData(vendor="Starbucks", total=5.25, date="2026-01-14")
    r_vendor, r_date, r_amount = normalize_receipt_data(receipt)
    t_vendor, t_date, t_amount = normalize_transaction_data("Starbucks", "2026-01-14", 5.25)
    check("Same date -> same output both sides", r_date == t_date)
    check(
        "Same amount -> same output both sides",
        r_vendor == t_vendor and _nearly_equal(r_amount, t_amount),
    )

    print(f"\n{LINE * 42}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print(f"  Phase 3: COMPLETE {PASS}")
    else:
        print(f"  Phase 3: {failed} FAILED - fix before proceeding")
    print(f"{LINE * 42}")


if __name__ == "__main__":
    main()

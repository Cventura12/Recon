"""
test_match.py - Phase 4 Matching Engine Tests

End-to-end checks for:
- score_vendor
- score_amount
- score_date
- find_matches

Usage: python test_match.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Ensure local imports resolve from project root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from match import find_matches, score_amount, score_date, score_vendor
from models import ReceiptData
from normalize import normalize_vendor


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


def _in_range(value: float, low: float, high: float) -> bool:
    return low <= value < high


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
    print("  Phase 4: Matching Engine Tests")
    print(LINE * 62)

    # Category 1: score_vendor
    vendor_cases: list[dict[str, Any]] = [
        {"r": "Amazon.com", "t": "Amazon", "range": (90, 101), "desc": "Amazon.com vs Amazon"},
        {"r": "Starbucks", "t": "Starbucks", "range": (100, 101), "desc": "Starbucks vs Starbucks"},
        {"r": "Home Depot", "t": "THE HOME DEPOT #4821", "range": (95, 101), "desc": "Home Depot vs THE HOME DEPOT #4821"},
        {
            "r": "El Agave Mexican Restaurant",
            "t": "ELAGAVE*1847 CHATT TN",
            "range": (40, 75),
            "desc": "El Agave vs ELAGAVE*1847",
        },
        {"r": "Fastenal", "t": "FASTENAL CO01 CHATT", "range": (40, 70), "desc": "Fastenal vs FASTENAL CO01 CHATT"},
        {"r": "Bob's Local Hardware", "t": "Walmart", "range": (0, 35), "desc": "Bob's vs Walmart"},
        {"r": "Bob's Local Hardware", "t": "Shell Gas Station", "range": (0, 35), "desc": "Bob's vs Shell"},
        {"r": "Starbucks", "t": "SYSCO 4823847", "range": (0, 35), "desc": "Starbucks vs SYSCO"},
        {"r": "", "t": "", "exact": 0.0, "desc": "Both empty"},
        {"r": "Starbucks", "t": "", "exact": 0.0, "desc": "Bank empty"},
        {"r": "", "t": "Amazon", "exact": 0.0, "desc": "Receipt empty"},
        {"r": None, "t": "Amazon", "exact": 0.0, "desc": "Receipt None"},
        {"r": "Amazon.com", "t": "AMZN MKTP US*2K4RF", "range": (95, 101), "desc": "Amazon alias equivalence"},
        {"r": "PP*JOHNDEEREFINAN", "t": "JohnDeereFinan", "range": (95, 101), "desc": "PayPal prefix removed"},
        {"r": "SQ *JOE'S PIZZA GRILL", "t": "Joes Pizza Grill", "range": (95, 101), "desc": "Square prefix removed"},
    ]
    print(f"\n  score_vendor ({len(vendor_cases)} cases):")
    for case in vendor_cases:
        score, evidence = score_vendor(case["r"], case["t"])  # type: ignore[arg-type]
        rv = normalize_vendor(case["r"])  # type: ignore[arg-type]
        tv = normalize_vendor(case["t"])  # type: ignore[arg-type]

        if "range" in case:
            score_ok = _in_range(score, case["range"][0], case["range"][1])
        else:
            score_ok = _nearly_equal(score, case["exact"])

        evidence_ok = isinstance(evidence, str) and len(evidence) > 0
        if rv == tv:
            names_ok = rv in evidence
        else:
            names_ok = rv in evidence and tv in evidence

        tuple_ok = isinstance(score, float) and isinstance(evidence, str)
        check(
            f"{case['desc']}: score={score}",
            score_ok and evidence_ok and names_ok and tuple_ok,
        )

    # Category 2: score_amount
    amount_cases: list[dict[str, Any]] = [
        {"r": 89.97, "t": 89.97, "range": (100, 101), "diff": 0.0, "desc": "$89.97 vs $89.97"},
        {"r": 47.50, "t": 47.50, "range": (100, 101), "diff": 0.0, "desc": "$47.50 vs $47.50"},
        {"r": 234.67, "t": 234.67, "range": (100, 101), "diff": 0.0, "desc": "$234.67 vs $234.67"},
        {"r": 178.23, "t": 182.59, "range": (85, 95), "diff": 4.36, "desc": "$178.23 vs $182.59"},
        {"r": 5.25, "t": 6.83, "range": (0, 5), "diff": 1.58, "desc": "$5.25 vs $6.83"},
        {"r": 0.0, "t": 50.0, "range": (0, 1), "diff": 50.0, "desc": "$0.00 vs $50.00"},
        {"r": 100.0, "t": 0.0, "range": (0, 1), "diff": 100.0, "desc": "$100.00 vs $0.00"},
        {"r": 100.0, "t": 100.0, "range": (100, 101), "diff": 0.0, "desc": "$100.00 vs $100.00"},
        {"r": 100.0, "t": 90.0, "range": (55, 65), "diff": 10.0, "desc": "$100.00 vs $90.00"},
        {"r": 100.0, "t": 130.0, "range": (0, 1), "diff": 30.0, "desc": "$100.00 vs $130.00"},
        {"r": 50.0, "t": 51.0, "range": (90, 95), "diff": 1.0, "desc": "$50.00 vs $51.00"},
        {"r": 10.0, "t": 7.0, "range": (0, 1), "diff": 3.0, "desc": "$10.00 vs $7.00"},
    ]
    print(f"\n  score_amount ({len(amount_cases)} cases):")
    for case in amount_cases:
        score, abs_diff, pct_diff, evidence = score_amount(case["r"], case["t"])
        score_ok = _in_range(score, case["range"][0], case["range"][1])
        diff_ok = _nearly_equal(abs_diff, case["diff"])
        evidence_ok = isinstance(evidence, str) and len(evidence) > 0
        tuple_ok = (
            isinstance(score, float)
            and isinstance(abs_diff, float)
            and isinstance(pct_diff, float)
            and isinstance(evidence, str)
        )
        check(
            f"{case['desc']}: score={score}, diff=${abs_diff:.2f}",
            score_ok and diff_ok and evidence_ok and tuple_ok,
        )

    # Category 3: score_date
    date_cases: list[dict[str, Any]] = [
        {"r": "2026-01-10", "t": "2026-01-10", "score": 100.0, "days": 0, "desc": "Same day #1"},
        {"r": "2026-01-12", "t": "2026-01-12", "score": 100.0, "days": 0, "desc": "Same day #2"},
        {"r": "2026-01-15", "t": "2026-01-17", "score": 60.0, "days": 2, "desc": "2-day delay (R04)"},
        {"r": "2026-01-18", "t": "2026-01-20", "score": 60.0, "days": 2, "desc": "2-day delay (R05)"},
        {"r": "2026-01-15", "t": "2026-01-16", "score": 80.0, "days": 1, "desc": "1-day delay"},
        {"r": "2026-01-15", "t": "2026-01-18", "score": 40.0, "days": 3, "desc": "3-day delay"},
        {"r": "2026-01-10", "t": "2026-01-22", "score": 0.0, "days": 12, "desc": "12 days apart"},
        {"r": "", "t": "2026-01-12", "score": 0.0, "days": 999, "desc": "Missing receipt date"},
        {"r": "2026-01-12", "t": "", "score": 0.0, "days": 999, "desc": "Missing bank date"},
        {"r": "", "t": "", "score": 0.0, "days": 999, "desc": "Both dates missing"},
    ]
    print(f"\n  score_date ({len(date_cases)} cases):")
    for case in date_cases:
        score, days, evidence = score_date(case["r"], case["t"])
        ok = _nearly_equal(score, case["score"]) and days == case["days"] and isinstance(evidence, str) and len(evidence) > 0
        check(f"{case['desc']}: score={score}, days={days}", ok)

    # Category 4: find_matches full pipeline with real CSV
    print("\n  find_matches - Full Pipeline:")
    df = pd.read_csv(Path(__file__).resolve().parent / "test_data" / "transactions.csv")

    r01 = ReceiptData(vendor="Amazon.com", total=89.97, date="2026-01-10", confidence=0.98)
    r02 = ReceiptData(vendor="El Agave Mexican Restaurant", total=47.50, date="2026-01-12", confidence=0.95)
    r03 = ReceiptData(vendor="Starbucks", total=5.25, date="2026-01-14", confidence=0.97)
    r04 = ReceiptData(vendor="Home Depot", total=234.67, date="2026-01-15", confidence=0.96)
    r05 = ReceiptData(vendor="Fastenal", total=178.23, date="2026-01-18", confidence=0.72)
    r06 = ReceiptData(vendor="Bob's Local Hardware", total=45.00, date="2026-01-22", confidence=0.93)

    matches_01 = find_matches(r01, df)
    matches_02 = find_matches(r02, df)
    matches_03 = find_matches(r03, df)
    matches_04 = find_matches(r04, df)
    matches_05 = find_matches(r05, df)
    matches_06 = find_matches(r06, df)

    check(
        "Receipt 01 (Amazon): 1+ matches, top=TXN001, confidence>85%",
        len(matches_01) >= 1
        and matches_01[0].transaction.transaction_id == "TXN001"
        and matches_01[0].overall_confidence > 85
        and matches_01[0].vendor_score > 90
        and _nearly_equal(matches_01[0].amount_diff, 0.0)
        and matches_01[0].date_diff == 0,
    )
    check(
        "Receipt 02 (El Agave): top=TXN002, vendor_score<80",
        len(matches_02) >= 1
        and matches_02[0].transaction.transaction_id == "TXN002"
        and matches_02[0].vendor_score < 80
        and _nearly_equal(matches_02[0].amount_diff, 0.0)
        and matches_02[0].date_diff == 0,
    )
    check(
        "Receipt 03 (Starbucks): top=TXN003, amount_diff>0",
        len(matches_03) >= 1
        and matches_03[0].transaction.transaction_id == "TXN003"
        and matches_03[0].amount_diff > 0
        and matches_03[0].amount_pct_diff > 25,
    )
    check(
        "Receipt 04 (Home Depot): top=TXN004, date_diff=2",
        len(matches_04) >= 1
        and matches_04[0].transaction.transaction_id == "TXN004"
        and matches_04[0].date_diff == 2
        and _nearly_equal(matches_04[0].amount_diff, 0.0)
        and matches_04[0].vendor_score > 90,
    )
    check(
        "Receipt 05 (Fastenal): top=TXN005, compound mismatch signals",
        len(matches_05) >= 1
        and matches_05[0].transaction.transaction_id == "TXN005"
        and matches_05[0].vendor_score < 80
        and matches_05[0].amount_diff > 0
        and matches_05[0].date_diff > 0,
    )
    check("Receipt 06 (Bob's): no matches (empty list)", len(matches_06) == 0)

    # Category 5: edge cases
    print("\n  find_matches - Edge Cases:")
    check("Empty DataFrame returns []", find_matches(r01, pd.DataFrame()) == [])
    check(
        "Missing columns returns []",
        find_matches(r01, pd.DataFrame({"wrong": [1]})) == [],
    )
    r_no_date = ReceiptData(vendor="Starbucks", total=5.25, date=None)
    matches_no_date = find_matches(r_no_date, df)
    check("No-date receipt still produces candidates", len(matches_no_date) > 0)

    sorted_ok = True
    for grouped in [matches_01, matches_02, matches_03, matches_04, matches_05]:
        for i in range(len(grouped) - 1):
            if grouped[i].overall_confidence < grouped[i + 1].overall_confidence:
                sorted_ok = False
                break
    check("Results sorted by confidence descending", sorted_ok)

    # Category 6: evidence integrity
    print("\n  Evidence Integrity:")
    all_candidates = [c for group in [matches_01, matches_02, matches_03, matches_04, matches_05] for c in group]

    check("All candidates have 3 evidence strings", all(len(c.evidence) == 3 for c in all_candidates))
    check(
        "All evidence strings non-empty",
        all(isinstance(ev, str) and len(ev) > 0 for c in all_candidates for ev in c.evidence),
    )
    check(
        "All sub-scores in valid ranges",
        all(
            0 <= c.vendor_score <= 100
            and c.amount_diff >= 0
            and c.amount_pct_diff >= 0
            and c.date_diff >= 0
            and 0 <= c.overall_confidence <= 100
            for c in all_candidates
        ),
    )
    check(
        "All candidates include transaction core fields",
        all(c.transaction.merchant is not None and c.transaction.date is not None for c in all_candidates),
    )
    check(
        "Evidence order is vendor -> amount -> date",
        all(
            c.evidence[0].lower().startswith("vendor")
            and "amount" in c.evidence[1].lower()
            and any(
                token in c.evidence[2].lower()
                for token in (
                    "same date",
                    "settlement delay",
                    "date gap",
                    "date mismatch",
                    "missing",
                    "cannot compare",
                )
            )
            for c in all_candidates
        ),
    )

    print(f"\n{LINE * 62}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print(f"  Phase 4: COMPLETE {PASS}")
    else:
        print(f"  Phase 4: {failed} FAILED - fix before proceeding")
    print(f"{LINE * 62}")


if __name__ == "__main__":
    main()

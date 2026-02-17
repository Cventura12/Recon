"""
test_explain.py - Phase 6 Explanation Module Tests

Validates:
- format_explanation (terminal text output)
- format_explanation_json (structured API output)
- full pipeline integration for all six test receipts

Usage: python test_explain.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure imports resolve from project root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from diagnose import diagnose
from explain import format_explanation, format_explanation_json
from extract import extract_receipt
from match import find_matches
from models import Diagnosis, MatchCandidate, MismatchType, ReceiptData, Transaction


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


def make_diagnosis(
    labels: list[MismatchType] | None = None,
    confidence: float = 85.0,
    evidence: list[str] | None = None,
    has_match: bool = True,
    has_receipt: bool = True,
    receipt_confidence: float = 0.95,
    vendor_score: float = 80.0,
    amount_diff: float = 0.0,
    amount_pct_diff: float = 0.0,
    date_diff: int = 0,
    receipt_vendor: str = "Test Vendor",
    receipt_total: float = 100.0,
    receipt_date: str | None = "2026-01-15",
    bank_merchant: str = "TEST MERCHANT",
    bank_amount: float = 100.0,
    bank_date: str = "2026-01-15",
    receipt_tip: float | None = None,
    receipt_tax: float | None = None,
) -> Diagnosis:
    """Create controlled Diagnosis fixtures for explanation tests."""
    receipt = None
    if has_receipt:
        receipt = ReceiptData(
            vendor=receipt_vendor,
            total=receipt_total,
            date=receipt_date,
            tip=receipt_tip,
            tax=receipt_tax,
            confidence=receipt_confidence,
        )

    top_match = None
    if has_match:
        top_match = MatchCandidate(
            transaction=Transaction(
                merchant=bank_merchant,
                amount=bank_amount,
                date=bank_date,
            ),
            vendor_score=vendor_score,
            amount_diff=amount_diff,
            amount_pct_diff=amount_pct_diff,
            date_diff=date_diff,
            overall_confidence=confidence,
            evidence=[
                f"Vendor score: {vendor_score}",
                f"Amount diff: ${amount_diff:.2f}",
                f"Date diff: {date_diff} days",
            ],
        )

    return Diagnosis(
        labels=labels or [],
        confidence=confidence,
        evidence=evidence or (list(top_match.evidence) if top_match else ["No match evidence"]),
        top_match=top_match,
        receipt=receipt,
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
    print("  Phase 6: Explanation Module Tests")
    print(LINE * 62)

    vendor_diag = make_diagnosis(
        labels=[MismatchType.VENDOR_MISMATCH],
        confidence=84.0,
        receipt_vendor="El Agave Mexican Restaurant",
        receipt_total=47.50,
        receipt_date="2026-01-12",
        bank_merchant="ELAGAVE*1847 CHATT TN",
        bank_amount=47.50,
        bank_date="2026-01-12",
        vendor_score=61.0,
        evidence=[
            "Vendor names differ: 'el agave mexican' vs 'elagave' (score: 61)",
            "Exact amount match: $47.50",
            "Same date: 2026-01-12",
            "Vendor descriptor mismatch: names scored 61/100 (threshold: 80)",
        ],
    )
    delay_diag = make_diagnosis(
        labels=[MismatchType.SETTLEMENT_DELAY],
        confidence=90.0,
        receipt_vendor="Home Depot",
        receipt_total=234.67,
        receipt_date="2026-01-15",
        bank_merchant="THE HOME DEPOT #4821",
        bank_amount=234.67,
        bank_date="2026-01-17",
        date_diff=2,
        evidence=[
            "Vendor names match exactly: 'home depot'",
            "Exact amount match: $234.67",
            "Settlement delay: 2 day(s) later (receipt: 2026-01-15, bank: 2026-01-17)",
            "Settlement delay: 2 day(s) between receipt and posting.",
        ],
    )
    no_match_diag = make_diagnosis(
        labels=[MismatchType.NO_MATCH],
        confidence=95.0,
        has_match=False,
        receipt_vendor="Bob's Local Hardware",
        receipt_total=45.00,
        receipt_date="2026-01-22",
        evidence=[
            "No transactions in the CSV scored above the 30% threshold.",
            "Receipt dated 2026-01-22 - verify transactions from this range.",
            "Possible causes: not yet posted, different account, wrong dataset.",
        ],
    )
    clean_diag = make_diagnosis(
        labels=[],
        confidence=92.0,
        receipt_vendor="Amazon.com",
        receipt_total=89.97,
        receipt_date="2026-01-10",
        bank_merchant="Amazon",
        bank_amount=89.97,
        bank_date="2026-01-10",
        vendor_score=100.0,
        evidence=[
            "Vendor names match: 'amazon' ~ 'amazon' (score: 100)",
            "Exact amount match: $89.97",
            "Same date: 2026-01-10",
            "All signals align - clean match with no exception.",
        ],
    )
    compound_diag = make_diagnosis(
        labels=[
            MismatchType.VENDOR_MISMATCH,
            MismatchType.SETTLEMENT_DELAY,
            MismatchType.TIP_TAX_VARIANCE,
        ],
        confidence=70.0,
        receipt_vendor="Fastenal",
        bank_merchant="FASTENAL CO01 CHATT",
        receipt_total=178.23,
        bank_amount=182.59,
        amount_diff=4.36,
        amount_pct_diff=2.4,
        date_diff=2,
        vendor_score=59.0,
        receipt_confidence=0.72,
        evidence=[
            "Vendor names differ: 'fastenal' vs 'fastenal co01 chatt' (score: 59)",
            "Amount very close: $178.23 vs $182.59 (diff: +$4.36, 2.4%)",
            "Settlement delay: 2 day(s) later (receipt: 2026-01-18, bank: 2026-01-20)",
            "Vendor descriptor mismatch triggered",
            "Settlement delay triggered",
            "Tip/tax variance triggered",
            "⚠ Low extraction confidence (72%). Verify manually.",
        ],
    )
    low_conf_diag = make_diagnosis(
        labels=[MismatchType.VENDOR_MISMATCH],
        confidence=70.0,
        receipt_confidence=0.65,
    )
    all_test_diagnoses = [
        vendor_diag,
        delay_diag,
        no_match_diag,
        clean_diag,
        compound_diag,
        low_conf_diag,
    ]

    # Category 1: text structure/content.
    print("\n  format_explanation - Text Structure:")
    text_vendor = format_explanation(vendor_diag)
    check(
        "Vendor mismatch: has header, receipt, match, evidence, label",
        ("Probable Match" in text_vendor or "Match" in text_vendor)
        and "84%" in text_vendor
        and "El Agave Mexican Restaurant" in text_vendor
        and "$47.50" in text_vendor
        and "ELAGAVE*1847 CHATT TN" in text_vendor
        and "Vendor Descriptor Mismatch" in text_vendor
        and "•" in text_vendor
        and "Diagnosis:" in text_vendor,
    )

    text_delay = format_explanation(delay_diag)
    check(
        "Settlement delay: correct sections",
        "90%" in text_delay
        and "Home Depot" in text_delay
        and "THE HOME DEPOT" in text_delay
        and "Settlement Delay" in text_delay,
    )

    text_no_match = format_explanation(no_match_diag)
    check(
        "NO_MATCH: no best match section, correct label",
        "NO MATCH" in text_no_match
        and "Bob's Local Hardware" in text_no_match
        and "$45.00" in text_no_match
        and "Best Match:" not in text_no_match
        and "No Match Found" in text_no_match,
    )

    text_clean = format_explanation(clean_diag)
    check(
        "Clean match: correct label",
        "92%" in text_clean
        and "Amazon" in text_clean
        and ("Clean Match" in text_clean or "No Exception" in text_clean),
    )

    text_compound = format_explanation(compound_diag)
    check(
        "Compound: labels joined with +, low confidence warning",
        "70%" in text_compound
        and "Fastenal" in text_compound
        and "+" in text_compound
        and ("⚠" in text_compound or "confidence" in text_compound.lower()),
    )

    text_low_conf = format_explanation(low_conf_diag)
    check(
        "Low confidence: warning present",
        ("⚠" in text_low_conf or "confidence" in text_low_conf.lower())
        and ("65%" in text_low_conf or "0.65" in text_low_conf),
    )

    # Category 2: formatting quality.
    print("\n  format_explanation - Formatting Quality:")
    check(
        "Output is non-empty string",
        all(isinstance(format_explanation(diag), str) and len(format_explanation(diag)) > 100 for diag in all_test_diagnoses),
    )
    check(
        "Multi-line output (10+ lines)",
        format_explanation(vendor_diag).count("\n") >= 10,
    )
    trimmed = format_explanation(vendor_diag).strip().split("\n")
    check(
        "Starts/ends with separator",
        len(trimmed) >= 2 and ("=" in trimmed[0]) and ("=" in trimmed[-1]),
    )
    check(
        "Dollar amounts have 2 decimals",
        "$5.00" in format_explanation(make_diagnosis(receipt_total=5.00))
        and "$1247.83" in format_explanation(make_diagnosis(receipt_total=1247.83)),
    )
    check(
        "Confidence shown as integer",
        "84%" in format_explanation(make_diagnosis(confidence=84.3))
        and "84.3%" not in format_explanation(make_diagnosis(confidence=84.3)),
    )
    check(
        "Edge case: no receipt data handled",
        "(no receipt data available)"
        in format_explanation(make_diagnosis(has_receipt=False, has_match=False, labels=[MismatchType.NO_MATCH])),
    )

    # Category 3: JSON schema validation.
    print("\n  format_explanation_json - Schema:")
    json_results = [format_explanation_json(diag) for diag in all_test_diagnoses]
    check("All diagnosis types produce dict output", all(isinstance(r, dict) for r in json_results))
    check(
        "All diagnosis types produce valid JSON",
        all(json.loads(json.dumps(r)) == r for r in json_results),
    )
    required_keys = {"status", "confidence", "diagnosis", "evidence", "receipt", "top_match", "warnings"}
    check("All required keys present", all(required_keys.issubset(set(r.keys())) for r in json_results))
    check("Status is valid value", all(r["status"] in ("match_found", "no_match", "clean_match") for r in json_results))
    check(
        "Confidence in range",
        all(isinstance(r["confidence"], (int, float)) and 0 <= r["confidence"] <= 100 for r in json_results),
    )
    check(
        "Diagnosis section shape valid",
        all(
            isinstance(r["diagnosis"], dict)
            and {"labels", "label_names", "label_summary", "is_compound", "is_clean_match"}.issubset(set(r["diagnosis"].keys()))
            and isinstance(r["diagnosis"]["labels"], list)
            and isinstance(r["diagnosis"]["is_compound"], bool)
            for r in json_results
        ),
    )
    check(
        "Evidence is list of strings",
        all(isinstance(r["evidence"], list) and all(isinstance(ev, str) for ev in r["evidence"]) for r in json_results),
    )
    check("Warnings is list", all(isinstance(r["warnings"], list) for r in json_results))

    # Category 4: JSON status mapping.
    print("\n  format_explanation_json - Status Values:")
    status_no_match = format_explanation_json(make_diagnosis(labels=[MismatchType.NO_MATCH], has_match=False))
    check('NO_MATCH -> "no_match"', status_no_match["status"] == "no_match" and status_no_match["top_match"] is None)
    status_clean = format_explanation_json(make_diagnosis(labels=[], confidence=92))
    check('Clean -> "clean_match"', status_clean["status"] == "clean_match" and status_clean["diagnosis"]["is_clean_match"] is True)
    status_mismatch = format_explanation_json(make_diagnosis(labels=[MismatchType.VENDOR_MISMATCH]))
    check('Mismatch -> "match_found"', status_mismatch["status"] == "match_found" and len(status_mismatch["diagnosis"]["labels"]) == 1)
    status_compound = format_explanation_json(
        make_diagnosis(labels=[MismatchType.VENDOR_MISMATCH, MismatchType.SETTLEMENT_DELAY])
    )
    check('Compound -> "match_found" + is_compound=true', status_compound["status"] == "match_found" and status_compound["diagnosis"]["is_compound"] is True)

    # Category 5: nested JSON data details.
    print("\n  format_explanation_json - Nested Data:")
    nested_receipt = format_explanation_json(make_diagnosis(has_receipt=True, receipt_total=47.50))
    check("Receipt present when available", nested_receipt["receipt"] is not None and nested_receipt["receipt"]["total"] == 47.50)
    nested_no_receipt = format_explanation_json(
        make_diagnosis(has_receipt=False, has_match=False, labels=[MismatchType.NO_MATCH])
    )
    check("Receipt null when unavailable", nested_no_receipt["receipt"] is None)
    nested_match = format_explanation_json(make_diagnosis(has_match=True, bank_merchant="ELAGAVE*1847"))
    check("Top match present when available", nested_match["top_match"] is not None and nested_match["top_match"]["merchant"] == "ELAGAVE*1847")
    check("Scores nested correctly", nested_match["top_match"] is not None and "scores" in nested_match["top_match"] and "vendor_score" in nested_match["top_match"]["scores"])
    nested_no_match = format_explanation_json(make_diagnosis(has_match=False, labels=[MismatchType.NO_MATCH]))
    check("Top match null when unavailable", nested_no_match["top_match"] is None)
    nested_warn = format_explanation_json(make_diagnosis(receipt_confidence=0.65))
    check("Warnings populated for low confidence", len(nested_warn["warnings"]) >= 1 and any("confidence" in w.lower() for w in nested_warn["warnings"]))
    nested_ok_warn = format_explanation_json(make_diagnosis(receipt_confidence=0.95))
    check("Warnings empty for normal confidence", nested_ok_warn["warnings"] == [])
    check(
        "Labels are enum values (strings)",
        isinstance(status_compound["diagnosis"]["labels"], list)
        and all(isinstance(lbl, str) for lbl in status_compound["diagnosis"]["labels"]),
    )

    # Category 6: integration across pipeline.
    print("\n  Integration - Full Pipeline:")
    base_dir = Path(__file__).resolve().parent
    df = pd.read_csv(base_dir / "test_data" / "transactions.csv")
    integration_receipts: list[tuple[str, str]] = [
        ("test_data/receipts/receipt_01_clean_match.png", "Amazon"),
        ("test_data/receipts/receipt_02_vendor_mismatch.png", "El Agave"),
        ("test_data/receipts/receipt_03_tip_tax_variance.png", "Starbucks"),
        ("test_data/receipts/receipt_04_settlement_delay.png", "Home Depot"),
        ("test_data/receipts/receipt_05_combined_mismatch.png", "Fastenal"),
        ("test_data/receipts/receipt_06_no_match.png", "Bob's"),
    ]

    original_key = os.environ.pop("VISION_AGENT_API_KEY", None)
    try:
        for path_str, display_name in integration_receipts:
            receipt = extract_receipt(str(base_dir / path_str))
            matches = find_matches(receipt, df)
            diag = diagnose(matches, receipt)
            text = format_explanation(diag)
            result = format_explanation_json(diag)
            json.dumps(result)
            check(
                f"{display_name}: status={result['status']}, confidence={result['confidence']}%",
                isinstance(text, str)
                and len(text) > 50
                and (display_name in text or display_name.lower() in text.lower())
                and result["status"] in ("match_found", "no_match", "clean_match"),
            )
    finally:
        if original_key is not None:
            os.environ["VISION_AGENT_API_KEY"] = original_key

    print(f"\n{LINE * 62}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print(f"  Phase 6: COMPLETE {PASS}")
    else:
        print(f"  Phase 6: {failed} FAILED - fix before proceeding")
    print(f"{LINE * 62}")


if __name__ == "__main__":
    main()

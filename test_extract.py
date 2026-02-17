"""
test_extract.py - Phase 2 Extraction Module Tests

Tests the extraction module against all 6 test receipts,
flexible filename matching, error handling, and data properties.

Usage: python test_extract.py

Requires: No API key needed (uses mock extraction).
"""

from __future__ import annotations

import os
import sys
from typing import Any

# Ensure we can import from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extract import _extract_mock, extract_receipt
from models import ReceiptData


def main() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    passed = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal passed, failed
        if condition:
            print(f"    ✓ {name}")
            passed += 1
        else:
            print(f"    ✗ {name}")
            failed += 1

    def nearly_equal(a: float, b: float, tol: float = 1e-9) -> bool:
        return abs(a - b) <= tol

    def call_router_without_api_key(path: str) -> ReceiptData:
        original_key = os.environ.pop("VISION_AGENT_API_KEY", None)
        try:
            return extract_receipt(path)
        finally:
            if original_key is not None:
                os.environ["VISION_AGENT_API_KEY"] = original_key

    print("══════════════════════════════════════════")
    print("  Phase 2: Extraction Module Tests")
    print("══════════════════════════════════════════")

    # Category 1: Mock Extraction - All 6 Test Receipts
    print("\n  Mock Extraction — Standard Filenames:")
    test_cases: list[dict[str, Any]] = [
        {
            "id": "receipt_01",
            "file": "test_data/receipts/receipt_01_clean_match.png",
            "expected_vendor": "Amazon.com",
            "expected_total": 89.97,
            "expected_date": "2026-01-10",
            "expected_confidence": 0.98,
            "expected_has_tip": False,
            "expected_has_tax": True,
        },
        {
            "id": "receipt_02",
            "file": "test_data/receipts/receipt_02_vendor_mismatch.png",
            "expected_vendor": "El Agave Mexican Restaurant",
            "expected_total": 47.50,
            "expected_date": "2026-01-12",
            "expected_confidence": 0.95,
            "expected_has_tip": True,
            "expected_has_tax": True,
        },
        {
            "id": "receipt_03",
            "file": "test_data/receipts/receipt_03_tip_tax_variance.png",
            "expected_vendor": "Starbucks",
            "expected_total": 5.25,
            "expected_date": "2026-01-14",
            "expected_confidence": 0.97,
            "expected_has_tip": False,
            "expected_has_tax": True,
        },
        {
            "id": "receipt_04",
            "file": "test_data/receipts/receipt_04_settlement_delay.png",
            "expected_vendor": "Home Depot",
            "expected_total": 234.67,
            "expected_date": "2026-01-15",
            "expected_confidence": 0.96,
            "expected_has_tip": False,
            "expected_has_tax": True,
        },
        {
            "id": "receipt_05",
            "file": "test_data/receipts/receipt_05_combined_mismatch.png",
            "expected_vendor": "Fastenal",
            "expected_total": 178.23,
            "expected_date": "2026-01-18",
            "expected_confidence": 0.72,
            "expected_has_tip": False,
            "expected_has_tax": True,
        },
        {
            "id": "receipt_06",
            "file": "test_data/receipts/receipt_06_no_match.png",
            "expected_vendor": "Bob's Local Hardware",
            "expected_total": 45.00,
            "expected_date": "2026-01-22",
            "expected_confidence": 0.93,
            "expected_has_tip": False,
            "expected_has_tax": True,
        },
    ]

    for case in test_cases:
        receipt = _extract_mock(case["file"])
        ok = (
            isinstance(receipt, ReceiptData)
            and receipt.vendor == case["expected_vendor"]
            and nearly_equal(receipt.total, case["expected_total"])
            and receipt.date == case["expected_date"]
            and nearly_equal(receipt.confidence, case["expected_confidence"])
            and receipt.has_tip is case["expected_has_tip"]
            and receipt.has_tax is case["expected_has_tax"]
            and isinstance(receipt.chunk_ids, list)
            and len(receipt.chunk_ids) > 0
            and isinstance(receipt.raw_text, str)
            and len(receipt.raw_text.strip()) > 0
        )
        check(
            f"{case['id']}: vendor='{receipt.vendor}', total=${receipt.total:.2f}",
            ok,
        )

    # Category 2: Mock Extraction - Flexible Filename Matching
    print("\n  Mock Extraction — Flexible Matching:")
    flexible_names = [
        "receipt_02.png",
        "vendor_mismatch.png",
        "agave_test.png",
        "test_receipt_02_vendor_mismatch.jpg",
    ]
    for name in flexible_names:
        receipt = _extract_mock(name)
        check(
            f"'{name}' matches El Agave",
            receipt.vendor == "El Agave Mexican Restaurant"
            and nearly_equal(receipt.total, 47.50)
            and receipt.date == "2026-01-12",
        )

    # Category 3: Mock Extraction - Unknown Filename
    print("\n  Mock Extraction — Unknown Filename:")
    unknown = _extract_mock("random_unknown_file.png")
    check("Unknown file returns low confidence", unknown.confidence <= 0.5)
    check("Unknown file returns $0.00 total", nearly_equal(unknown.total, 0.0))

    # Category 4: Router Function - Mock Path (no API key)
    print("\n  Router — Mock Path:")
    routed = call_router_without_api_key("test_data/receipts/receipt_02_vendor_mismatch.png")
    check("Routes to mock when no API key", "Server: Maria" in (routed.raw_text or ""))
    check(
        "Returns correct data through router",
        routed.vendor == "El Agave Mexican Restaurant"
        and nearly_equal(routed.total, 47.50)
        and routed.date == "2026-01-12",
    )

    # Category 5: Router Function - Error Handling
    print("\n  Router — Error Handling:")
    missing_raised = False
    try:
        call_router_without_api_key("nonexistent_receipt.png")
    except FileNotFoundError:
        missing_raised = True
    check("FileNotFoundError for missing file", missing_raised)

    empty_path_handled = False
    try:
        result = call_router_without_api_key("")
        empty_path_handled = (
            isinstance(result, ReceiptData)
            and result.vendor == "EXTRACTION_ERROR"
            and nearly_equal(result.confidence, 0.1)
        )
    except (FileNotFoundError, ValueError):
        empty_path_handled = True
    check("Error for empty path", empty_path_handled)

    # Category 6: ReceiptData Properties
    print("\n  ReceiptData Properties:")
    r02 = call_router_without_api_key("test_data/receipts/receipt_02_vendor_mismatch.png")
    r05 = call_router_without_api_key("test_data/receipts/receipt_05_combined_mismatch.png")
    r06 = call_router_without_api_key("test_data/receipts/receipt_06_no_match.png")

    check("has_tip works (receipt_02)", r02.has_tip is True)
    check("has_tax works (receipt_02)", r02.has_tax is True)
    check("is_low_confidence false (receipt_02)", r02.is_low_confidence is False)
    check("tax_tip_total correct (receipt_02)", nearly_equal(r02.tax_tip_total, 10.50))
    check("is_low_confidence works (receipt_05)", r05.is_low_confidence is True)
    check("partial grounding count is 1 (receipt_05)", len(r05.chunk_ids) == 1)
    check("has_tip false (receipt_06)", r06.has_tip is False)

    # Category 7: Serialization
    print("\n  Serialization:")
    receipt = call_router_without_api_key("test_data/receipts/receipt_02_vendor_mismatch.png")
    json_str = receipt.model_dump_json()
    check("JSON contains vendor text", "El Agave" in json_str)
    restored = ReceiptData.model_validate_json(json_str)
    check(
        "JSON roundtrip preserves data",
        restored.vendor == receipt.vendor and nearly_equal(restored.total, receipt.total),
    )

    print(f"\n{'═' * 42}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print("  Phase 2: COMPLETE ✓")
    else:
        print(f"  Phase 2: {failed} FAILED — fix before proceeding")
    print(f"{'═' * 42}")


if __name__ == "__main__":
    main()

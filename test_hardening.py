"""
test_hardening.py - Phase 8 Hardening Regression Tests.

Comprehensive regression suite for:
- defensive input validation
- structured logging sanity
- grounding utilities
- confidence calibration
- edge-case receipt scenarios
- original receipt regression coverage

Usage:
    python test_hardening.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from diagnose import _calibrate_confidence, diagnose
from explain import format_explanation, format_explanation_json
from extract import extract_receipt
from grounding import GroundingInfo, extract_grounding, grounding_coverage, has_grounding
from logging_config import get_logger, setup_logging
from match import find_matches, score_amount, score_date, score_vendor
from models import Diagnosis, MismatchType, ReceiptData
from normalize import normalize_amount, normalize_date, normalize_vendor


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
    print("  Phase 8: Hardening Regression Tests")
    print(LINE * 62)

    base_dir = Path(__file__).resolve().parent
    main_csv = base_dir / "test_data" / "transactions.csv"
    edge_csv = base_dir / "test_data" / "transactions_edge_cases.csv"

    original_key = os.environ.pop("VISION_AGENT_API_KEY", None)
    try:
        # ----------------------------------------------------------
        # Category 1: Input validation - None and empty inputs
        # ----------------------------------------------------------
        print("\n  Input Validation - None/Empty:")
        check("normalize_vendor(None) -> ''", normalize_vendor(None) == "")
        check("normalize_date(None) -> ''", normalize_date(None) == "")
        check("normalize_amount(None) -> 0.0", normalize_amount(None) == 0.0)

        check("normalize_vendor(12345) -> '12345'", normalize_vendor(12345) == "12345")
        check("normalize_amount('not a number') -> 0.0", normalize_amount("not a number") == 0.0)
        check("normalize_date(12345) -> ''", normalize_date(12345) == "")

        vendor_score, _ = score_vendor("", "")
        check("score_vendor('', '') -> 0.0", vendor_score == 0.0)

        amount_score, _, _, _ = score_amount(0, 0)
        check("score_amount(0, 0) -> 0.0", amount_score == 0.0)

        date_score, days_apart, _ = score_date("", "")
        check("score_date('', '') score=0.0", date_score == 0.0)
        check("score_date('', '') days=999", days_apart == 999)

        check("find_matches(None, DataFrame()) -> []", find_matches(None, pd.DataFrame()) == [])
        check(
            "find_matches(valid_receipt, None) -> []",
            find_matches(ReceiptData(vendor="X", total=1.0), None) == [],
        )

        diag_none_matches = diagnose(None)
        check("diagnose(None) -> NO_MATCH", MismatchType.NO_MATCH in diag_none_matches.labels)

        diag_none_entries = diagnose([None, None])
        check("diagnose([None, None]) -> NO_MATCH", MismatchType.NO_MATCH in diag_none_entries.labels)

        text_none = format_explanation(None)
        check("format_explanation(None) returns string", isinstance(text_none, str) and len(text_none) > 0)

        json_none = format_explanation_json(None)
        check("format_explanation_json(None) returns dict", isinstance(json_none, dict))
        check("format_explanation_json(None) status=error", json_none.get("status") == "error")

        # ----------------------------------------------------------
        # Category 2: Input validation - bad types
        # ----------------------------------------------------------
        print("\n  Input Validation - Bad Types:")
        bad_df = pd.DataFrame({"wrong": [1], "columns": [2], "here": [3]})
        receipt = ReceiptData(vendor="Test", total=100.0, date="2026-01-15")
        bad_matches = find_matches(receipt, bad_df)
        check("Wrong DataFrame columns -> empty matches", bad_matches == [])

        nan_df = pd.DataFrame(
            {
                "merchant": ["Amazon", None, "Target"],
                "amount": [89.97, float("nan"), 45.00],
                "date": ["2026-01-10", "2026-01-11", None],
            }
        )
        nan_matches = find_matches(receipt, nan_df)
        check("NaN values don't crash find_matches", isinstance(nan_matches, list))

        mixed_df = pd.DataFrame(
            {
                "merchant": ["Amazon"],
                "amount": ["$89.97"],
                "date": ["2026-01-10"],
            }
        )
        mixed_matches = find_matches(receipt, mixed_df)
        check("Mixed amount types don't crash find_matches", isinstance(mixed_matches, list))

        check(
            "find_matches rejects non-DataFrame input",
            find_matches(receipt, {"merchant": ["Amazon"]}) == [],  # type: ignore[arg-type]
        )

        # ----------------------------------------------------------
        # Category 3: Unicode handling
        # ----------------------------------------------------------
        print("\n  Unicode Handling:")
        unicode_vendor = normalize_vendor("Café Résistance")
        check("Café -> cafe", "cafe" in unicode_vendor)
        check("Señor Taco's normalizes", normalize_vendor("Señor Taco's") != "")
        check("Japanese vendor survives normalization", normalize_vendor("日本料理") != "")
        check("Über Eats normalizes", normalize_vendor("Über Eats") != "")

        # ----------------------------------------------------------
        # Category 4: Edge-case receipts pipeline
        # ----------------------------------------------------------
        print("\n  Edge-Case Receipts:")
        df_edge = pd.read_csv(edge_csv)

        r07 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_07_no_date.png"))
        d07 = diagnose(find_matches(r07, df_edge), r07)
        t07 = format_explanation(d07)
        check("Receipt 07: no date extracted", r07.date is None)
        check("Receipt 07: diagnosis object produced", isinstance(d07, Diagnosis))
        check("Receipt 07: text explanation produced", isinstance(t07, str) and len(t07) > 0)

        r08 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_08_blurry.png"))
        d08 = diagnose(find_matches(r08, df_edge), r08)
        check("Receipt 08: low confidence (<0.5)", r08.confidence < 0.5)
        check(
            "Receipt 08: low confidence warning in evidence",
            any("confidence" in ev.lower() for ev in d08.evidence),
        )

        r09 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_09_voided.png"))
        d09 = diagnose(find_matches(r09, df_edge), r09)
        check("Receipt 09: voided total is 0.0", r09.total == 0.0)
        check("Receipt 09: diagnosis object produced", isinstance(d09, Diagnosis))

        r10 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_10_unicode.png"))
        d10 = diagnose(find_matches(r10, df_edge), r10)
        check("Receipt 10: unicode vendor present", "Café" in r10.vendor or "cafe" in r10.vendor.lower())
        check("Receipt 10: diagnosis object produced", isinstance(d10, Diagnosis))

        r11 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_11_duplicate.png"))
        d11 = diagnose(find_matches(r11, df_edge), r11)
        check("Receipt 11: diagnosis object produced", isinstance(d11, Diagnosis))

        # ----------------------------------------------------------
        # Category 5: Grounding utilities
        # ----------------------------------------------------------
        print("\n  Grounding Utilities:")
        r02 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_02_vendor_mismatch.png"))
        check("has_grounding detects chunk IDs", has_grounding(r02) is True)

        g02 = extract_grounding(r02)
        check("extract_grounding returns list", isinstance(g02, list))
        check("extract_grounding returns >=2 entries", len(g02) >= 2)

        coverage_02 = grounding_coverage(r02)
        check("grounding_coverage in [0, 1]", 0.0 <= coverage_02 <= 1.0)

        serializable = True
        for grounding in g02:
            if not isinstance(grounding, GroundingInfo):
                serializable = False
                break
            payload = grounding.to_dict()
            if not {"field", "value", "chunk_ids", "confidence", "bounding_box"}.issubset(
                set(payload.keys())
            ):
                serializable = False
                break
            try:
                json.dumps(payload)
            except Exception:
                serializable = False
                break
        check("GroundingInfo serializes to JSON", serializable)

        check("Blurry receipt has no grounding", has_grounding(r08) is False)
        check("Blurry receipt coverage is 0.0", grounding_coverage(r08) == 0.0)

        diag_ground = diagnose(find_matches(r02, pd.read_csv(main_csv)), r02)
        json_ground = format_explanation_json(diag_ground)
        has_grounding_fields = (
            json_ground.get("receipt") is not None
            and "grounding_coverage" in json_ground["receipt"]
            and "grounding" in json_ground["receipt"]
        )
        check("JSON output includes grounding fields", has_grounding_fields)

        # ----------------------------------------------------------
        # Category 6: Confidence calibration
        # ----------------------------------------------------------
        print("\n  Confidence Calibration:")
        conf_normal = _calibrate_confidence(85.0, None, 1, [])
        check("Normal case remains near baseline", 83.0 <= conf_normal <= 100.0)

        low_receipt = ReceiptData(vendor="X", total=100.0, confidence=0.5)
        conf_low = _calibrate_confidence(85.0, low_receipt, 1, [MismatchType.VENDOR_MISMATCH])
        check("Low extraction confidence reduces score", conf_low < 85.0)

        conf_ambiguous = _calibrate_confidence(85.0, None, 3, [MismatchType.VENDOR_MISMATCH])
        check("Multiple candidates reduce score", conf_ambiguous < 85.0)

        conf_compound = _calibrate_confidence(
            85.0,
            None,
            1,
            [
                MismatchType.VENDOR_MISMATCH,
                MismatchType.SETTLEMENT_DELAY,
                MismatchType.TIP_TAX_VARIANCE,
            ],
        )
        check("Compound labels reduce score", conf_compound < 85.0)

        check(
            "Calibration lower bound respected",
            _calibrate_confidence(0.0, low_receipt, 5, [MismatchType.VENDOR_MISMATCH] * 3) >= 0.0,
        )
        check(
            "Calibration upper bound respected",
            _calibrate_confidence(100.0, None, 1, []) <= 100.0,
        )

        # ----------------------------------------------------------
        # Category 7: Regression for original 6 receipts
        # ----------------------------------------------------------
        print("\n  Regression - Original 6 Receipts:")
        df_main = pd.read_csv(main_csv)

        r01 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_01_clean_match.png"))
        d01 = diagnose(find_matches(r01, df_main), r01)
        check("Receipt 01 remains clean match", d01.is_clean_match or d01.labels == [])

        r02b = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_02_vendor_mismatch.png"))
        d02b = diagnose(find_matches(r02b, df_main), r02b)
        check("Receipt 02 remains vendor mismatch", MismatchType.VENDOR_MISMATCH in d02b.labels)

        r03 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_03_tip_tax_variance.png"))
        d03 = diagnose(find_matches(r03, df_main), r03)
        check(
            "Receipt 03 remains partial or tip/tax",
            MismatchType.PARTIAL_MATCH in d03.labels or MismatchType.TIP_TAX_VARIANCE in d03.labels,
        )

        r04 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_04_settlement_delay.png"))
        d04 = diagnose(find_matches(r04, df_main), r04)
        check("Receipt 04 remains settlement delay", MismatchType.SETTLEMENT_DELAY in d04.labels)

        r05 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_05_combined_mismatch.png"))
        d05 = diagnose(find_matches(r05, df_main), r05)
        check("Receipt 05 remains compound (2+ labels)", len(d05.labels) >= 2)

        r06 = extract_receipt(str(base_dir / "test_data" / "receipts" / "receipt_06_no_match.png"))
        d06 = diagnose(find_matches(r06, df_main), r06)
        check("Receipt 06 remains NO_MATCH", MismatchType.NO_MATCH in d06.labels)

        # ----------------------------------------------------------
        # Category 8: Logging module
        # ----------------------------------------------------------
        print("\n  Logging Module:")
        setup_ok = True
        try:
            setup_logging(level=logging.DEBUG)
            setup_logging(level=logging.INFO, json_format=True)
            setup_logging(level=logging.INFO, json_format=False)
        except Exception:
            setup_ok = False
        check("setup_logging works", setup_ok)

        logger = get_logger("test-hardening")
        logger_ok = isinstance(logger, logging.Logger)
        try:
            logger.info("test message")
        except Exception:
            logger_ok = False
        check("get_logger returns valid logger", logger_ok)
    finally:
        if original_key is not None:
            os.environ["VISION_AGENT_API_KEY"] = original_key

    print(f"\n{LINE * 62}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print(f"  Phase 8: COMPLETE {PASS}")
    else:
        print(f"  Phase 8: {failed} FAILED - fix before proceeding")
    print(f"{LINE * 62}")


if __name__ == "__main__":
    main()


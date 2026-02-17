"""
verify_phase1.py - Phase 1 Completion Checker

Verifies that all Phase 1 deliverables are correctly set up:
- Project structure (all files and directories exist)
- Configuration files (.env, .gitignore, requirements.txt)
- Pydantic models (all 5 models instantiate and validate correctly)
- Test data (CSV loads with correct shape, receipt files exist)
- Module placeholders (all imports resolve, stubs raise NotImplementedError)

Usage: python verify_phase1.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _unicode_enabled() -> bool:
    try:
        "✓✗═".encode(sys.stdout.encoding or "utf-8")
        return True
    except Exception:
        return False


UNICODE = _unicode_enabled()
PASS = "✓" if UNICODE else "[OK]"
FAIL = "✗" if UNICODE else "[FAIL]"
LINE = "═" * 42 if UNICODE else "=" * 42


class Verifier:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    @property
    def total(self) -> int:
        return self.passed + self.failed

    def check(self, name: str, condition: bool, error: str | None = None) -> None:
        if condition:
            print(f"    {PASS} {name}")
            self.passed += 1
            return
        print(f"    {FAIL} {name}")
        if error:
            print(f"      -> {error}")
        self.failed += 1


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252")


def _import_module(name: str) -> tuple[ModuleType | None, str | None]:
    try:
        module = importlib.import_module(name)
        return module, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _expects_not_implemented(func: Any, *args: Any, **kwargs: Any) -> tuple[bool, str | None]:
    try:
        func(*args, **kwargs)
        return False, "Expected NotImplementedError but function returned successfully"
    except NotImplementedError:
        return True, None
    except Exception as exc:
        return False, f"Expected NotImplementedError, got {type(exc).__name__}: {exc}"


def verify_file_system(v: Verifier) -> None:
    print("\n  File System:")
    required_paths = [
        ".env",
        ".gitignore",
        "requirements.txt",
        "README.md",
        "models.py",
        "extract.py",
        "normalize.py",
        "match.py",
        "diagnose.py",
        "explain.py",
        "main.py",
        "test_data/transactions.csv",
        "test_data/receipts/receipt_01_clean_match.png",
        "test_data/receipts/receipt_02_vendor_mismatch.png",
        "test_data/receipts/receipt_03_tip_tax_variance.png",
        "test_data/receipts/receipt_04_settlement_delay.png",
        "test_data/receipts/receipt_05_combined_mismatch.png",
        "test_data/receipts/receipt_06_no_match.png",
    ]
    for rel in required_paths:
        path = ROOT / rel
        v.check(f"{rel} exists", path.exists())


def verify_configuration(v: Verifier) -> None:
    print("\n  Configuration:")
    env_text = _read_text(ROOT / ".env")
    requirements_text = _read_text(ROOT / "requirements.txt").lower()
    gitignore_text = _read_text(ROOT / ".gitignore").lower()

    v.check(
        ".env has API key placeholder",
        "VISION_AGENT_API_KEY" in env_text,
    )
    v.check(
        "requirements include pydantic, pandas, rapidfuzz",
        all(dep in requirements_text for dep in ("pydantic", "pandas", "rapidfuzz")),
    )
    v.check(
        ".gitignore includes .env and pycache rules",
        ".env" in gitignore_text and ("__pycache__" in gitignore_text or "pycache" in gitignore_text),
    )


def verify_models(v: Verifier) -> dict[str, Any]:
    print("\n  Models:")
    models, err = _import_module("models")
    if models is None:
        checks = [
            "MismatchType has 5 variants",
            "ReceiptData minimal instantiation works",
            "ReceiptData full instantiation works",
            "ReceiptData.has_tip works",
            "ReceiptData.is_low_confidence works",
            "Transaction instantiation works",
            "MatchCandidate nested Transaction works",
            "Diagnosis helper properties work",
            "Diagnosis.label_summary works for each type",
            "Validation rejects negative total",
            "Validation rejects confidence > 1.0",
            "JSON serialization roundtrip works",
        ]
        for label in checks:
            v.check(label, False, err)
        return {}

    MismatchType = models.MismatchType
    ReceiptData = models.ReceiptData
    Transaction = models.Transaction
    MatchCandidate = models.MatchCandidate
    Diagnosis = models.Diagnosis

    v.check("MismatchType has 5 variants", len(MismatchType) == 5)

    receipt_min = ReceiptData(vendor="Starbucks", total=5.25)
    v.check(
        "ReceiptData minimal instantiation works",
        receipt_min.vendor == "Starbucks" and receipt_min.total == 5.25,
    )

    receipt_full = ReceiptData(
        vendor="El Agave Mexican Restaurant",
        total=47.50,
        date="2026-01-12",
        tax=3.50,
        tip=7.00,
        subtotal=37.00,
        confidence=0.95,
        chunk_ids=["chunk_010"],
    )
    v.check(
        "ReceiptData full instantiation works",
        receipt_full.tax == 3.50 and receipt_full.tip == 7.00 and receipt_full.subtotal == 37.00,
    )
    v.check("ReceiptData.has_tip works", receipt_full.has_tip is True)
    receipt_low = ReceiptData(vendor="Fastenal", total=178.23, confidence=0.65)
    v.check("ReceiptData.is_low_confidence works", receipt_low.is_low_confidence is True)

    txn = Transaction(
        merchant="ELAGAVE*1847 CHATT TN",
        amount=47.50,
        date="2026-01-12",
        description="Restaurant",
        transaction_id="TXN002",
    )
    v.check("Transaction instantiation works", txn.merchant == "ELAGAVE*1847 CHATT TN")

    candidate = MatchCandidate(
        transaction=txn,
        vendor_score=60.9,
        amount_diff=0.0,
        amount_pct_diff=0.0,
        date_diff=0,
        overall_confidence=84.3,
        evidence=[
            "Vendor names differ: 'el agave mexican' vs 'elagave' (score: 60.9)",
            "Exact amount match: $47.50",
            "Same date: 2026-01-12",
        ],
    )
    v.check(
        "MatchCandidate nested Transaction works",
        candidate.transaction.transaction_id == "TXN002",
    )

    diagnosis = Diagnosis(
        labels=[MismatchType.VENDOR_MISMATCH],
        confidence=84.3,
        evidence=candidate.evidence,
        top_match=candidate,
        receipt=receipt_full,
    )
    v.check(
        "Diagnosis helper properties work",
        diagnosis.is_match is True and diagnosis.is_clean_match is False and diagnosis.is_compound is False,
    )

    expected_summaries = {
        MismatchType.VENDOR_MISMATCH: "Vendor Descriptor Mismatch",
        MismatchType.SETTLEMENT_DELAY: "Settlement Delay",
        MismatchType.TIP_TAX_VARIANCE: "Tip/Tax Variance",
        MismatchType.PARTIAL_MATCH: "Partial Match",
        MismatchType.NO_MATCH: "No Match Found",
    }
    label_ok = True
    for label, expected in expected_summaries.items():
        tmp = Diagnosis(labels=[label], top_match=candidate if label != MismatchType.NO_MATCH else None)
        if tmp.label_summary != expected:
            label_ok = False
            break
    v.check("Diagnosis.label_summary works for each type", label_ok)

    negative_total_rejected = False
    try:
        ReceiptData(vendor="Bad Data", total=-1.0)
    except Exception:
        negative_total_rejected = True
    v.check("Validation rejects negative total", negative_total_rejected)

    confidence_rejected = False
    try:
        ReceiptData(vendor="Bad Data", total=10.0, confidence=1.5)
    except Exception:
        confidence_rejected = True
    v.check("Validation rejects confidence > 1.0", confidence_rejected)

    roundtrip_ok = False
    try:
        payload = diagnosis.model_dump_json()
        restored = Diagnosis.model_validate_json(payload)
        roundtrip_ok = restored.top_match is not None and restored.top_match.transaction.merchant == txn.merchant
    except Exception:
        roundtrip_ok = False
    v.check("JSON serialization roundtrip works", roundtrip_ok)

    return {
        "MismatchType": MismatchType,
        "ReceiptData": ReceiptData,
        "Transaction": Transaction,
        "MatchCandidate": MatchCandidate,
        "Diagnosis": Diagnosis,
        "receipt": receipt_full,
        "txn": txn,
        "candidate": candidate,
        "diagnosis": diagnosis,
    }


def verify_test_data(v: Verifier) -> None:
    print("\n  Test Data:")
    csv_path = ROOT / "test_data/transactions.csv"
    df = pd.read_csv(csv_path)
    v.check("transactions.csv has exactly 10 rows", len(df) == 10)

    required_cols = {"merchant", "amount", "date", "description", "transaction_id"}
    v.check("CSV has required columns", required_cols.issubset(set(df.columns)))

    receipt_files = [
        "receipt_01_clean_match.png",
        "receipt_02_vendor_mismatch.png",
        "receipt_03_tip_tax_variance.png",
        "receipt_04_settlement_delay.png",
        "receipt_05_combined_mismatch.png",
        "receipt_06_no_match.png",
    ]
    receipts_ok = all((ROOT / "test_data/receipts" / name).exists() for name in receipt_files)
    v.check("All 6 receipt placeholder files exist", receipts_ok)

    v.check("expected_results.md exists", (ROOT / "test_data/expected_results.md").exists())


def verify_module_placeholders(v: Verifier, model_ctx: dict[str, Any]) -> None:
    print("\n  Module Placeholders:")

    sample_receipt = model_ctx.get("receipt")
    sample_candidate = model_ctx.get("candidate")
    sample_diagnosis = model_ctx.get("diagnosis")

    if sample_receipt is None:
        models, err = _import_module("models")
        if models is not None:
            sample_receipt = models.ReceiptData(vendor="Sample", total=1.0)
            sample_txn = models.Transaction(merchant="Sample", amount=1.0, date="2026-01-01")
            sample_candidate = models.MatchCandidate(
                transaction=sample_txn,
                vendor_score=100.0,
                amount_diff=0.0,
                amount_pct_diff=0.0,
                date_diff=0,
                overall_confidence=100.0,
            )
            sample_diagnosis = models.Diagnosis(top_match=sample_candidate, receipt=sample_receipt)

    module_specs = {
        "extract": {
            "functions": {
                "extract_receipt": ("test_data/receipts/receipt_01_clean_match.png",),
                "_extract_with_ade": ("test_data/receipts/receipt_01_clean_match.png", "fake_api_key"),
                "_extract_mock": ("test_data/receipts/receipt_01_clean_match.png",),
            }
        },
        "normalize": {
            "functions": {
                "normalize_vendor": ("AMZN MKTP US*2K4RF83J0",),
                "normalize_date": ("2026-01-10",),
                "normalize_amount": ("$47.50",),
                "normalize_receipt": ("Amazon.com", "2026-01-10", "$89.97"),
                "normalize_transaction": ("AMZN MKTP US*2K4RF83J0", "2026-01-10", "89.97"),
            }
        },
        "match": {
            "functions": {
                "score_vendor": ("amazon", "amzn mktp"),
                "score_amount": (47.50, 50.00),
                "score_date": ("2026-01-10", "2026-01-12"),
                "find_matches": (
                    sample_receipt,
                    pd.DataFrame(columns=["merchant", "amount", "date", "description", "transaction_id"]),
                ),
            }
        },
        "diagnose": {
            "functions": {
                "diagnose": ([sample_candidate] if sample_candidate is not None else [], sample_receipt),
            }
        },
        "explain": {
            "functions": {
                "format_explanation": (sample_diagnosis,),
                "format_explanation_json": (sample_diagnosis,),
            }
        },
    }

    for module_name, spec in module_specs.items():
        module, err = _import_module(module_name)
        v.check(f"{module_name}.py imports cleanly", module is not None, err)

        if module is None:
            v.check(f"{module_name}.py key functions exist", False, "Module import failed")
            v.check(f"{module_name}.py stubs raise NotImplementedError", False, "Module import failed")
            continue

        all_exist = all(hasattr(module, fn_name) for fn_name in spec["functions"])
        v.check(f"{module_name}.py key functions exist", all_exist)

        all_raise = True
        first_error: str | None = None
        for fn_name, args in spec["functions"].items():
            if not hasattr(module, fn_name):
                all_raise = False
                first_error = f"Missing function: {fn_name}"
                break
            ok, call_err = _expects_not_implemented(getattr(module, fn_name), *args)
            if not ok:
                all_raise = False
                first_error = f"{fn_name}: {call_err}"
                break
        v.check(f"{module_name}.py stubs raise NotImplementedError", all_raise, first_error)


def main() -> int:
    print(LINE)
    print("  Phase 1 Verification")
    print(LINE)

    verifier = Verifier()

    verify_file_system(verifier)
    verify_configuration(verifier)
    model_ctx = verify_models(verifier)
    verify_test_data(verifier)
    verify_module_placeholders(verifier, model_ctx)

    print(f"\n{LINE}")
    if verifier.failed == 0:
        print(f"  Results: {verifier.passed}/{verifier.total} passed")
        print(f"  Phase 1: COMPLETE {PASS}")
        print(LINE)
        return 0

    print(f"  Results: {verifier.passed}/{verifier.total} passed, {verifier.failed} FAILED")
    print(f"  Phase 1: INCOMPLETE - fix items marked {FAIL}")
    print(LINE)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

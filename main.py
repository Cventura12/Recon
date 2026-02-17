"""
main.py - CLI orchestration for the diagnostic agent.

This module is orchestration-only:
1. extract
2. match
3. diagnose
4. explain
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import pandas as pd

from diagnose import diagnose
from explain import format_explanation, format_explanation_json
from extract import extract_receipt
from logging_config import get_logger, setup_logging
from match import find_matches

logger = get_logger("diagnostic-agent")

REQUIRED_COLUMNS = ["merchant", "amount", "date"]
OPTIONAL_COLUMNS = ["description", "transaction_id"]


def _configure_output_symbols() -> tuple[str, str]:
    """Configure stdout encoding and return safe line/fail symbols."""
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        "═✗".encode(sys.stdout.encoding or "utf-8")
        return "═", "✗"
    except Exception:
        return "=", "X"


BOX_CHAR, FAIL_CHAR = _configure_output_symbols()


def load_transactions(csv_path: str) -> pd.DataFrame:
    """Load and validate a bank transactions CSV file."""
    if csv_path is None:
        raise ValueError("csv_path cannot be None")

    csv_path = str(csv_path).strip()
    if not csv_path:
        raise ValueError("csv_path cannot be empty")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Transactions CSV not found: {csv_path}\n"
            "Provide a valid CSV path with --csv"
        )

    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        logger.warning(
            "csv_encoding_warning | path=%s | reason='utf-8 decode failed' | fallback=latin-1",
            csv_path,
        )
        df = pd.read_csv(csv_path, encoding="latin-1")
    except Exception as exc:
        raise ValueError(f"Failed to read CSV '{csv_path}': {exc}") from exc

    if df is None:
        raise ValueError(f"Failed to read CSV '{csv_path}' - no DataFrame returned")

    # Normalize column names and remove fully empty rows.
    df.columns = [str(col).strip().lower() for col in df.columns]
    df = df.dropna(how="all").copy()

    if df.empty:
        raise ValueError(f"Transactions CSV is empty: {csv_path}")

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            f"Transactions CSV missing required columns: {missing}\n"
            f"Required: {REQUIRED_COLUMNS}\n"
            f"Found: {list(df.columns)}\n"
            "Make sure your CSV has 'merchant', 'amount', and 'date' columns."
        )

    # Ensure optional columns exist for downstream access.
    for optional in OPTIONAL_COLUMNS:
        if optional not in df.columns:
            df[optional] = None

    # Clean merchant/date strings for stability.
    df["merchant"] = df["merchant"].astype(str).str.strip()
    df["date"] = df["date"].astype(str).str.strip()

    # Coerce amount safely while preserving pipeline continuity.
    amount_clean = (
        df["amount"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    amount_numeric = pd.to_numeric(amount_clean, errors="coerce")
    invalid_amounts = int(amount_numeric.isna().sum())
    if invalid_amounts > 0:
        logger.warning(
            "csv_amount_warning | invalid_amount_rows=%s | fallback='set to 0.0'",
            invalid_amounts,
        )
    df["amount"] = amount_numeric.fillna(0.0).astype(float)

    logger.info(
        "csv_loaded | path=%s | rows=%s | columns=%s",
        csv_path,
        len(df),
        list(df.columns),
    )

    try:
        dates = pd.to_datetime(df["date"], errors="coerce")
        valid_dates = dates.dropna()
        if not valid_dates.empty:
            logger.info(
                "csv_date_range | min=%s | max=%s",
                valid_dates.min().strftime("%Y-%m-%d"),
                valid_dates.max().strftime("%Y-%m-%d"),
            )
    except Exception as exc:
        logger.debug(
            "csv_date_range_warning | error=%s | fallback='skip date range logging'",
            exc,
        )

    return df


def run_pipeline(
    receipt_path: str,
    csv_path: str,
    transactions_df: pd.DataFrame | None = None,
) -> str:
    """Run the full diagnostic pipeline for one receipt."""
    pipeline_start = time.time()

    logger.info("%s", "─" * 50)
    logger.info("pipeline_start | receipt_file=%s", os.path.basename(str(receipt_path)))
    logger.info("%s", "─" * 50)

    # Stage 1: extract.
    stage_start = time.time()
    logger.info("pipeline_stage | stage=1/4 | name=extract | status=start")
    receipt = extract_receipt(receipt_path)
    extract_time = time.time() - stage_start
    logger.info(
        "pipeline_stage | stage=1/4 | name=extract | status=complete | vendor=%r | total=%.2f | date=%s | confidence=%.0f%% | duration_s=%.2f",
        receipt.vendor,
        receipt.total,
        receipt.date,
        receipt.confidence * 100.0,
        extract_time,
    )

    # Stage 2: match.
    stage_start = time.time()
    logger.info("pipeline_stage | stage=2/4 | name=match | status=start")
    if transactions_df is None:
        transactions_df = load_transactions(csv_path)
    matches = find_matches(receipt, transactions_df)
    match_time = time.time() - stage_start
    logger.info(
        "pipeline_stage | stage=2/4 | name=match | status=complete | candidates=%s | duration_s=%.2f",
        len(matches),
        match_time,
    )

    # Stage 3: diagnose.
    stage_start = time.time()
    logger.info("pipeline_stage | stage=3/4 | name=diagnose | status=start")
    diagnosis = diagnose(matches, receipt)
    diagnose_time = time.time() - stage_start
    logger.info(
        "pipeline_stage | stage=3/4 | name=diagnose | status=complete | label_summary=%r | confidence=%.1f%% | duration_s=%.2f",
        diagnosis.label_summary,
        diagnosis.confidence,
        diagnose_time,
    )

    # Stage 4: explain.
    stage_start = time.time()
    logger.info("pipeline_stage | stage=4/4 | name=explain | status=start")
    explanation = format_explanation(diagnosis)
    diagnosis.explanation = explanation
    explain_time = time.time() - stage_start

    total_time = time.time() - pipeline_start
    logger.info(
        "pipeline_complete | total_duration_s=%.2f | extract_s=%.2f | match_s=%.2f | diagnose_s=%.2f | explain_s=%.2f",
        total_time,
        extract_time,
        match_time,
        diagnose_time,
        explain_time,
    )
    return explanation


def _print_summary_table(results: list[tuple[str, str, float, str]]) -> None:
    """Print a formatted summary table for batch mode results."""
    print(f"\n{BOX_CHAR * 60}")
    print(f"  SUMMARY - {len(results)} receipt(s) processed")
    print(f"{BOX_CHAR * 60}")
    print()
    print(f"  {'Receipt':<35} {'Diagnosis':<25} {'Conf':>5}")
    print(f"  {'─' * 35} {'─' * 25} {'─' * 5}")

    for filename, summary, confidence, _matched_merchant in results:
        short_name = filename[:33] + ".." if len(filename) > 35 else filename
        short_summary = summary[:23] + ".." if len(summary) > 25 else summary
        print(f"  {short_name:<35} {short_summary:<25} {confidence:>4.0f}%")

    print()
    print(f"{BOX_CHAR * 60}")


def run_all_test_receipts(csv_path: str) -> None:
    """Run the diagnostic pipeline on all files in test_data/receipts/."""
    transactions_df = load_transactions(csv_path)

    receipts_dir = Path("test_data/receipts")
    if not receipts_dir.is_dir():
        logger.error("batch_error | reason='receipts directory missing' | path=%s", receipts_dir)
        print(f"Error: Directory '{receipts_dir}' not found.")
        print("Make sure you're running from the project root directory.")
        return

    receipt_files = sorted(
        file.name
        for file in receipts_dir.iterdir()
        if file.is_file() and not file.name.startswith(".") and not file.name.startswith("_")
    )
    if not receipt_files:
        logger.warning("batch_warning | reason='no receipt files found' | path=%s", receipts_dir)
        print(f"No receipt files found in {receipts_dir}/")
        return

    logger.info("batch_start | receipt_count=%s | directory=%s", len(receipt_files), receipts_dir)
    results: list[tuple[str, str, float, str]] = []

    for index, filename in enumerate(receipt_files, start=1):
        receipt_path = str(receipts_dir / filename)
        print(f"\n{BOX_CHAR * 60}")
        print(f"  Receipt {index}/{len(receipt_files)}: {filename}")
        print(f"{BOX_CHAR * 60}")

        try:
            start = time.time()
            receipt = extract_receipt(receipt_path)
            matches = find_matches(receipt, transactions_df)
            diagnosis = diagnose(matches, receipt)
            explanation = format_explanation(diagnosis)
            diagnosis.explanation = explanation
            elapsed = time.time() - start

            print(explanation)
            logger.info(
                "batch_receipt_complete | file=%s | diagnosis=%r | confidence=%.1f%% | duration_s=%.2f",
                filename,
                diagnosis.label_summary,
                diagnosis.confidence,
                elapsed,
            )
            results.append(
                (
                    filename,
                    diagnosis.label_summary,
                    diagnosis.confidence,
                    diagnosis.top_match.transaction.merchant if diagnosis.top_match else "—",
                )
            )
        except Exception as exc:
            logger.error(
                "batch_receipt_error | file=%s | error_type=%s | error=%s",
                filename,
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            print(f"\n  {FAIL_CHAR} Error processing {filename}: {exc}\n")
            results.append((filename, "ERROR", 0.0, str(exc)[:40]))

    _print_summary_table(results)
    success_count = sum(1 for _, summary, _, _ in results if summary != "ERROR")
    error_count = len(results) - success_count
    logger.info("batch_complete | success=%s | failed=%s", success_count, error_count)


def main() -> None:
    """CLI entry point for the Diagnostic Agent."""
    parser = argparse.ArgumentParser(
        prog="diagnostic-agent",
        description=(
            "Diagnostic Agent for Accounting Exceptions\n"
            "Explains WHY accounting mismatches happen between "
            "receipts and bank transactions."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --receipt receipt.png --csv transactions.csv\n"
            "  %(prog)s --all --csv test_data/transactions.csv\n"
            "  %(prog)s --all --csv test_data/transactions.csv --verbose\n"
        ),
    )
    parser.add_argument(
        "--receipt",
        "-r",
        type=str,
        help="Path to a single receipt image file (.png, .jpg, .pdf)",
    )
    parser.add_argument(
        "--csv",
        "-c",
        type=str,
        required=True,
        help="Path to the bank transactions CSV file (required)",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Process all receipts in test_data/receipts/ directory",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (DEBUG-level) logging",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of formatted text (single receipt mode)",
    )
    parser.add_argument(
        "--log-json",
        action="store_true",
        help="Output logs as JSON lines (for production/log aggregation)",
    )

    args = parser.parse_args()
    setup_logging(
        level=logging.DEBUG if args.verbose else logging.INFO,
        json_format=args.log_json,
    )

    if not args.receipt and not args.all:
        parser.error("Provide either --receipt PATH or --all")
    if args.receipt and args.all:
        parser.error("Use --receipt OR --all, not both")

    try:
        if args.all:
            logger.info("cli_mode | mode=batch | csv=%s", args.csv)
            run_all_test_receipts(args.csv)
            return

        logger.info("cli_mode | mode=single | receipt=%s | csv=%s", args.receipt, args.csv)
        if args.json:
            transactions_df = load_transactions(args.csv)
            receipt = extract_receipt(args.receipt)
            matches = find_matches(receipt, transactions_df)
            diagnosis = diagnose(matches, receipt)
            result = format_explanation_json(diagnosis)
            print(json.dumps(result, indent=2))
        else:
            explanation = run_pipeline(args.receipt, args.csv)
            print(explanation)
    except FileNotFoundError as exc:
        logger.error("cli_error | type=FileNotFoundError | error=%s", exc)
        print(f"\nError: {exc}")
        raise SystemExit(1) from exc
    except ValueError as exc:
        logger.error("cli_error | type=ValueError | error=%s", exc)
        print(f"\nError: {exc}")
        raise SystemExit(1) from exc
    except KeyboardInterrupt:
        print("\nInterrupted.")
        raise SystemExit(130)
    except Exception as exc:
        logger.error(
            "cli_error | type=%s | error=%s",
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        print(f"\nUnexpected error: {exc}")
        print("Run with --verbose for full traceback.")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()


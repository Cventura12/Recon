"""
match.py - Transaction scoring and candidate ranking.

This module evaluates each bank transaction as a potential match for a single
receipt using three scoring dimensions:
- vendor similarity
- amount proximity
- date proximity

Outputs are ranked `MatchCandidate` objects with evidence strings that explain
why each score was assigned.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

try:
    from rapidfuzz import fuzz
except ImportError:
    from difflib import SequenceMatcher

    class _FuzzFallback:
        """Pure Python fallback when rapidfuzz is not installed."""

        @staticmethod
        def ratio(s1: str, s2: str) -> float:
            return SequenceMatcher(None, s1, s2).ratio() * 100.0

    fuzz = _FuzzFallback()

from logging_config import get_logger
from models import MatchCandidate, ReceiptData, Transaction
from normalize import normalize_amount, normalize_date, normalize_vendor

logger = get_logger(__name__)

# NOTE: The @graceful decorator from logging_config.py can be applied to any
# pipeline function for automatic error recovery. For now this module handles
# errors explicitly with local try/except blocks.

VENDOR_WEIGHT = 0.40
AMOUNT_WEIGHT = 0.35
DATE_WEIGHT = 0.25

MAX_DATE_DIFF_DAYS = 3
MIN_CONFIDENCE_THRESHOLD = 30.0
MAX_RESULTS = 3


def score_vendor(receipt_vendor: str, transaction_merchant: str) -> tuple[float, str]:
    """Score vendor name similarity between receipt and transaction."""
    rv = normalize_vendor(receipt_vendor)
    tm = normalize_vendor(transaction_merchant)

    if not rv and not tm:
        score = 0.0
        evidence = "Both vendor names are empty - cannot compare"
        logger.debug(
            "vendor_scoring | receipt_raw=%r | receipt_norm=%r | bank_raw=%r | bank_norm=%r | score=%.1f",
            receipt_vendor,
            rv,
            transaction_merchant,
            tm,
            score,
        )
        return score, evidence

    if not rv:
        score = 0.0
        evidence = f"Receipt vendor name is empty (bank: '{tm}')"
        logger.debug(
            "vendor_scoring | receipt_raw=%r | receipt_norm=%r | bank_raw=%r | bank_norm=%r | score=%.1f",
            receipt_vendor,
            rv,
            transaction_merchant,
            tm,
            score,
        )
        return score, evidence

    if not tm:
        score = 0.0
        evidence = f"Bank merchant name is empty (receipt: '{rv}')"
        logger.debug(
            "vendor_scoring | receipt_raw=%r | receipt_norm=%r | bank_raw=%r | bank_norm=%r | score=%.1f",
            receipt_vendor,
            rv,
            transaction_merchant,
            tm,
            score,
        )
        return score, evidence

    if rv == tm:
        score = 100.0
        evidence = f"Vendor names match exactly: '{rv}'"
        logger.debug(
            "vendor_scoring | receipt_raw=%r | receipt_norm=%r | bank_raw=%r | bank_norm=%r | score=%.1f",
            receipt_vendor,
            rv,
            transaction_merchant,
            tm,
            score,
        )
        return score, evidence

    score = round(float(fuzz.ratio(rv, tm)), 1)
    score = max(0.0, min(100.0, score))

    if score >= 95:
        evidence = f"Vendor names match: '{rv}' ~ '{tm}' (score: {score})"
    elif score >= 80:
        evidence = f"Vendor names similar: '{rv}' ~ '{tm}' (score: {score})"
    elif score >= 60:
        evidence = f"Vendor names differ: '{rv}' vs '{tm}' (score: {score})"
    elif score >= 40:
        evidence = f"Vendor names weakly similar: '{rv}' vs '{tm}' (score: {score})"
    else:
        evidence = f"Vendor names unrelated: '{rv}' vs '{tm}' (score: {score})"

    logger.debug(
        "vendor_scoring | receipt_raw=%r | receipt_norm=%r | bank_raw=%r | bank_norm=%r | score=%.1f",
        receipt_vendor,
        rv,
        transaction_merchant,
        tm,
        score,
    )
    return score, evidence


def score_amount(receipt_total: float, transaction_amount: float) -> tuple[float, float, float, str]:
    """Score amount proximity between receipt total and transaction amount."""
    receipt_value = normalize_amount(receipt_total)
    txn_value = normalize_amount(transaction_amount)

    if receipt_value <= 0.0:
        abs_diff = round(abs(txn_value), 2)
        score = 0.0
        pct_diff = 100.0
        evidence = (
            f"Receipt total is $0.00 - cannot compute amount proximity "
            f"(bank: ${txn_value:.2f})"
        )
        logger.debug(
            "amount_scoring | receipt=%.2f | bank=%.2f | score=%.1f | abs_diff=%.2f | pct_diff=%.1f",
            receipt_value,
            txn_value,
            score,
            abs_diff,
            pct_diff,
        )
        return score, abs_diff, pct_diff, evidence

    abs_diff = round(abs(receipt_value - txn_value), 2)
    pct_diff = round((abs_diff / receipt_value) * 100.0, 1)
    score = max(0.0, (1.0 - (abs_diff / receipt_value) / 0.25)) * 100.0
    score = round(min(100.0, score), 1)

    if abs_diff == 0:
        evidence = f"Exact amount match: ${receipt_value:.2f}"
        logger.debug(
            "amount_scoring | receipt=%.2f | bank=%.2f | score=%.1f | abs_diff=%.2f | pct_diff=%.1f",
            receipt_value,
            txn_value,
            score,
            abs_diff,
            pct_diff,
        )
        return score, abs_diff, pct_diff, evidence

    diff_sign = "+" if txn_value > receipt_value else "-"
    if pct_diff <= 2.0:
        evidence = (
            f"Amount very close: ${receipt_value:.2f} vs ${txn_value:.2f} "
            f"(diff: {diff_sign}${abs_diff:.2f}, {pct_diff}%)"
        )
    elif pct_diff <= 10.0:
        evidence = (
            f"Amount close: ${receipt_value:.2f} vs ${txn_value:.2f} "
            f"(diff: {diff_sign}${abs_diff:.2f}, {pct_diff}%)"
        )
    elif pct_diff <= 25.0:
        evidence = (
            f"Amount differs: ${receipt_value:.2f} vs ${txn_value:.2f} "
            f"(diff: {diff_sign}${abs_diff:.2f}, {pct_diff}%)"
        )
    else:
        evidence = (
            f"Amount significantly different: ${receipt_value:.2f} vs ${txn_value:.2f} "
            f"(diff: {diff_sign}${abs_diff:.2f}, {pct_diff}%)"
        )

    logger.debug(
        "amount_scoring | receipt=%.2f | bank=%.2f | score=%.1f | abs_diff=%.2f | pct_diff=%.1f",
        receipt_value,
        txn_value,
        score,
        abs_diff,
        pct_diff,
    )
    return score, abs_diff, pct_diff, evidence


def score_date(receipt_date: str, transaction_date: str) -> tuple[float, int, str]:
    """Score date proximity between receipt and transaction."""
    rd = normalize_date(receipt_date)
    td = normalize_date(transaction_date)

    if not rd and not td:
        score = 0.0
        days_apart = 999
        evidence = "Both dates are missing - cannot compare"
        logger.debug(
            "date_scoring | receipt_norm=%s | bank_norm=%s | days_apart=%s | score=%.1f",
            rd,
            td,
            days_apart,
            score,
        )
        return score, days_apart, evidence

    if not rd:
        score = 0.0
        days_apart = 999
        evidence = f"Receipt date is missing (bank: {td})"
        logger.debug(
            "date_scoring | receipt_norm=%s | bank_norm=%s | days_apart=%s | score=%.1f",
            rd,
            td,
            days_apart,
            score,
        )
        return score, days_apart, evidence

    if not td:
        score = 0.0
        days_apart = 999
        evidence = f"Bank date is missing (receipt: {rd})"
        logger.debug(
            "date_scoring | receipt_norm=%s | bank_norm=%s | days_apart=%s | score=%.1f",
            rd,
            td,
            days_apart,
            score,
        )
        return score, days_apart, evidence

    try:
        r_date = datetime.strptime(rd, "%Y-%m-%d")
        t_date = datetime.strptime(td, "%Y-%m-%d")
    except ValueError as exc:
        logger.warning(
            "date_scoring_parse_error | receipt_norm=%s | bank_norm=%s | error=%s | fallback_days=999",
            rd,
            td,
            exc,
        )
        return 0.0, 999, f"Could not compare dates: {rd} vs {td}"

    days_apart = abs((t_date - r_date).days)
    score = round(max(0.0, (1.0 - (days_apart / 5.0))) * 100.0, 1)

    if days_apart == 0:
        evidence = f"Same date: {rd}"
    elif days_apart <= 3:
        direction = "later" if t_date > r_date else "earlier"
        evidence = (
            f"Settlement delay: {days_apart} day(s) {direction} "
            f"(receipt: {rd}, bank: {td})"
        )
    elif days_apart <= 7:
        evidence = (
            f"Date gap: {days_apart} days apart (receipt: {rd}, bank: {td}) - "
            "exceeds typical 1-3 day settlement window"
        )
    else:
        evidence = f"Date mismatch: {days_apart} days apart (receipt: {rd}, bank: {td})"

    logger.debug(
        "date_scoring | receipt_norm=%s | bank_norm=%s | days_apart=%s | score=%.1f",
        rd,
        td,
        days_apart,
        score,
    )
    return score, days_apart, evidence


def find_matches(receipt: ReceiptData, transactions_df: pd.DataFrame) -> list[MatchCandidate]:
    """Find best matching transactions for a receipt."""
    if receipt is None:
        logger.error("matching_input_error | receipt_none=True | fallback=[]")
        return []

    if transactions_df is None:
        logger.warning("matching_input_warning | dataframe_none=True | fallback=[]")
        return []

    if not isinstance(transactions_df, pd.DataFrame):
        logger.error(
            "matching_input_error | expected_type=DataFrame | got_type=%s | fallback=[]",
            type(transactions_df).__name__,
        )
        return []

    if transactions_df.empty:
        logger.warning("matching_input_warning | dataframe_empty=True | fallback=[]")
        return []

    required_cols = ["merchant", "amount", "date"]
    missing_cols = [col for col in required_cols if col not in transactions_df.columns]
    if missing_cols:
        logger.error(
            "matching_input_error | missing_columns=%s | available_columns=%s | fallback=[]",
            missing_cols,
            list(transactions_df.columns),
        )
        return []

    receipt_vendor = str(getattr(receipt, "vendor", "") or "")
    receipt_total = normalize_amount(getattr(receipt, "total", 0.0))
    receipt_date = str(getattr(receipt, "date", "") or "")

    if not receipt_vendor:
        logger.warning(
            "matching_receipt_warning | vendor_empty=True | fallback='rely on amount/date signals'"
        )
    if receipt_total <= 0.0:
        logger.warning(
            "matching_receipt_warning | total_zero_or_invalid=True | fallback='rely on vendor/date signals'"
        )

    original_len = len(transactions_df)
    valid_df = transactions_df.dropna(subset=["merchant", "amount"]).copy()
    dropped_rows = original_len - len(valid_df)
    if dropped_rows > 0:
        logger.warning(
            "matching_input_warning | dropped_rows=%s | reason='missing merchant or amount' | remaining_rows=%s",
            dropped_rows,
            len(valid_df),
        )

    if valid_df.empty:
        logger.warning("matching_input_warning | no_valid_rows_after_dropna=True | fallback=[]")
        return []

    candidates: list[MatchCandidate] = []
    skipped_date = 0

    for idx, row in valid_df.iterrows():
        try:
            raw_date = str(row["date"]) if pd.notna(row["date"]) else ""
            d_score, days_apart, d_evidence = score_date(receipt_date, raw_date)
            if days_apart > MAX_DATE_DIFF_DAYS and days_apart != 999:
                skipped_date += 1
                continue

            raw_merchant = str(row["merchant"]) if pd.notna(row["merchant"]) else ""
            amount_value = normalize_amount(row["amount"] if pd.notna(row["amount"]) else 0.0)

            v_score, v_evidence = score_vendor(receipt_vendor, raw_merchant)
            a_score, abs_diff, pct_diff, a_evidence = score_amount(receipt_total, amount_value)

            overall = round(
                v_score * VENDOR_WEIGHT
                + a_score * AMOUNT_WEIGHT
                + d_score * DATE_WEIGHT,
                1,
            )

            description_raw = row.get("description", None)
            transaction_id_raw = row.get("transaction_id", None)

            candidate = MatchCandidate(
                transaction=Transaction(
                    merchant=raw_merchant,
                    amount=amount_value,
                    date=raw_date,
                    description=str(description_raw) if pd.notna(description_raw) else None,
                    transaction_id=str(transaction_id_raw) if pd.notna(transaction_id_raw) else None,
                ),
                vendor_score=v_score,
                amount_diff=abs_diff,
                amount_pct_diff=pct_diff,
                date_diff=days_apart,
                overall_confidence=overall,
                evidence=[v_evidence, a_evidence, d_evidence],
            )
            candidates.append(candidate)
        except Exception as exc:
            logger.warning(
                "matching_row_error | row_index=%s | merchant=%r | error=%s | fallback='skip row'",
                idx,
                row.get("merchant", "?"),
                exc,
            )
            continue

    above_threshold = [
        candidate for candidate in candidates if candidate.overall_confidence >= MIN_CONFIDENCE_THRESHOLD
    ]
    below_threshold = len(candidates) - len(above_threshold)
    above_threshold.sort(key=lambda candidate: candidate.overall_confidence, reverse=True)
    result = above_threshold[:MAX_RESULTS]

    top_conf = result[0].overall_confidence if result else 0.0
    logger.info(
        "matching_complete | candidates_scored=%s | above_threshold=%s | skipped_date=%s | filtered_below_threshold=%s | top_confidence=%.1f%% | receipt_vendor=%r",
        len(candidates),
        len(result),
        skipped_date,
        below_threshold,
        top_conf,
        receipt_vendor,
    )

    if result:
        top = result[0]
        logger.info(
            "matching_top | merchant=%r | confidence=%.1f%% | vendor_score=%.1f | amount_diff=%.2f | date_diff=%s",
            top.transaction.merchant,
            top.overall_confidence,
            top.vendor_score,
            top.amount_diff,
            top.date_diff,
        )
    else:
        logger.info("matching_top | none=True | reason='no candidates above threshold'")

    return result


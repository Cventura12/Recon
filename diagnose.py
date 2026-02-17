"""
diagnose.py - Deterministic mismatch classification rules.

This module converts ranked match candidates into a final `Diagnosis`.
"""

from __future__ import annotations

from logging_config import get_logger
from models import Diagnosis, MatchCandidate, MismatchType, ReceiptData

logger = get_logger(__name__)

# NOTE: The @graceful decorator from logging_config.py can be applied to any
# pipeline function for automatic error recovery. For now this module handles
# errors explicitly with local try/except blocks.

# -- Classification Thresholds --
# These control when each mismatch archetype fires.
# Tuning guidance is in the comments for each.

VENDOR_MATCH_THRESHOLD = 80
# Vendor similarity score (0-100) above which vendors are considered "matching."
# At 80: "starbucks" vs "starbucks" (100) = match.
#         "el agave mexican" vs "elagave" (61) = MISMATCH.
#         "home depot" vs "home depot" (100) = match.
# Lower this to 70 if you want to be more lenient on vendor matching.
# Raise to 90 if you want stricter matching.

SETTLEMENT_MAX_DAYS = 3
# Maximum date difference (in days) to consider as a settlement delay.
# 1-3 is the standard credit card settlement window.
# Set to 5 to handle holiday weekends (rare but possible).

TIP_TAX_MAX_PCT = 25
# Maximum percentage difference to attribute to tip/tax variance.
# At 25%: a $100 receipt with $125 bank charge = within threshold.
#         a $100 receipt with $130 bank charge = exceeds threshold.
# NOTE: The Starbucks test case (30.1%) exceeds this threshold.
# User research may reveal this needs to be 35% for restaurants.

AMOUNT_CLOSE_THRESHOLD = 2
# Percentage difference below which amounts are considered "matching."
# At 2%: a $100 receipt with $101.50 bank charge = amounts "match."
# This is the threshold for declaring amounts as NOT a source of mismatch.

DATE_CLOSE_THRESHOLD = 0
# Days difference at which dates are considered "matching."
# 0 = only same-day counts as matching dates.
# If you change this to 1, then 1-day differences won't trigger
# SETTLEMENT_DELAY (they'll be considered "matching").


def _safe_float(value: object, fallback: float = 0.0) -> float:
    """Safely coerce a value to float for defensive calculations."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _calibrate_confidence(
    match_confidence: float,
    receipt: ReceiptData | None,
    num_matches: int,
    labels: list[MismatchType],
) -> float:
    """Calibrate final confidence with extraction quality and ambiguity signals."""
    adjusted = _safe_float(match_confidence, 0.0)

    if receipt and receipt.is_low_confidence:
        extraction_penalty = (0.8 - receipt.confidence) * 30.0
        extraction_penalty = max(0.0, min(extraction_penalty, 15.0))
        adjusted -= extraction_penalty
        logger.debug(
            "confidence_calibration | factor=extraction_quality | penalty=%.1f | receipt_confidence=%.2f",
            extraction_penalty,
            receipt.confidence,
        )

    if num_matches >= 3:
        adjusted -= 5.0
        logger.debug("confidence_calibration | factor=ambiguity | num_matches=%s | penalty=5.0", num_matches)
    elif num_matches == 2:
        adjusted -= 2.0
        logger.debug("confidence_calibration | factor=ambiguity | num_matches=%s | penalty=2.0", num_matches)

    if len(labels) >= 3:
        adjusted -= 3.0
        logger.debug("confidence_calibration | factor=compound_complexity | labels=%s | penalty=3.0", len(labels))
    elif len(labels) == 2:
        adjusted -= 1.0
        logger.debug("confidence_calibration | factor=compound_complexity | labels=%s | penalty=1.0", len(labels))

    if receipt is not None and not labels and adjusted >= 80.0:
        adjusted += 3.0
        logger.debug("confidence_calibration | factor=clean_bonus | bonus=3.0")

    calibrated = max(0.0, min(100.0, round(adjusted, 1)))
    logger.debug(
        "confidence_calibration | raw=%.1f | calibrated=%.1f | num_matches=%s | labels=%s",
        _safe_float(match_confidence, 0.0),
        calibrated,
        num_matches,
        [label.value for label in labels],
    )
    return calibrated


def diagnose(
    matches: list[MatchCandidate] | None,
    receipt: ReceiptData | None = None,
) -> Diagnosis:
    """Classify mismatch type based on match candidates."""
    try:
        if matches is None:
            matches = []

        matches = [match for match in matches if match is not None]

        # ==========================================================
        # CASE 1: No matches found at all
        # ==========================================================
        if not matches:
            logger.info("diagnosis_case | type=no_match | reason='no candidates available'")
            evidence = [
                "No transactions in the CSV scored above the 30% confidence threshold.",
            ]
            if receipt and receipt.date:
                evidence.append(
                    f"Receipt dated {receipt.date} - verify that transactions "
                    f"from this date range are included in the CSV."
                )
            evidence.append(
                "Possible causes: transaction not yet posted by the bank, "
                "transaction in a different account, or receipt doesn't "
                "belong to this transaction set."
            )
            return Diagnosis(
                labels=[MismatchType.NO_MATCH],
                confidence=95.0,
                evidence=evidence,
                top_match=None,
                receipt=receipt,
                explanation="",
            )

        top = matches[0]
        if not hasattr(top, "vendor_score") or not hasattr(top, "overall_confidence"):
            logger.error(
                "diagnosis_input_error | reason='top candidate missing required fields' | fallback=no_match"
            )
            return Diagnosis(
                labels=[MismatchType.NO_MATCH],
                confidence=0.0,
                evidence=["Internal error: match candidate has invalid structure."],
                top_match=None,
                receipt=receipt,
                explanation="",
            )

        labels: list[MismatchType] = []
        diagnosis_evidence: list[str] = []

        vendor_matches = _safe_float(top.vendor_score) >= VENDOR_MATCH_THRESHOLD
        amount_pct_diff = _safe_float(top.amount_pct_diff)
        amount_matches = amount_pct_diff <= AMOUNT_CLOSE_THRESHOLD
        date_diff = int(getattr(top, "date_diff", 999))
        date_matches = date_diff == DATE_CLOSE_THRESHOLD

        logger.debug(
            "diagnosis_signals | vendor_matches=%s | vendor_score=%.1f | amount_matches=%s | amount_pct_diff=%.1f | date_matches=%s | date_diff=%s",
            vendor_matches,
            _safe_float(top.vendor_score),
            amount_matches,
            amount_pct_diff,
            date_matches,
            date_diff,
        )

        # -- Check 1: VENDOR_MISMATCH --
        if not vendor_matches:
            labels.append(MismatchType.VENDOR_MISMATCH)
            receipt_vendor = receipt.vendor if receipt else "unknown"
            bank_merchant = top.transaction.merchant
            diagnosis_evidence.append(
                f"Vendor descriptor mismatch: names scored {top.vendor_score:.1f}/100 "
                f"(threshold: {VENDOR_MATCH_THRESHOLD}). Receipt vendor '{receipt_vendor}' "
                f"does not closely match bank descriptor '{bank_merchant}' - likely "
                "abbreviated or coded by payment processor."
            )
            logger.info(
                "diagnosis_rule_fired | rule=vendor_mismatch | vendor_score=%.1f | threshold=%s",
                top.vendor_score,
                VENDOR_MATCH_THRESHOLD,
            )

        # -- Check 2: SETTLEMENT_DELAY --
        if not date_matches and 1 <= date_diff <= SETTLEMENT_MAX_DAYS:
            labels.append(MismatchType.SETTLEMENT_DELAY)
            diagnosis_evidence.append(
                f"Settlement delay: {date_diff} day(s) between receipt date and bank "
                f"posting date. Credit card transactions typically settle in 1-{SETTLEMENT_MAX_DAYS} "
                "business days, so this delay is within the normal range."
            )
            logger.info(
                "diagnosis_rule_fired | rule=settlement_delay | date_diff=%s | threshold_max=%s",
                date_diff,
                SETTLEMENT_MAX_DAYS,
            )

        # -- Check 3: TIP_TAX_VARIANCE --
        if not amount_matches and amount_pct_diff <= TIP_TAX_MAX_PCT:
            labels.append(MismatchType.TIP_TAX_VARIANCE)
            base_evidence = (
                f"Amount variance of ${top.amount_diff:.2f} ({amount_pct_diff:.1f}%) "
                f"is within the {TIP_TAX_MAX_PCT}% threshold for tip/tax variance."
            )
            context_parts: list[str] = []

            if receipt and receipt.has_tip and receipt.tip is not None:
                context_parts.append(f"Receipt includes a ${receipt.tip:.2f} tip.")

            if receipt and receipt.has_tax and receipt.tax is not None:
                if abs(_safe_float(top.amount_diff) - receipt.tax) < 1.0:
                    context_parts.append(
                        f"Difference (${top.amount_diff:.2f}) is close to the receipt tax amount (${receipt.tax:.2f})."
                    )

            if receipt is not None:
                if _safe_float(top.transaction.amount) > receipt.total:
                    context_parts.append(
                        "Bank charged more than receipt total - consistent with tip added after receipt was printed."
                    )
                elif _safe_float(top.transaction.amount) < receipt.total:
                    context_parts.append(
                        "Bank charged less than receipt total - possible discount, partial refund, or pre-tip authorization."
                    )

            if context_parts:
                diagnosis_evidence.append(base_evidence + " " + " ".join(context_parts))
            else:
                diagnosis_evidence.append(
                    base_evidence + " Consistent with tip, tax adjustment, or rounding difference."
                )

            logger.info(
                "diagnosis_rule_fired | rule=tip_tax_variance | amount_diff=%.2f | amount_pct_diff=%.1f | threshold_max=%s",
                _safe_float(top.amount_diff),
                amount_pct_diff,
                TIP_TAX_MAX_PCT,
            )

        # ==========================================================
        # POST-CHECK: Handle cases where no archetype triggered
        # ==========================================================
        if not labels:
            if _safe_float(top.overall_confidence) >= 80.0:
                diagnosis_evidence.append(
                    "All signals align - vendor, amount, and date all match within thresholds. "
                    "This appears to be a clean match with no accounting exception."
                )
                logger.info(
                    "diagnosis_case | type=clean_match | confidence=%.1f | vendor_score=%.1f | amount_pct_diff=%.1f | date_diff=%s",
                    _safe_float(top.overall_confidence),
                    _safe_float(top.vendor_score),
                    amount_pct_diff,
                    date_diff,
                )
            else:
                labels.append(MismatchType.PARTIAL_MATCH)
                contributing_factors: list[str] = []

                if VENDOR_MATCH_THRESHOLD <= _safe_float(top.vendor_score) < 95.0:
                    contributing_factors.append(
                        f"vendor similarity is moderate ({top.vendor_score:.1f}/100)"
                    )
                if amount_pct_diff > AMOUNT_CLOSE_THRESHOLD and amount_pct_diff > TIP_TAX_MAX_PCT:
                    contributing_factors.append(
                        f"amount difference ({amount_pct_diff:.1f}%) exceeds the {TIP_TAX_MAX_PCT}% tip/tax threshold"
                    )
                if date_diff > SETTLEMENT_MAX_DAYS and date_diff != 999:
                    contributing_factors.append(
                        f"date gap ({date_diff} days) exceeds the {SETTLEMENT_MAX_DAYS}-day settlement window"
                    )

                if contributing_factors:
                    diagnosis_evidence.append(
                        f"Partial match: overall confidence is {top.overall_confidence:.1f}% "
                        f"(below 80% clean match threshold). Contributing factors: "
                        f"{'; '.join(contributing_factors)}."
                    )
                else:
                    diagnosis_evidence.append(
                        f"Partial match: overall confidence is {top.overall_confidence:.1f}% "
                        "(below 80% clean match threshold). Some signals align but the combined "
                        "evidence is not strong enough for a confident diagnosis."
                    )

                logger.info(
                    "diagnosis_rule_fired | rule=partial_match | confidence=%.1f",
                    _safe_float(top.overall_confidence),
                )

        # -- Extraction confidence warning --
        if receipt and receipt.is_low_confidence:
            diagnosis_evidence.append(
                f"WARNING: Low extraction confidence ({receipt.confidence:.0%}). "
                "The receipt image may be blurry, damaged, or partially illegible. "
                "Extracted values should be verified manually before acting on this diagnosis."
            )
            logger.warning(
                "diagnosis_warning | type=low_extraction_confidence | confidence=%.0f%%",
                receipt.confidence * 100.0,
            )

        # -- Multiple candidates notice --
        if len(matches) > 1:
            runner_up = matches[1]
            confidence_gap = _safe_float(top.overall_confidence) - _safe_float(runner_up.overall_confidence)
            if confidence_gap < 15.0:
                diagnosis_evidence.append(
                    f"Note: A second candidate ('{runner_up.transaction.merchant}', "
                    f"${runner_up.transaction.amount:.2f}) scored {runner_up.overall_confidence:.1f}% - "
                    f"only {confidence_gap:.1f} points below the top match. Manual review recommended."
                )

        complete_evidence = list(getattr(top, "evidence", []) or []) + diagnosis_evidence
        calibrated_confidence = _calibrate_confidence(
            _safe_float(top.overall_confidence),
            receipt,
            len(matches),
            labels,
        )

        diagnosis = Diagnosis(
            labels=labels,
            confidence=calibrated_confidence,
            evidence=complete_evidence,
            top_match=top,
            receipt=receipt,
            explanation="",
        )

        logger.info(
            "diagnosis_complete | labels=%s | confidence=%.1f%% | evidence_count=%s | receipt_vendor=%r",
            [label.value for label in labels],
            diagnosis.confidence,
            len(complete_evidence),
            receipt.vendor if receipt else "unknown",
        )
        return diagnosis
    except Exception as exc:
        logger.error(
            "diagnosis_error | error_type=%s | error=%s | fallback=no_match",
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return Diagnosis(
            labels=[MismatchType.NO_MATCH],
            confidence=0.0,
            evidence=[
                f"Diagnosis failed due to {type(exc).__name__}: {exc}",
                "Returning safe fallback diagnosis; review input data manually.",
            ],
            top_match=matches[0] if matches else None,
            receipt=receipt,
            explanation="",
        )

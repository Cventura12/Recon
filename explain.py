"""
explain.py - Human-readable and JSON-ready diagnosis formatting.

This module converts a structured `Diagnosis` object into:
- terminal-friendly text output for CLI usage
- machine-friendly dictionary output for APIs/logging/storage
"""

from __future__ import annotations

from logging_config import get_logger
from models import Diagnosis, MismatchType

logger = get_logger(__name__)

LABEL_NAMES: dict[MismatchType, str] = {
    MismatchType.VENDOR_MISMATCH: "Vendor Descriptor Mismatch",
    MismatchType.SETTLEMENT_DELAY: "Settlement Delay",
    MismatchType.TIP_TAX_VARIANCE: "Tip/Tax Variance",
    MismatchType.PARTIAL_MATCH: "Partial Match",
    MismatchType.NO_MATCH: "No Match Found",
}

OUTPUT_WIDTH = 56
SEPARATOR = "=" * OUTPUT_WIDTH
MAX_EVIDENCE_DISPLAY = 8


def format_explanation(diagnosis: Diagnosis | None) -> str:
    """Format a Diagnosis into a clean, human-readable text block."""
    if diagnosis is None:
        logger.error("explain_input_error | diagnosis_none=True | fallback=error_block")
        return (
            "\n"
            + SEPARATOR
            + "\n"
            + "  ERROR: No diagnosis data available\n"
            + SEPARATOR
            + "\n"
        )

    try:
        diagnosis_labels = list(diagnosis.labels) if diagnosis.labels is not None else []
        lines: list[str] = [""]

        if MismatchType.NO_MATCH in diagnosis_labels:
            header = "NO MATCH FOUND"
        elif diagnosis.is_clean_match:
            header = f"Match Found - {diagnosis.confidence:.0f}%"
        else:
            if diagnosis.confidence >= 80:
                status = "Probable Match"
            elif diagnosis.confidence >= 50:
                status = "Possible Match"
            else:
                status = "Weak Match"
            header = f"{status} - {diagnosis.confidence:.0f}%"

        lines.append(SEPARATOR)
        lines.append(f"  {header}")
        lines.append(SEPARATOR)

        lines.append("")
        if diagnosis.receipt:
            lines.append(f"  Receipt:      {diagnosis.receipt.vendor}")
            lines.append(
                f"                ${diagnosis.receipt.total:.2f}  |  "
                f"{diagnosis.receipt.date or 'date unknown'}"
            )
        else:
            lines.append("  Receipt:      (no receipt data available)")

        if diagnosis.top_match and MismatchType.NO_MATCH not in diagnosis_labels:
            tm = diagnosis.top_match
            lines.append("")
            lines.append(f"  Best Match:   {tm.transaction.merchant}")
            lines.append(
                f"                ${tm.transaction.amount:.2f}  |  "
                f"{tm.transaction.date or 'date unknown'}"
            )

        lines.append("")
        lines.append("  Evidence:")

        evidence_items = list(diagnosis.evidence) if diagnosis.evidence else []
        if not evidence_items:
            lines.append("    • (no evidence recorded)")
        elif len(evidence_items) <= MAX_EVIDENCE_DISPLAY:
            for evidence in evidence_items:
                lines.append(f"    • {evidence}")
        else:
            for evidence in evidence_items[: MAX_EVIDENCE_DISPLAY - 1]:
                lines.append(f"    • {evidence}")
            remaining = len(evidence_items) - (MAX_EVIDENCE_DISPLAY - 1)
            lines.append(f"    • ... and {remaining} more evidence item(s)")

        if diagnosis.receipt:
            try:
                from grounding import grounding_coverage, has_grounding

                if has_grounding(diagnosis.receipt):
                    coverage = grounding_coverage(diagnosis.receipt)
                    if coverage > 0:
                        lines.append("")
                        lines.append(
                            f"  Grounding: {coverage:.0%} of fields traced to receipt image"
                        )
            except Exception as exc:
                logger.debug(
                    "explain_grounding_warning | error=%s | fallback='skip grounding section'",
                    exc,
                )

        lines.append("")
        if diagnosis.is_clean_match:
            lines.append("  Diagnosis: Clean Match - No Exception")
        elif diagnosis_labels:
            lines.append(f"  Diagnosis: {diagnosis.label_summary}")
        else:
            lines.append("  Diagnosis: Unclassified")

        if diagnosis.receipt and diagnosis.receipt.is_low_confidence:
            lines.append("")
            lines.append(
                f"  WARNING: Low extraction confidence ({diagnosis.receipt.confidence:.0%})"
            )
            lines.append(
                "    Receipt may be blurry or damaged. Verify extracted values manually."
            )

        if any("second candidate" in evidence.lower() for evidence in evidence_items):
            lines.append("")
            lines.append("  WARNING: Multiple close candidates detected")
            lines.append("    Runner-up candidate scored close to top match. Review manually.")

        lines.append("")
        lines.append(SEPARATOR)
        lines.append("")
        return "\n".join(lines)
    except Exception as exc:
        logger.error(
            "explain_format_error | error_type=%s | error=%s",
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return (
            "\n"
            + SEPARATOR
            + "\n"
            + "  EXPLANATION FORMAT ERROR\n"
            + SEPARATOR
            + "\n\n"
            + f"  Error: {type(exc).__name__}: {exc}\n\n"
            + SEPARATOR
            + "\n"
        )


def format_explanation_json(diagnosis: Diagnosis | None) -> dict:
    """Format a Diagnosis as a structured JSON-compatible dictionary."""
    if diagnosis is None:
        logger.error("explain_json_input_error | diagnosis_none=True | fallback=error_payload")
        return {
            "status": "error",
            "confidence": 0.0,
            "diagnosis": {
                "labels": [],
                "label_names": [],
                "label_summary": "Error",
                "is_compound": False,
                "is_clean_match": False,
            },
            "evidence": ["No diagnosis data available"],
            "receipt": None,
            "top_match": None,
            "warnings": ["Diagnosis object was None"],
        }

    diagnosis_labels = list(diagnosis.labels) if diagnosis.labels is not None else []

    if MismatchType.NO_MATCH in diagnosis_labels:
        status = "no_match"
    elif diagnosis.is_clean_match:
        status = "clean_match"
    else:
        status = "match_found"

    diagnosis_section = {
        "labels": [label.value for label in diagnosis_labels],
        "label_names": diagnosis.label_names,
        "label_summary": diagnosis.label_summary,
        "is_compound": diagnosis.is_compound,
        "is_clean_match": diagnosis.is_clean_match,
    }

    receipt_section = None
    if diagnosis.receipt:
        receipt_section = {
            "vendor": diagnosis.receipt.vendor,
            "total": diagnosis.receipt.total,
            "date": diagnosis.receipt.date,
            "tax": diagnosis.receipt.tax,
            "tip": diagnosis.receipt.tip,
            "subtotal": diagnosis.receipt.subtotal,
            "confidence": diagnosis.receipt.confidence,
            "is_low_confidence": diagnosis.receipt.is_low_confidence,
            "chunk_ids": list(diagnosis.receipt.chunk_ids),
        }

        try:
            from grounding import extract_grounding, grounding_coverage

            receipt_section["grounding_coverage"] = round(
                grounding_coverage(diagnosis.receipt), 2
            )
            receipt_section["grounding"] = [
                grounding.to_dict() for grounding in extract_grounding(diagnosis.receipt)
            ]
        except Exception as exc:
            logger.debug(
                "explain_json_grounding_warning | error=%s | fallback='omit grounding details'",
                exc,
            )
            receipt_section["grounding_coverage"] = 0.0
            receipt_section["grounding"] = []

    top_match_section = None
    if diagnosis.top_match:
        top_match_section = {
            "merchant": diagnosis.top_match.transaction.merchant,
            "amount": diagnosis.top_match.transaction.amount,
            "date": diagnosis.top_match.transaction.date,
            "transaction_id": diagnosis.top_match.transaction.transaction_id,
            "description": diagnosis.top_match.transaction.description,
            "scores": {
                "vendor_score": round(diagnosis.top_match.vendor_score, 1),
                "amount_diff": round(diagnosis.top_match.amount_diff, 2),
                "amount_pct_diff": round(diagnosis.top_match.amount_pct_diff, 1),
                "date_diff": diagnosis.top_match.date_diff,
                "overall_confidence": round(diagnosis.top_match.overall_confidence, 1),
            },
            "evidence": list(diagnosis.top_match.evidence),
        }

    warnings: list[str] = []
    if diagnosis.receipt and diagnosis.receipt.is_low_confidence:
        warnings.append(
            f"Low extraction confidence ({diagnosis.receipt.confidence:.0%}). Verify extracted values manually."
        )

    return {
        "status": status,
        "confidence": round(float(diagnosis.confidence), 1),
        "diagnosis": diagnosis_section,
        "evidence": list(diagnosis.evidence),
        "receipt": receipt_section,
        "top_match": top_match_section,
        "warnings": warnings,
    }


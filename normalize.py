"""
normalize.py - Data normalization module.

Three core normalizers:
    normalize_vendor(vendor)    -> cleaned vendor name
    normalize_date(date_str)    -> ISO YYYY-MM-DD
    normalize_amount(amount)    -> float rounded to 2 decimals

Three convenience wrappers:
    normalize_receipt_data(receipt)
    normalize_transaction_data(merchant, date, amount)
    normalize_for_comparison(receipt, df)

Design principles:
    - SAME normalization on BOTH sides
    - Pure transformations, no external API calls
    - Invalid input degrades to neutral defaults
"""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import datetime
from typing import Any

from dateutil import parser as dateparser

from logging_config import get_logger
from models import ReceiptData

try:
    import pandas as pd
except ImportError:
    pd = None  # pandas is optional for base normalizers

logger = get_logger(__name__)

VENDOR_ALIASES: dict[str, str] = {
    "amzn": "amazon",
    "amzn mktp": "amazon",
    "amazon.com": "amazon",
    "wmt": "walmart",
    "wal-mart": "walmart",
    "walmart.com": "walmart",
    "sbux": "starbucks",
    "starbux": "starbucks",
    "hd supply": "home depot",
    "the home depot": "home depot",
    "homedepot": "home depot",
    "costco whse": "costco",
    "costco wholesale": "costco",
    "tgt": "target",
    "target.com": "target",
    "chick-fil-a": "chick fil a",
    "mcd": "mcdonalds",
    "mcdonald's": "mcdonalds",
}

STRIP_SUFFIXES: list[str] = [
    "inc",
    "llc",
    "corp",
    "ltd",
    "co",
    "company",
    "restaurant",
    "rest",
    "rstrt",
    "store",
    "stores",
    "services",
    "service",
    "svc",
]

PROCESSOR_PREFIXES: list[str] = [
    "sq *",
    "sq*",
    "pp*",
    "pp *",
    "tst*",
    "tst *",
    "grub*",
    "dd *",
    "ue *",
]


def normalize_vendor(vendor: str | None) -> str:
    """Normalize a vendor/merchant string for comparison."""
    if vendor is None:
        return ""

    if not isinstance(vendor, str):
        try:
            vendor = str(vendor)
        except Exception:
            return ""

    if not vendor.strip():
        return ""

    name = vendor.lower().strip()
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")

    for prefix in PROCESSOR_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix) :].strip()
            break

    if "*" in name:
        name = name.split("*", 1)[0].strip()

    name = re.sub(r"#\s*\d+", "", name)
    # Keep Unicode letters (for international vendors) while stripping punctuation.
    name = re.sub(r"[^\w\s]", "", name, flags=re.UNICODE)
    name = name.replace("_", " ")

    words = name.split()
    while words and words[-1] in STRIP_SUFFIXES:
        words.pop()
    name = " ".join(words)

    normalized_aliases: list[tuple[str, str]] = []
    for alias, canonical in VENDOR_ALIASES.items():
        cleaned_alias = re.sub(r"[^a-z0-9\s]", "", alias.lower().strip())
        cleaned_alias = re.sub(r"\s+", " ", cleaned_alias).strip()
        if cleaned_alias:
            normalized_aliases.append((cleaned_alias, canonical))
    normalized_aliases.sort(key=lambda item: -len(item[0]))

    for alias, canonical in normalized_aliases:
        if name == alias:
            name = canonical
            break
    else:
        for alias, canonical in normalized_aliases:
            if name.startswith(alias):
                name = canonical
                break
        else:
            for alias, canonical in normalized_aliases:
                if alias in name:
                    name = canonical
                    break

    name = re.sub(r"\s+", " ", name).strip()
    logger.debug("normalize_vendor | raw=%r | normalized=%r", vendor, name)
    return name


def normalize_date(date_str: str | None) -> str:
    """Normalize date text to ISO YYYY-MM-DD."""
    if date_str is None:
        return ""

    if not isinstance(date_str, str):
        try:
            date_str = str(date_str)
        except Exception:
            return ""

    date_str = date_str.strip()
    if not date_str:
        return ""

    if not any(char.isdigit() for char in date_str):
        logger.debug("normalize_date | rejected_no_digits | raw=%r", date_str)
        return ""

    lowered = date_str.lower()
    if lowered in {"n/a", "na", "none", "null", "unknown"}:
        return ""

    if re.fullmatch(r"\d{4}", date_str):
        return ""
    if re.fullmatch(r"\d+", date_str):
        return ""
    if re.fullmatch(r"\d{1,2}[/-]\d{2,4}", date_str):
        return ""
    if re.fullmatch(r"[A-Za-z]{3,9}\s+\d{4}", date_str):
        return ""

    try:
        parsed = dateparser.parse(date_str, dayfirst=False)
        if parsed is None:
            logger.warning(
                "normalize_date | parse_failed | raw=%r | fallback=''",
                date_str,
            )
            return ""

        if parsed.year < 2000 or parsed.year > datetime.now().year + 2:
            logger.warning(
                "normalize_date | suspicious_year=%s | raw=%r",
                parsed.year,
                date_str,
            )

        normalized = parsed.strftime("%Y-%m-%d")
        logger.debug("normalize_date | raw=%r | normalized=%r", date_str, normalized)
        return normalized
    except (ValueError, TypeError, OverflowError) as exc:
        logger.warning(
            "normalize_date | parse_error=%s | raw=%r | fallback=''",
            type(exc).__name__,
            date_str,
        )
        return ""


def normalize_amount(amount_str: Any) -> float:
    """Normalize amount input into a non-negative 2-decimal float."""
    if amount_str is None:
        return 0.0

    if isinstance(amount_str, (int, float)) and not isinstance(amount_str, bool):
        value = float(amount_str)
        if not math.isfinite(value):
            logger.warning(
                "normalize_amount | non_finite=%r | fallback=0.0",
                amount_str,
            )
            return 0.0
        if value < 0:
            logger.warning(
                "normalize_amount | negative=%r | fallback=0.0",
                amount_str,
            )
            return 0.0
        return round(value, 2)

    try:
        if pd is not None and pd.isna(amount_str):
            return 0.0
    except (TypeError, ValueError):
        pass

    try:
        cleaned = str(amount_str).strip()
    except Exception:
        return 0.0

    if not cleaned:
        return 0.0

    lowered = cleaned.lower()
    if lowered in {"n/a", "na", "none", "null", "unknown"}:
        return 0.0

    is_negative = (
        cleaned.startswith("-")
        or (cleaned.startswith("(") and cleaned.endswith(")"))
        or "-$" in cleaned
        or "$-" in cleaned
    )

    cleaned = (
        cleaned.replace("$", "")
        .replace("€", "")
        .replace("£", "")
        .replace("¥", "")
        .replace("(", "")
        .replace(")", "")
        .replace(",", "")
        .strip()
    )

    if not cleaned:
        return 0.0

    try:
        value = float(cleaned)
    except (ValueError, TypeError):
        logger.warning(
            "normalize_amount | parse_failed | raw=%r | fallback=0.0",
            amount_str,
        )
        return 0.0

    if not math.isfinite(value):
        logger.warning(
            "normalize_amount | non_finite_parsed=%r | fallback=0.0",
            amount_str,
        )
        return 0.0

    if is_negative or value < 0:
        logger.warning(
            "normalize_amount | negative=%r | fallback=0.0",
            amount_str,
        )
        return 0.0

    normalized = round(value, 2)
    logger.debug("normalize_amount | raw=%r | normalized=%s", amount_str, normalized)
    return normalized


def normalize_receipt_data(receipt: ReceiptData | None) -> tuple[str, str, float]:
    """Normalize comparable fields from a ReceiptData object."""
    if receipt is None:
        logger.warning(
            "normalize_receipt_data | receipt_none=True | fallback=('', '', 0.0)"
        )
        return "", "", 0.0

    return (
        normalize_vendor(getattr(receipt, "vendor", "")),
        normalize_date(getattr(receipt, "date", "") or ""),
        normalize_amount(getattr(receipt, "total", 0.0)),
    )


def normalize_transaction_data(
    merchant: Any,
    date_str: Any,
    amount: Any,
) -> tuple[str, str, float]:
    """Normalize comparable transaction fields."""
    return (
        normalize_vendor(merchant),
        normalize_date(date_str),
        normalize_amount(amount),
    )


def normalize_for_comparison(
    receipt: ReceiptData | None,
    transactions_df: "pd.DataFrame | None",
) -> tuple[tuple[str, str, float], "pd.DataFrame"]:
    """Normalize receipt and all transaction rows for matching."""
    if pd is None:
        raise ImportError(
            "normalize_for_comparison requires pandas. Install with: pip install pandas"
        )

    receipt_normalized = normalize_receipt_data(receipt)

    if transactions_df is None or not isinstance(transactions_df, pd.DataFrame):
        logger.warning(
            "normalize_for_comparison | invalid_dataframe=%s | fallback_empty_df=True",
            type(transactions_df).__name__,
        )
        empty_df = pd.DataFrame(
            columns=[
                "merchant",
                "amount",
                "date",
                "norm_merchant",
                "norm_date",
                "norm_amount",
            ]
        )
        return receipt_normalized, empty_df

    df = transactions_df.copy()
    if "merchant" not in df.columns:
        df["merchant"] = ""
    if "date" not in df.columns:
        df["date"] = ""
    if "amount" not in df.columns:
        df["amount"] = 0.0

    df["norm_merchant"] = df["merchant"].apply(normalize_vendor)
    df["norm_date"] = df["date"].apply(normalize_date)
    df["norm_amount"] = df["amount"].apply(normalize_amount)

    return receipt_normalized, df

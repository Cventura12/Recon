"""
grounding.py - Visual grounding utilities.

Helpers for working with ADE visual grounding metadata.
"""

from __future__ import annotations

from models import ReceiptData
from logging_config import get_logger

logger = get_logger(__name__)


class GroundingInfo:
    """Visual grounding information for one extracted field."""

    def __init__(
        self,
        field_name: str,
        value: str,
        chunk_ids: list[str] | None = None,
        confidence: float = 1.0,
        bounding_box: tuple[float, float, float, float] | None = None,
    ) -> None:
        self.field_name = field_name
        self.value = value
        self.chunk_ids = chunk_ids or []
        self.confidence = confidence
        self.bounding_box = bounding_box

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "field": self.field_name,
            "value": self.value,
            "chunk_ids": list(self.chunk_ids),
            "confidence": float(self.confidence),
            "bounding_box": list(self.bounding_box) if self.bounding_box else None,
        }


def extract_grounding(receipt: ReceiptData) -> list[GroundingInfo]:
    """Extract per-field grounding metadata from ReceiptData."""
    if receipt is None:
        return []

    groundings: list[GroundingInfo] = []
    field_chunks: dict[str, list[str]] = {}

    for chunk_id in receipt.chunk_ids:
        parts = str(chunk_id).rsplit("_", 1)
        if len(parts) == 2:
            field_name = parts[1].strip().lower()
            if field_name:
                field_chunks.setdefault(field_name, []).append(str(chunk_id))

    fields = {
        "vendor": receipt.vendor,
        "total": f"${receipt.total:.2f}",
        "date": receipt.date,
        "tax": f"${receipt.tax:.2f}" if receipt.tax is not None else None,
        "tip": f"${receipt.tip:.2f}" if receipt.tip is not None else None,
        "subtotal": f"${receipt.subtotal:.2f}" if receipt.subtotal is not None else None,
    }

    for field_name, value in fields.items():
        if value is not None:
            groundings.append(
                GroundingInfo(
                    field_name=field_name,
                    value=str(value),
                    chunk_ids=field_chunks.get(field_name, []),
                    confidence=receipt.confidence,
                )
            )

    logger.debug(
        "grounding_extracted | count=%s | chunk_count=%s",
        len(groundings),
        len(receipt.chunk_ids),
    )
    return groundings


def has_grounding(receipt: ReceiptData) -> bool:
    """Return True if receipt has at least one chunk id."""
    if receipt is None:
        return False
    return len(receipt.chunk_ids) > 0


def grounding_coverage(receipt: ReceiptData) -> float:
    """Return fraction of extracted fields that have grounding."""
    if receipt is None or not receipt.chunk_ids:
        return 0.0

    groundings = extract_grounding(receipt)
    if not groundings:
        return 0.0

    grounded_fields = sum(1 for item in groundings if item.chunk_ids)

    total_fields = 2  # vendor + total
    if receipt.date:
        total_fields += 1
    if receipt.tax is not None:
        total_fields += 1
    if receipt.tip is not None:
        total_fields += 1
    if receipt.subtotal is not None:
        total_fields += 1

    return grounded_fields / max(total_fields, 1)


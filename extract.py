"""
extract.py - Receipt extraction boundary for the diagnostic pipeline.

This module is responsible for converting a raw receipt file (.png, .jpg, .pdf)
into structured data represented by `ReceiptData`.

Pipeline role:
- It is the only module that knows anything about LandingAI ADE.
- All ADE-specific SDK calls, parsing behavior, and confidence handling stay here.
- Downstream modules never see ADE internals; they only consume `ReceiptData`.

Design notes:
- The extraction engine is intentionally swappable. Replacing `_extract_with_ade`
  with another OCR/IE backend should not require changes to normalize/match/
  diagnose/explain as long as `ReceiptData` output remains consistent.
- If `VISION_AGENT_API_KEY` is not configured, extraction falls back to
  deterministic mock fixtures (`_extract_mock`) so end-to-end development can
  proceed without paid API access.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from logging_config import get_logger
from models import ReceiptData

logger = get_logger(__name__)

try:
    load_dotenv()
except UnicodeDecodeError:
    # Fallback for legacy Windows-encoded .env files.
    load_dotenv(encoding="cp1252")

# -- Configuration --

# ADE model version for receipt parsing
ADE_MODEL = "dpt-2-latest"

# Minimum confidence before warning is triggered
MIN_CONFIDENCE_THRESHOLD = 0.8

# Maximum file size (bytes) before warning
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

# Supported image formats
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".tiff", ".tif", ".bmp", ".webp"}


def extract_receipt(image_path: str) -> ReceiptData:
    """Extract structured data from a receipt image.

    This is the ONLY public function in this module. The rest of the
    pipeline calls this function and receives a ReceiptData object.
    It never needs to know which extraction engine was used.

    Extraction paths:
        1. ADE (when VISION_AGENT_API_KEY is set in .env):
           Uses LandingAI's Agentic Document Extraction API to parse
           the receipt image and extract vendor, total, date, tax, tip.
           Provides visual grounding via chunk_ids.

        2. Mock (when no API key):
           Returns hardcoded test data based on the receipt filename.
           Designed for development and testing. The mock data exactly
           matches test_data/transactions.csv for end-to-end testing.

    Error philosophy:
        This function NEVER crashes the pipeline. If extraction fails,
        it returns a ReceiptData with confidence=0.1 and vendor="EXTRACTION_ERROR".
        The downstream modules (match, diagnose, explain) handle low-confidence
        data gracefully - the explanation output will show a warning.

        The only exceptions that propagate are:
        - FileNotFoundError (caller gave a bad path)
        - ImportError (vision-agent package not installed)

    Args:
        image_path: Path to the receipt image file.
            Supported formats: .png, .jpg, .jpeg, .pdf, .tiff, .bmp, .webp
            Other formats are accepted with a warning.

    Returns:
        ReceiptData with extracted fields and confidence score.
        confidence < 0.8 means the extraction engine struggled -
        the explanation output will warn the user to verify manually.

    Raises:
        FileNotFoundError: If image_path doesn't exist.
        ImportError: If ADE API key is set but vision-agent isn't installed.

    Examples:
        # With ADE API key configured:
        >>> receipt = extract_receipt("photo_of_receipt.jpg")
        >>> receipt.vendor
        'El Agave Mexican Restaurant'
        >>> receipt.confidence
        0.95

        # Without API key (mock mode):
        >>> receipt = extract_receipt("test_data/receipts/receipt_02_vendor_mismatch.png")
        >>> receipt.vendor
        'El Agave Mexican Restaurant'

        # With a bad image:
        >>> receipt = extract_receipt("blurry_receipt.jpg")
        >>> receipt.confidence
        0.45  # Low - extraction struggled
        >>> receipt.is_low_confidence
        True
    """
    try:
        # -- Input validation (Phase 8 hardening) --
        if image_path is None:
            raise ValueError("image_path cannot be None")

        image_path = str(image_path).strip()
        if not image_path:
            raise ValueError("image_path cannot be empty")

        path = Path(image_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            raise FileNotFoundError(
                f"Receipt image not found: {image_path}\n"
                f"Resolved path: {path}\n"
                f"Current directory: {Path.cwd()}"
            )

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.warning(
                "extract_extension_warning | extension=%s | file=%s | supported=%s | fallback=continue",
                path.suffix,
                image_path,
                ", ".join(sorted(SUPPORTED_EXTENSIONS)),
            )

        file_size = path.stat().st_size
        if file_size == 0:
            raise ValueError(f"Receipt image is empty (0 bytes): {image_path}")

        if file_size > MAX_FILE_SIZE_BYTES:
            logger.warning(
                "extract_file_size_warning | size_mb=%.1f | file=%s | note='ADE may be slow/reject >20MB'",
                file_size / 1024 / 1024,
                image_path,
            )

        api_key = os.getenv("VISION_AGENT_API_KEY", "").strip()
        if api_key:
            logger.info(
                "extract_start | mode=ade | file=%s | path=%s",
                path.name,
                str(path),
            )
            result = _extract_with_ade(str(path), api_key)
            if result.confidence < 0.5:
                logger.warning(
                    "extract_low_confidence | mode=ade | file=%s | confidence=%.0f%% | fallback=continue",
                    path.name,
                    result.confidence * 100.0,
                )
        else:
            logger.info(
                "extract_start | mode=mock | file=%s | api_key=missing",
                path.name,
            )
            logger.info(
                "extract_mode_hint | set_env=VISION_AGENT_API_KEY | action='enable real ADE extraction'"
            )
            result = _extract_mock(str(path))

        if not result.vendor or result.vendor in ("", "UNKNOWN", "EXTRACTION_FAILED"):
            logger.warning(
                "extract_vendor_warning | file=%s | vendor=%r | fallback=continue",
                path.name, 
                result.vendor,
            )
        if result.total == 0.0:
            logger.warning(
                "extract_total_warning | file=%s | total=0.00 | fallback=continue",
                path.name,
            )
        if result.is_low_confidence:
            logger.warning(
                "extract_low_confidence | file=%s | confidence=%.0f%% | note='verify manually'",
                path.name,
                result.confidence * 100.0,
            )

        logger.info(
            "extract_complete | vendor=%r | total=%.2f | date=%s | confidence=%.0f%% | mode=%s | file=%s",
            result.vendor,
            result.total,
            result.date,
            result.confidence * 100.0,
            "ade" if api_key else "mock",
            path.name,
        )
        return result

    except FileNotFoundError:
        raise
    except ImportError as exc:
        raise ImportError(
            f"Missing required package for ADE extraction: {exc}\n"
            f"Install with: pip install vision-agent\n"
            f"Or remove VISION_AGENT_API_KEY from .env to use mock extraction."
        ) from exc
    except ValueError as exc:
        logger.error(
            "extract_validation_error | file=%s | error=%s",
            image_path,
            exc,
            exc_info=True,
        )
        return ReceiptData(
            vendor="EXTRACTION_ERROR",
            total=0.0,
            confidence=0.1,
            raw_text=f"Extraction failed: {type(exc).__name__}: {exc}",
        )
    except Exception as exc:
        logger.error(
            "extract_failure | file=%s | error_type=%s | error=%s",
            image_path,
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return ReceiptData(
            vendor="EXTRACTION_ERROR",
            total=0.0,
            confidence=0.1,
            raw_text=f"Extraction failed: {type(exc).__name__}: {exc}",
        )


def _extract_with_ade(image_path: str, api_key: str) -> ReceiptData:
    """Extract receipt fields with LandingAI ADE using Parse -> Extract.

    Pipeline:
    1. Parse: receipt image/PDF -> markdown + visual chunks.
    2. Extract: markdown + receipt schema -> structured key/value fields.

    Why schema descriptions matter:
    - ADE uses field descriptions as extraction guidance. Rich, explicit
      descriptions improve field selection and reduce ambiguous picks.

    Visual grounding:
    - Parsed chunks include identifiers tied to document regions. We keep
      these chunk IDs in `ReceiptData.chunk_ids` so downstream UI can show
      where extracted values came from on the source receipt.

    Version compatibility note:
    - The `vision-agent`/LandingAI interface has changed across releases.
      This function tries multiple import/call paths and keeps API-specific
      calls isolated so future updates are localized.

    Error-handling philosophy:
    - Missing package imports are re-raised with clear install guidance.
    - Runtime ADE failures do not crash the pipeline. Instead, return a
      low-confidence `ReceiptData` payload (`vendor='EXTRACTION_FAILED'`)
      so downstream modules can proceed and surface review warnings.

    Args:
        image_path: Path to receipt image/PDF to parse and extract.
        api_key: LandingAI API key provided by `extract_receipt`.

    Returns:
        ReceiptData: Structured extraction result with grounding metadata.
    """
    try:
        # Version compatibility: newer installs often expose helper functions
        # via vision_agent.tools.agentic_document_extraction, while some older
        # environments expose FrameSet APIs under landingai.pipeline.frameset.
        ade_module = None
        frame_set_cls = None
        try:
            from vision_agent.tools import agentic_document_extraction as ade_module  # type: ignore
        except ImportError:
            try:
                from landingai.pipeline.frameset import FrameSet as frame_set_cls  # type: ignore
            except ImportError as import_exc:
                raise ImportError(
                    "ADE requires the vision-agent package. "
                    "Install with: pip install vision-agent\n"
                    "Then set VISION_AGENT_API_KEY in your .env file."
                ) from import_exc

        receipt_schema = {
            "type": "object",
            "properties": {
                "vendor": {
                    "type": "string",
                    "description": (
                        "The vendor, merchant, or store name as printed on the "
                        "receipt, usually at the top in large text. This is the "
                        "business name, not the address or phone number. "
                        "Examples: 'Starbucks', 'The Home Depot', 'El Agave Mexican Restaurant'. "
                        "If multiple names appear (e.g., a franchise name and parent company), "
                        "use the most prominent one."
                    ),
                },
                "total": {
                    "type": "number",
                    "description": (
                        "The final total amount paid, including tax and tip. "
                        "Look for labels like 'Total', 'Grand Total', 'Amount Due', "
                        "'Balance Due', or 'Total Charged'. This is typically the "
                        "largest dollar amount on the receipt and appears near the bottom. "
                        "If multiple totals appear, use the one labeled 'Total' or "
                        "the largest amount. Include cents (e.g., 47.50 not 47)."
                    ),
                },
                "date": {
                    "type": "string",
                    "description": (
                        "The transaction date as printed on the receipt. May appear "
                        "in various formats: '01/15/2026', 'Jan 15, 2026', "
                        "'2026-01-15', '1/15/26'. Usually near the top or bottom "
                        "of the receipt. Return exactly as printed - do not reformat. "
                        "If both a date and time appear, return only the date portion."
                    ),
                },
                "tax": {
                    "type": "number",
                    "description": (
                        "Tax amount if listed as a separate line item. "
                        "Look for labels like 'Tax', 'Sales Tax', 'VAT', 'HST', 'GST'. "
                        "Return the dollar amount, not the percentage. "
                        "Return null if tax is not listed separately."
                    ),
                },
                "tip": {
                    "type": "number",
                    "description": (
                        "Tip or gratuity amount if present on the receipt. "
                        "Look for labels like 'Tip', 'Gratuity', 'Service Charge'. "
                        "Common on restaurant receipts. May be handwritten. "
                        "Return null if no tip is listed or if the tip line is blank."
                    ),
                },
                "subtotal": {
                    "type": "number",
                    "description": (
                        "Subtotal before tax and tip, if listed separately. "
                        "Look for labels like 'Subtotal', 'Sub-total', 'Items Total'. "
                        "This is typically smaller than the total. "
                        "Return null if not listed separately."
                    ),
                },
            },
            "required": ["vendor", "total"],
        }

        logger.info("ade_parse_start | file=%s | model=%s", os.path.basename(image_path), ADE_MODEL)
        parse_result: Any = None

        if ade_module is not None:
            parse_fn = getattr(ade_module, "parse_document", None)
            if callable(parse_fn):
                try:
                    parse_result = parse_fn(image_path, model=ADE_MODEL, api_key=api_key)
                except TypeError:
                    try:
                        parse_result = parse_fn(image_path, model=ADE_MODEL)
                    except TypeError:
                        parse_result = parse_fn(image_path)
            else:
                raise RuntimeError("ADE module does not expose parse_document()")
        else:
            frame_set = None
            try:
                frame_set = frame_set_cls(api_key=api_key)  # type: ignore[misc]
            except TypeError:
                frame_set = frame_set_cls()  # type: ignore[misc]

            parse_fn = getattr(frame_set, "parse_document", None)
            if callable(parse_fn):
                try:
                    parse_result = parse_fn(image_path, model=ADE_MODEL)
                except TypeError:
                    parse_result = parse_fn(image_path)
            else:
                parse_fn_cls = getattr(frame_set_cls, "parse_document", None)
                parse_fn = getattr(frame_set_cls, "parse_document")
                if callable(parse_fn_cls):
                    try:
                
                        parse_result = parse_fn_cls(image_path, model=ADE_MODEL, api_key=api_key)
                    except TypeError:
                        parse_result = parse_fn_cls(image_path, model=ADE_MODEL)
                else:
                    raise RuntimeError("FrameSet API does not expose parse_document()")

        if not parse_result:
            raise RuntimeError("ADE parse returned no result")

        if isinstance(parse_result, dict):
            markdown = parse_result.get("markdown", "")
            chunks = parse_result.get("chunks", []) or []
        else:
            markdown = getattr(parse_result, "markdown", "") or ""
            chunks = getattr(parse_result, "chunks", []) or []

        logger.info("ade_parse_complete | chunk_count=%s | file=%s", len(chunks), os.path.basename(image_path))
        logger.debug("ade_parse_preview | markdown_head=%r", markdown[:200])

        logger.info("ade_extract_start | file=%s", os.path.basename(image_path))
        extract_result: Any = None

        if ade_module is not None:
            extract_fn = getattr(ade_module, "extract_data", None)
            if callable(extract_fn):
                try:
                    extract_result = extract_fn(markdown=markdown, schema=receipt_schema, api_key=api_key)
                except TypeError:
                    try:
                        extract_result = extract_fn(markdown=markdown, schema=receipt_schema)
                    except TypeError:
                        extract_result = extract_fn(markdown, receipt_schema)
            else:
                raise RuntimeError("ADE module does not expose extract_data()")
        else:
            frame_set = None
            try:
                frame_set = frame_set_cls(api_key=api_key)  # type: ignore[misc]
            except TypeError:
                frame_set = frame_set_cls()  # type: ignore[misc]

            extract_fn = getattr(frame_set, "extract_data", None)
            if callable(extract_fn):
                try:
                    extract_result = extract_fn(markdown=markdown, schema=receipt_schema)
                except TypeError:
                    extract_result = extract_fn(markdown, receipt_schema)
            else:
                extract_fn_cls = getattr(frame_set_cls, "extract_data", None)
                if callable(extract_fn_cls):
                    try:
                        extract_result = extract_fn_cls(markdown=markdown, schema=receipt_schema, api_key=api_key)
                    except TypeError:
                        extract_result = extract_fn_cls(markdown=markdown, schema=receipt_schema)
                else:
                    raise RuntimeError("FrameSet API does not expose extract_data()")

        if extract_result is None:
            raise RuntimeError("ADE extract returned no result")

        if not isinstance(extract_result, dict):
            # Support objects that expose field-like attributes.
            extract_result = {
                "vendor": getattr(extract_result, "vendor", None),
                "total": getattr(extract_result, "total", None),
                "date": getattr(extract_result, "date", None),
                "tax": getattr(extract_result, "tax", None),
                "tip": getattr(extract_result, "tip", None),
                "subtotal": getattr(extract_result, "subtotal", None),
            }

        vendor_value = extract_result.get("vendor")
        if not vendor_value:
            logger.warning("ade_extract_warning | field=vendor | reason='missing' | fallback='UNKNOWN'")
            vendor_value = "UNKNOWN"

        total_raw = extract_result.get("total")
        total_value = _safe_float(total_raw)
        if total_value is None:
            logger.warning("ade_extract_warning | field=total | reason='missing_or_invalid' | fallback=0.0")
            total_value = 0.0

        chunk_ids: list[str] = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                chunk_id = chunk.get("chunk_id") or chunk.get("id")
            else:
                chunk_id = getattr(chunk, "chunk_id", None) or getattr(chunk, "id", None)
            if chunk_id:
                chunk_ids.append(str(chunk_id))

        confidence = _compute_confidence(extract_result=extract_result, chunks=chunks)
        receipt = ReceiptData(
            vendor=str(vendor_value),
            total=float(total_value),
            date=extract_result.get("date"),
            tax=_safe_float(extract_result.get("tax")),
            tip=_safe_float(extract_result.get("tip")),
            subtotal=_safe_float(extract_result.get("subtotal")),
            currency="USD",
            confidence=confidence,
            chunk_ids=chunk_ids,
            raw_text=markdown[:1000] if markdown else None,
        )
        logger.info(
            "ade_extract_complete | vendor=%r | total=%.2f | confidence=%.0f%% | chunk_ids=%s | file=%s",
            receipt.vendor,
            receipt.total,
            receipt.confidence * 100,
            len(chunk_ids),
            os.path.basename(image_path),
        )
        return receipt
    except ImportError:
        raise
    except Exception as exc:
        logger.error(
            "ade_extract_error | file=%s | error_type=%s | error=%s",
            image_path,
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return ReceiptData(
            vendor="EXTRACTION_FAILED",
            total=0.0,
            confidence=0.1,
            raw_text=f"ADE extraction failed: {exc}",
        )


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert a value to float, returning None if not possible."""
    if value is None:
        return None
    try:
        result = float(value)
        return result if result >= 0 else None
    except (ValueError, TypeError):
        return None


def _compute_confidence(extract_result: dict, chunks: list) -> float:
    """Estimate extraction confidence based on field completeness.

    Heuristic:
    - Start at 1.0
    - Deduct 0.15 if vendor is missing or "UNKNOWN"
    - Deduct 0.15 if total is missing or 0
    - Deduct 0.10 if date is missing
    - Deduct 0.05 if no chunks found (no grounding possible)
    - Clamp to [0.1, 1.0]

    This is a rough heuristic. ADE may provide its own confidence scores in
    future versions, which would replace this logic.
    """
    score = 1.0

    vendor = extract_result.get("vendor") if isinstance(extract_result, dict) else None
    total = extract_result.get("total") if isinstance(extract_result, dict) else None
    date = extract_result.get("date") if isinstance(extract_result, dict) else None

    if not vendor or str(vendor).strip().upper() == "UNKNOWN":
        score -= 0.15
    if _safe_float(total) in (None, 0.0):
        score -= 0.15
    if not date:
        score -= 0.10
    if not chunks:
        score -= 0.05

    return max(0.1, min(1.0, score))


def _extract_mock(image_path: str) -> ReceiptData:
    """Return hardcoded mock `ReceiptData` based on receipt filename patterns.

    This function powers the no-API fallback path and is intentionally kept in
    production, not just test code. It enables full pipeline execution
    (normalize -> match -> diagnose -> explain) when `VISION_AGENT_API_KEY` is
    not configured.

    Recognized mock cases:
    - receipt_01 / clean_match / amazon:
      Clean match baseline against TXN001.
    - receipt_02 / vendor_mismatch / agave:
      Vendor descriptor mismatch against TXN002.
    - receipt_03 / tip_tax / starbucks:
      Tip/tax variance threshold edge case against TXN003.
    - receipt_04 / settlement / home_depot:
      Settlement delay archetype against TXN004.
    - receipt_05 / combined / fastenal:
      Compound mismatch + low extraction confidence against TXN005.
    - receipt_06 / no_match / bobs / hardware:
      No-match scenario with no valid transaction candidate.

    Matching strategy:
    - Uses lowercase basename from `image_path`.
    - Searches for known key substrings in the filename.
    - Supports flexible naming (not restricted to exact canonical filenames).

    Fallback behavior:
    - If no key matches, returns a low-confidence default `ReceiptData`
      (`vendor='Unknown Vendor'`, `total=0.0`, `confidence=0.3`) and logs a
      warning with known match patterns.

    Args:
        image_path: Path to the receipt image placeholder.

    Returns:
        ReceiptData: Fixture data for the matched test case, or low-confidence
        default when no match key is found.

    Examples:
        _extract_mock("test_data/receipts/receipt_02_vendor_mismatch.png")
        _extract_mock("C:/tmp/vendor_mismatch_test.png")
        _extract_mock("./el_agave_receipt.jpg")
    """
    if image_path is None:
        filename = ""
    else:
        filename = os.path.basename(str(image_path)).lower()

    receipt_01 = ReceiptData(
        vendor="Amazon.com",
        total=89.97,
        date="2026-01-10",
        tax=5.97,
        tip=None,
        subtotal=84.00,
        currency="USD",
        confidence=0.98,
        chunk_ids=["chunk_001_vendor", "chunk_002_total", "chunk_003_date"],
        raw_text=(
            "Amazon.com\nOrder #112-4837264-9182736\n\n"
            "Items: $84.00\nTax: $5.97\nTotal: $89.97\nDate: 01/10/2026"
        ),
    )
    receipt_02 = ReceiptData(
        vendor="El Agave Mexican Restaurant",
        total=47.50,
        date="2026-01-12",
        tax=3.50,
        tip=7.00,
        subtotal=37.00,
        currency="USD",
        confidence=0.95,
        chunk_ids=["chunk_010_vendor", "chunk_011_total", "chunk_012_date", "chunk_013_tip"],
        raw_text=(
            "El Agave Mexican Restaurant\n1847 Rossville Blvd\nChattanooga, TN 37408\n\n"
            "Chicken Enchiladas  $12.00\nSteak Fajitas       $18.00\nDrinks              $7.00\n\n"
            "Subtotal: $37.00\nTax:      $3.50\nTip:      $7.00\n\n"
            "Total:    $47.50\n\nDate: 01/12/2026\nServer: Maria"
        ),
    )
    receipt_03 = ReceiptData(
        vendor="Starbucks",
        total=5.25,
        date="2026-01-14",
        tax=0.35,
        tip=None,
        subtotal=4.90,
        currency="USD",
        confidence=0.97,
        chunk_ids=["chunk_020_vendor", "chunk_021_total"],
        raw_text=(
            "Starbucks #14892\nChattanooga, TN\n\n"
            "Grande Latte    $4.90\nTax             $0.35\n\n"
            "Total:          $5.25\n\n01/14/2026 08:42 AM"
        ),
    )
    receipt_04 = ReceiptData(
        vendor="Home Depot",
        total=234.67,
        date="2026-01-15",
        tax=18.67,
        tip=None,
        subtotal=216.00,
        currency="USD",
        confidence=0.96,
        chunk_ids=["chunk_030_vendor", "chunk_031_total", "chunk_032_date", "chunk_033_items"],
        raw_text=(
            "The Home Depot #4821\n6910 Lee Hwy\nChattanooga, TN 37421\n\n"
            "2x4x8 Lumber (x20)  $140.00\nDrywall Screws       $24.00\n"
            "Joint Compound       $32.00\nPaint Roller Kit     $20.00\n\n"
            "Subtotal: $216.00\nTax:      $18.67\nTotal:    $234.67\n\n01/15/2026 14:23"
        ),
    )
    receipt_05 = ReceiptData(
        vendor="Fastenal",
        total=178.23,
        date="2026-01-18",
        tax=13.23,
        tip=None,
        subtotal=165.00,
        currency="USD",
        confidence=0.72,
        chunk_ids=["chunk_040_vendor"],
        raw_text=(
            "Fast3nal\n    Industrial Supp1ies\n\n"
            "Bolts M8x40    $85.00\nWashers        $45.00\nAnch0r Kit     $35.00\n\n"
            "Subt0tal: $165.00\nTax:      $13.23\nT0tal:    $178.23\n\n01/18/2026"
        ),
    )
    receipt_06 = ReceiptData(
        vendor="Bob's Local Hardware",
        total=45.00,
        date="2026-01-22",
        tax=3.00,
        tip=None,
        subtotal=42.00,
        currency="USD",
        confidence=0.93,
        chunk_ids=["chunk_050_vendor", "chunk_051_total", "chunk_052_date"],
        raw_text=(
            "Bob's Local Hardware\n2847 Brainerd Rd\n\n"
            "Hammer       $15.00\nNails (1lb)  $8.00\nWD-40        $7.00\nDuct Tape    $12.00\n\n"
            "Subtotal: $42.00\nTax:      $3.00\nTotal:    $45.00\n\n01/22/2026"
        ),
    )
    receipt_07 = ReceiptData(
        vendor="Walgreens",
        total=23.47,
        date=None,
        tax=1.47,
        tip=None,
        subtotal=22.00,
        currency="USD",
        confidence=0.80,
        chunk_ids=["chunk_060_vendor", "chunk_061_total"],
        raw_text=(
            "Walgreens\n\nIbuprofen    $12.00\nBandages     $10.00\n\n"
            "Subtotal: $22.00\nTax: $1.47\nTotal: $23.47\n\n[date illegible]"
        ),
    )
    receipt_08 = ReceiptData(
        vendor="unclear",
        total=67.89,
        date="2026-01-14",
        tax=None,
        tip=None,
        subtotal=None,
        currency="USD",
        confidence=0.35,
        chunk_ids=[],
        raw_text="[mostly illegible thermal print]\n...$67.89...\n...01/14...",
    )
    receipt_09 = ReceiptData(
        vendor="Target",
        total=0.00,
        date="2026-01-15",
        tax=0.00,
        tip=None,
        subtotal=0.00,
        currency="USD",
        confidence=0.90,
        chunk_ids=["chunk_080_vendor"],
        raw_text="Target\n\nVOIDED TRANSACTION\n\nTotal: $0.00\n01/15/2026",
    )
    receipt_10 = ReceiptData(
        vendor="Café Résistance",
        total=18.75,
        date="2026-01-13",
        tax=1.25,
        tip=3.00,
        subtotal=14.50,
        currency="USD",
        confidence=0.92,
        chunk_ids=["chunk_090_vendor", "chunk_091_total"],
        raw_text=(
            "Café Résistance\n2847 Market St\n\nLatte    $5.50\nCroissant $9.00\n\n"
            "Subtotal: $14.50\nTax: $1.25\nTip: $3.00\nTotal: $18.75\n01/13/2026"
        ),
    )
    receipt_11 = ReceiptData(
        vendor="Amazon.com",
        total=89.97,
        date="2026-01-10",
        tax=5.97,
        tip=None,
        subtotal=84.00,
        currency="USD",
        confidence=0.98,
        chunk_ids=["chunk_100_vendor", "chunk_101_total"],
        raw_text=(
            "Amazon.com\nOrder #999-0000000-0000000\n\n"
            "Items: $84.00\nTax: $5.97\nTotal: $89.97\nDate: 01/10/2026"
        ),
    )

    mock_registry: dict[str, ReceiptData] = {
        "receipt_01": receipt_01,
        "clean_match": receipt_01,
        "amazon": receipt_01,
        "receipt_02": receipt_02,
        "vendor_mismatch": receipt_02,
        "agave": receipt_02,
        "receipt_03": receipt_03,
        "tip_tax": receipt_03,
        "starbucks": receipt_03,
        "receipt_04": receipt_04,
        "settlement": receipt_04,
        "home_depot": receipt_04,
        "homedepot": receipt_04,
        "receipt_05": receipt_05,
        "combined": receipt_05,
        "fastenal": receipt_05,
        "receipt_06": receipt_06,
        "no_match": receipt_06,
        "hardware": receipt_06,
        "bobs": receipt_06,
        "receipt_07": receipt_07,
        "no_date": receipt_07,
        "receipt_08": receipt_08,
        "blurry": receipt_08,
        "receipt_09": receipt_09,
        "voided": receipt_09,
        "receipt_10": receipt_10,
        "unicode": receipt_10,
        "cafe": receipt_10,
        "receipt_11": receipt_11,
        "duplicate": receipt_11,
    }

    result = None
    for key, receipt_data in mock_registry.items():
        if key in filename:
            result = receipt_data.model_copy(deep=True)
            break

    if result is None:
        logger.warning(
            "mock_extract_fallback | file=%s | fallback='Unknown Vendor low confidence default' | patterns=receipt_01..11",
            filename,
        )
        result = ReceiptData(
            vendor="Unknown Vendor",
            total=0.0,
            date=None,
            confidence=0.3,
            raw_text=f"[MOCK] No mock data configured for: {filename}",

        )

    try:
        ReceiptData.model_validate(result.model_dump())
    except Exception as exc:
        logger.error(
            "mock_extract_validation_error | file=%s | error=%s",
            filename,
            exc,
            exc_info=True,
        )
        return ReceiptData(
            vendor="MOCK_VALIDATION_ERROR",
            total=0.0,
            confidence=0.1,

            raw_text=f"Mock validation error: {exc}",
        )

    logger.info(
        "mock_extract_complete | vendor=%r | total=%.2f | date=%s | confidence=%.0f%% | file=%s",
        result.vendor,
        result.total,
        result.date,
        result.confidence * 100.0,
        filename,
    )
    return result

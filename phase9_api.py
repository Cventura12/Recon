"""
phase9_api.py - FastAPI HTTP layer for the diagnostic accounting agent.

Phase 9 scope:
- Expose existing pipeline through HTTP.
- Provide only two API endpoints:
  - POST /diagnose
  - GET /health

No matching/diagnosis business logic is implemented here.
"""

from __future__ import annotations

import base64
import copy
import os
import secrets
import tempfile
import threading
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import uvicorn
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from diagnose import diagnose
from explain import format_explanation_json
from extract import extract_receipt
from logging_config import get_logger, setup_logging
from main import load_transactions
from match import find_matches
from models import ReceiptData
from workspace_store import WorkspaceState, WorkspaceStore

logger = get_logger("phase9-api")

app = FastAPI(
    title="Accounting Exception Diagnostics API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Allows local UI use from file:// or another local host/port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

NEXT_CHECK_HINTS: dict[str, str] = {
    "settlement_delay": "Check posting vs settlement date window.",
    "tip_tax_variance": "Check for tip/tax not itemized on the receipt.",
    "vendor_descriptor_mismatch": "Check parent descriptor or merchant alias mapping.",
    "no_match": "Check date window, export completeness, or different card/account.",
    "partial_match": "Review vendor, amount delta, and posting date together for context.",
}
DEFAULT_PREVIEW_MAX_BYTES = 3 * 1024 * 1024
DEBUG_PREVIEW_MAX_BYTES = 15 * 1024 * 1024
WORKBENCH_EXCEPTION_STATES = {
    "PROBABLE_MATCH",
    "POSSIBLE_MATCH",
    "NO_CONFIDENT_MATCH",
}


class ExceptionQueue:
    """In-memory queue of diagnosed exceptions (resets on server restart)."""

    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []
        self._counter = 0
        self._lock = threading.Lock()

    @staticmethod
    def _status_from_payload(payload: dict[str, Any]) -> str:
        status = str(payload.get("status", "")).strip().lower()
        if status == "clean_match":
            return "CLEAN_MATCH"

        ui = payload.get("ui") or {}
        raw = str(ui.get("match_state_badge", "")).strip().upper()
        if raw == "PROBABLE":
            return "PROBABLE_MATCH"
        if raw == "POSSIBLE":
            return "POSSIBLE_MATCH"
        return "NO_CONFIDENT_MATCH"

    @staticmethod
    def _diagnosis_from_payload(payload: dict[str, Any]) -> str:
        diagnosis_section = payload.get("diagnosis") or {}
        labels = diagnosis_section.get("labels") or []
        if isinstance(labels, list) and labels:
            first = str(labels[0]).strip().upper()
            if first:
                return first

        summary = str(diagnosis_section.get("label_summary", "")).strip()
        if not summary:
            return "UNCLASSIFIED"
        return summary.upper().replace(" ", "_")

    @staticmethod
    def _candidate_or_receipt(payload: dict[str, Any]) -> tuple[str, float, str, str]:
        top_match = payload.get("top_match") or {}
        receipt = payload.get("receipt") or {}

        merchant = str(top_match.get("merchant") or receipt.get("vendor") or "Unknown")
        vendor = str(receipt.get("vendor") or "")
        amount_raw = top_match.get("amount", receipt.get("total", 0.0))
        date_raw = top_match.get("date", receipt.get("date", ""))

        try:
            amount = round(float(amount_raw), 2)
        except (TypeError, ValueError):
            amount = 0.0

        date = str(date_raw or "")
        return merchant, amount, date, vendor

    @staticmethod
    def _confidence_fields(payload: dict[str, Any]) -> tuple[float, int]:
        try:
            confidence_pct = round(float(payload.get("confidence", 0.0)), 1)
        except (TypeError, ValueError):
            confidence_pct = 0.0
        confidence_ratio = round(confidence_pct / 100.0, 4)
        return confidence_ratio, int(round(confidence_pct))

    def add_exception(self, item: dict[str, Any]) -> dict[str, Any]:
        """Insert a queue item with generated id into in-memory storage."""
        try:
            amount_value = round(float(item.get("amount", 0.0) or 0.0), 2)
        except (TypeError, ValueError):
            amount_value = 0.0
        try:
            confidence_value = round(float(item.get("confidence", 0.0) or 0.0), 4)
        except (TypeError, ValueError):
            confidence_value = 0.0
        try:
            confidence_pct_value = int(round(float(item.get("confidence_pct", 0.0) or 0.0)))
        except (TypeError, ValueError):
            confidence_pct_value = 0

        with self._lock:
            self._counter += 1
            item_id = f"ex_{self._counter:03d}"
            record = {
                "id": item_id,
                "merchant": str(item.get("merchant") or "Unknown"),
                "vendor": str(item.get("vendor") or ""),
                "amount": amount_value,
                "date": str(item.get("date") or ""),
                "match_state": str(item.get("match_state") or "NO_CONFIDENT_MATCH"),
                "diagnosis": str(item.get("diagnosis") or "UNCLASSIFIED"),
                "confidence": confidence_value,
                "confidence_pct": confidence_pct_value,
                "session_id": str(item.get("session_id") or "sess_manual"),
                "created_at": str(item.get("created_at") or datetime.now(timezone.utc).isoformat()),
                "result_payload": copy.deepcopy(item.get("result_payload") or {}),
            }
            self._items.append(record)
            return copy.deepcopy(record)

    def add_payload(self, payload: dict[str, Any], session_id: str = "sess_manual") -> dict[str, Any]:
        """Convert diagnosis payload to queue item and store it."""
        if not isinstance(payload, dict):
            raise ValueError("Queue payload must be a JSON object.")

        merchant, amount, date, vendor = self._candidate_or_receipt(payload)
        confidence_ratio, confidence_pct = self._confidence_fields(payload)
        diagnosis = self._diagnosis_from_payload(payload)
        match_state = self._status_from_payload(payload)
        return self.add_exception(
            {
                "merchant": merchant,
                "vendor": vendor,
                "amount": amount,
                "date": date,
                "match_state": match_state,
                "diagnosis": diagnosis,
                "confidence": confidence_ratio,
                "confidence_pct": confidence_pct,
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "result_payload": payload,
            }
        )

    def add(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Backward-compatible alias used by existing Phase 10 endpoints/UI."""
        return self.add_payload(payload=payload, session_id="sess_manual")

    def list_summaries(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": item["id"],
                    "merchant": item["merchant"],
                    "vendor": item["vendor"],
                    "amount": item["amount"],
                    "date": item["date"],
                    "match_state": item["match_state"],
                    "diagnosis": item["diagnosis"],
                    "confidence": item["confidence"],
                    "confidence_pct": item["confidence_pct"],
                    "session_id": item["session_id"],
                    "created_at": item["created_at"],
                }
                for item in self._items
            ]

    def get_payload(self, item_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            for item in self._items:
                if item["id"] == item_id:
                    return copy.deepcopy(item["result_payload"])
        return None

    def clear(self) -> None:
        with self._lock:
            self._items = []
            self._counter = 0

    def clear_session(self, session_id: str) -> int:
        """Remove all queue items belonging to the given session_id."""
        with self._lock:
            before = len(self._items)
            self._items = [item for item in self._items if item.get("session_id") != session_id]
            return before - len(self._items)

    def export_records(self) -> list[dict[str, Any]]:
        """Return full queue records including payload for workspace persistence."""
        with self._lock:
            return copy.deepcopy(self._items)

    def load_records(self, records: list[dict[str, Any]]) -> None:
        """Hydrate queue from persisted records and restore counter."""
        if not isinstance(records, list):
            records = []

        loaded: list[dict[str, Any]] = []
        max_counter = 0

        for raw in records:
            if not isinstance(raw, dict):
                continue

            item_id = str(raw.get("id") or "").strip()
            if not item_id:
                item_id = f"ex_{len(loaded) + 1:03d}"

            match = re.match(r"^ex_(\d+)$", item_id)
            if match:
                try:
                    max_counter = max(max_counter, int(match.group(1)))
                except ValueError:
                    pass

            try:
                amount = round(float(raw.get("amount", 0.0) or 0.0), 2)
            except (TypeError, ValueError):
                amount = 0.0
            try:
                confidence = round(float(raw.get("confidence", 0.0) or 0.0), 4)
            except (TypeError, ValueError):
                confidence = 0.0
            try:
                confidence_pct = int(round(float(raw.get("confidence_pct", 0.0) or 0.0)))
            except (TypeError, ValueError):
                confidence_pct = 0

            loaded.append(
                {
                    "id": item_id,
                    "merchant": str(raw.get("merchant") or "Unknown"),
                    "vendor": str(raw.get("vendor") or ""),
                    "amount": amount,
                    "date": str(raw.get("date") or ""),
                    "match_state": str(raw.get("match_state") or "NO_CONFIDENT_MATCH"),
                    "diagnosis": str(raw.get("diagnosis") or "UNCLASSIFIED"),
                    "confidence": confidence,
                    "confidence_pct": confidence_pct,
                    "session_id": str(raw.get("session_id") or "sess_manual"),
                    "created_at": str(raw.get("created_at") or datetime.now(timezone.utc).isoformat()),
                    "result_payload": copy.deepcopy(raw.get("result_payload") or {}),
                }
            )

        with self._lock:
            self._items = loaded
            self._counter = max_counter if max_counter > 0 else len(loaded)

    def list_sessions(self) -> list[dict[str, Any]]:
        """Return in-memory session summaries for lightweight UI controls."""
        with self._lock:
            groups: dict[str, dict[str, Any]] = {}
            for item in self._items:
                sid = str(item.get("session_id") or "sess_manual")
                created = str(item.get("created_at") or "")
                if sid not in groups:
                    groups[sid] = {
                        "session_id": sid,
                        "count": 0,
                        "latest_created_at": created,
                    }
                groups[sid]["count"] += 1
                if created > groups[sid]["latest_created_at"]:
                    groups[sid]["latest_created_at"] = created

            sessions = list(groups.values())
            sessions.sort(key=lambda item: item["latest_created_at"], reverse=True)
            return sessions


exception_queue = ExceptionQueue()
workspace_store = WorkspaceStore()
workspace_state = workspace_store.load_workspace()
exception_queue.load_records(workspace_state.workbench_queue)


def _workspace_snapshot() -> WorkspaceState:
    """Build current workspace snapshot using queue + persisted review metadata."""
    state_copy = workspace_state.model_copy(deep=True)
    state_copy.workspace_id = "default"
    state_copy.workbench_queue = exception_queue.export_records()
    return state_copy


def _persist_workspace_snapshot() -> None:
    """Persist current workspace snapshot to local storage file."""
    workspace_store.save_workspace(_workspace_snapshot())


async def _save_upload(upload: UploadFile, destination: Path) -> None:
    """Save an UploadFile to disk."""
    try:
        with destination.open("wb") as out_file:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                out_file.write(chunk)
    finally:
        await upload.close()


def _is_debug_enabled() -> bool:
    """Return True when DEBUG mode is enabled via environment variable."""
    return os.getenv("DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _build_candidate_view(matches: list[Any]) -> list[dict[str, Any]]:
    """Build UI-friendly candidate structures from MatchCandidate objects."""
    view: list[dict[str, Any]] = []
    for candidate in matches:
        view.append(
            {
                "merchant": candidate.transaction.merchant,
                "amount": round(float(candidate.transaction.amount), 2),
                "date": candidate.transaction.date,
                "transaction_id": candidate.transaction.transaction_id,
                "description": candidate.transaction.description,
                "overall_confidence": round(float(candidate.overall_confidence), 1),
                "vendor_similarity_score": round(float(candidate.vendor_score), 1),
                "amount_delta": round(float(candidate.amount_diff), 2),
                "amount_delta_pct": round(float(candidate.amount_pct_diff), 1),
                "date_delta_days": int(candidate.date_diff),
                "evidence": list(candidate.evidence),
            }
        )
    return view


def _match_state_badge(status: str, confidence: float) -> str:
    """Map status/confidence to operator-friendly match-state badge."""
    if status == "no_match":
        return "NO CONFIDENT"
    if confidence >= 80:
        return "PROBABLE"
    if confidence >= 50:
        return "POSSIBLE"
    return "NO CONFIDENT"


def _deterministic_next_checks(labels: list[str]) -> list[str]:
    """Return deterministic 'what to check next' hints from diagnosis labels."""
    if not labels:
        return ["Check whether the matched transaction already has supporting documentation attached."]
    checks: list[str] = []
    for label in labels:
        hint = NEXT_CHECK_HINTS.get(label)
        if hint and hint not in checks:
            checks.append(hint)
    return checks


def _bbox_to_object(bbox: Any) -> Optional[dict[str, Any]]:
    """Convert bbox payload to normalized dict format if possible."""
    if not bbox:
        return None
    if isinstance(bbox, dict):
        try:
            x = float(bbox["x"])
            y = float(bbox["y"])
            width = float(bbox["width"])
            height = float(bbox["height"])
        except (KeyError, TypeError, ValueError):
            return None
        normalized = bool(bbox.get("normalized", False))
    elif isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        try:
            x = float(bbox[0])
            y = float(bbox[1])
            width = float(bbox[2])
            height = float(bbox[3])
        except (TypeError, ValueError):
            return None
        normalized = max(x, y, width, height) <= 1.0
    else:
        return None

    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "normalized": normalized,
    }


def _scale_bbox_for_display(
    bbox: dict[str, Any],
    natural_width: float,
    natural_height: float,
    display_width: float,
    display_height: float,
) -> dict[str, float]:
    """Scale a grounding bounding box to rendered image pixel coordinates."""
    x = float(bbox["x"])
    y = float(bbox["y"])
    width = float(bbox["width"])
    height = float(bbox["height"])
    normalized = bool(bbox.get("normalized", False))

    if normalized:
        return {
            "x": x * display_width,
            "y": y * display_height,
            "width": width * display_width,
            "height": height * display_height,
        }

    x_scale = display_width / max(float(natural_width), 1.0)
    y_scale = display_height / max(float(natural_height), 1.0)
    return {
        "x": x * x_scale,
        "y": y * y_scale,
        "width": width * x_scale,
        "height": height * y_scale,
    }


def _build_grounding_view(payload: dict[str, Any]) -> dict[str, Any]:
    """Build field-grounding structure for Vendor/Date/Total evidence viewer."""
    receipt_payload = payload.get("receipt") or {}
    grounding_list = receipt_payload.get("grounding") or []

    fields: dict[str, dict[str, Any]] = {
        "vendor": {
            "field": "vendor",
            "value": receipt_payload.get("vendor"),
            "chunk_ids": [],
            "bounding_boxes": [],
            "available": False,
        },
        "date": {
            "field": "date",
            "value": receipt_payload.get("date"),
            "chunk_ids": [],
            "bounding_boxes": [],
            "available": False,
        },
        "total": {
            "field": "total",
            "value": receipt_payload.get("total"),
            "chunk_ids": [],
            "bounding_boxes": [],
            "available": False,
        },
    }

    for item in grounding_list:
        field_name = str(item.get("field", "")).strip().lower()
        if field_name not in fields:
            continue
        chunk_ids = item.get("chunk_ids") or []
        fields[field_name]["chunk_ids"] = [str(chunk_id) for chunk_id in chunk_ids]
        fields[field_name]["available"] = len(fields[field_name]["chunk_ids"]) > 0

        bbox_obj = _bbox_to_object(item.get("bounding_box"))
        if bbox_obj is not None:
            fields[field_name]["bounding_boxes"].append(bbox_obj)
            fields[field_name]["available"] = True

    has_bbox = any(fields[key]["bounding_boxes"] for key in fields)
    return {
        "fields": fields,
        "has_grounding": any(field_data["available"] for field_data in fields.values()),
        "has_bounding_boxes": has_bbox,
        "message": None if has_bbox else "Grounding not available for this extraction.",
    }


def _build_receipt_preview(
    receipt_path: Path,
    receipt_upload: UploadFile,
    debug_enabled: bool,
) -> dict[str, Any]:
    """Build optional receipt preview payload for UI grounding viewer."""
    content_type = receipt_upload.content_type or ""
    preview: dict[str, Any] = {
        "enabled": False,
        "mime_type": content_type,
        "image_data_url": None,
        "message": "Receipt preview unavailable for this upload.",
    }

    if not content_type.startswith("image/"):
        preview["enabled"] = False
        preview["message"] = "Receipt preview is only available for image uploads."
        return preview

    try:
        raw = receipt_path.read_bytes()
        max_bytes = DEBUG_PREVIEW_MAX_BYTES if debug_enabled else DEFAULT_PREVIEW_MAX_BYTES
        if len(raw) > max_bytes:
            preview["enabled"] = False
            preview["message"] = (
                f"Receipt preview omitted because file size exceeds {max_bytes // (1024 * 1024)}MB."
            )
            return preview

        encoded = base64.b64encode(raw).decode("ascii")
        preview["enabled"] = True
        preview["image_data_url"] = f"data:{content_type};base64,{encoded}"
        preview["message"] = None
        return preview
    except Exception as exc:
        logger.warning(
            "api_receipt_preview_warning | error_type=%s | error=%s | fallback='no preview'",
            type(exc).__name__,
            exc,
        )
        preview["enabled"] = False
        preview["message"] = "Receipt preview unavailable for this upload."
        return preview


def _default_receipt_preview() -> dict[str, Any]:
    """Receipt preview placeholder used for queue/session flows without images."""
    return {
        "enabled": False,
        "mime_type": "",
        "image_data_url": None,
        "message": "Receipt preview omitted for this workbench item.",
    }


def _enrich_payload_ui(payload: dict[str, Any], matches: list[Any], receipt_preview: dict[str, Any]) -> dict[str, Any]:
    """Attach UI envelope fields used by the web operator interface."""
    candidate_view = _build_candidate_view(matches)
    labels = payload.get("diagnosis", {}).get("labels", [])
    payload["ui"] = {
        "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "match_state": payload.get("status", "match_found"),
        "match_state_badge": _match_state_badge(
            str(payload.get("status", "")),
            float(payload.get("confidence", 0.0)),
        ),
        "diagnosis_label": payload.get("diagnosis", {}).get("label_summary", "Unclassified"),
        "diagnosis_summary": (
            f"{payload.get('diagnosis', {}).get('label_summary', 'Unclassified')} "
            f"({payload.get('confidence', 0.0):.1f}%)"
        ),
        "top_candidate": candidate_view[0] if candidate_view else None,
        "other_candidates": candidate_view[1:],
        "next_checks": _deterministic_next_checks(labels if isinstance(labels, list) else []),
        "grounding_view": _build_grounding_view(payload),
        "receipt_preview": receipt_preview,
    }
    return payload


def _generate_session_id() -> str:
    """Return short deterministic-looking random session id for queue grouping."""
    return f"sess_{secrets.token_hex(2)}"


def _build_no_match_payload_from_row(row: pd.Series) -> dict[str, Any]:
    """Build a deterministic NO_MATCH diagnosis payload for a transaction row."""
    merchant = str(row.get("merchant", "") or "Unknown Merchant")
    date_value = row.get("date")
    date_str = str(date_value) if pd.notna(date_value) else None
    amount_raw = row.get("amount")
    try:
        amount = float(amount_raw) if pd.notna(amount_raw) else 0.0
    except (TypeError, ValueError):
        amount = 0.0

    receipt = ReceiptData(
        vendor=merchant,
        total=max(0.0, amount),
        date=date_str,
        confidence=1.0,
    )
    diagnosis_result = diagnose([], receipt)
    payload = format_explanation_json(diagnosis_result)
    return _enrich_payload_ui(payload, matches=[], receipt_preview=_default_receipt_preview())


def _manual_total_to_float(manual_total: str) -> float:
    """Parse manual total safely."""
    cleaned = manual_total.strip().replace("$", "").replace(",", "")
    if not cleaned:
        raise ValueError("manual_total was empty after trimming")
    value = float(cleaned)
    if value < 0:
        raise ValueError("manual_total cannot be negative")
    return round(value, 2)


def _apply_manual_overrides(
    receipt: ReceiptData,
    manual_vendor: Optional[str],
    manual_date: Optional[str],
    manual_total: Optional[str],
) -> ReceiptData:
    """Apply optional manual field overrides to extracted receipt data."""
    data = receipt.model_dump()

    if manual_vendor is not None and manual_vendor.strip():
        data["vendor"] = manual_vendor.strip()

    if manual_date is not None and manual_date.strip():
        data["date"] = manual_date.strip()

    if manual_total is not None and manual_total.strip():
        try:
            data["total"] = _manual_total_to_float(manual_total)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid manual_total: {exc}") from exc

    return ReceiptData.model_validate(data)


def _run_pipeline_for_receipt(
    receipt: ReceiptData,
    transactions_df: pd.DataFrame,
    receipt_preview: dict[str, Any],
) -> tuple[dict[str, Any], list[Any]]:
    """Run deterministic match+diagnose+explain for prepared receipt data."""
    matches = find_matches(receipt, transactions_df)
    diagnosis_result = diagnose(matches, receipt)
    payload = format_explanation_json(diagnosis_result)
    return _enrich_payload_ui(payload, matches=matches, receipt_preview=receipt_preview), matches


@app.get("/health")
def health() -> dict[str, str]:
    """Service health check."""
    return {"status": "ok"}


@app.get("/workspace/load")
def workspace_load() -> dict[str, Any]:
    """Load the persisted default workspace snapshot."""
    global workspace_state

    loaded = workspace_store.load_workspace()
    workspace_state = loaded.model_copy(deep=True)
    exception_queue.load_records(workspace_state.workbench_queue)
    snapshot = _workspace_snapshot()
    return snapshot.model_dump(mode="json")


@app.post("/workspace/save")
def workspace_save(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Save full workspace snapshot (single-workspace prototype)."""
    global workspace_state

    try:
        incoming = WorkspaceState.model_validate(payload)
        incoming.workspace_id = "default"
        workspace_state = incoming.model_copy(deep=True)
        exception_queue.load_records(workspace_state.workbench_queue)
        _persist_workspace_snapshot()
        return _workspace_snapshot().model_dump(mode="json")
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "workspace_save_error | error_type=%s | error=%s",
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to save workspace.") from exc


@app.post("/workspace/reset")
def workspace_reset() -> dict[str, str]:
    """Reset persisted workspace and clear in-memory queue state."""
    global workspace_state

    workspace_store.reset_workspace()
    workspace_state = workspace_store.default_workspace()
    exception_queue.clear()
    return {"status": "reset"}


@app.get("/workbench")
def list_workbench_items() -> list[dict[str, Any]]:
    """Return in-memory exception queue summaries."""
    return exception_queue.list_summaries()


@app.get("/workbench/sessions")
def list_workbench_sessions() -> list[dict[str, Any]]:
    """Return lightweight summaries for currently loaded in-memory sessions."""
    return exception_queue.list_sessions()


@app.delete("/workbench/session/{session_id}")
def clear_workbench_session(session_id: str) -> dict[str, Any]:
    """Clear all queue items that belong to a specific session id."""
    removed = exception_queue.clear_session(session_id)
    if removed > 0:
        _persist_workspace_snapshot()
    return {"session_id": session_id, "removed": removed}


@app.post("/workbench/add")
def add_workbench_item(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Insert a diagnosis payload into the in-memory exception queue."""
    try:
        record = exception_queue.add_payload(payload, session_id="sess_manual")
        _persist_workspace_snapshot()
        return {
            "id": record["id"],
            "merchant": record["merchant"],
            "vendor": record["vendor"],
            "amount": record["amount"],
            "date": record["date"],
            "match_state": record["match_state"],
            "diagnosis": record["diagnosis"],
            "confidence": record["confidence"],
            "confidence_pct": record["confidence_pct"],
            "session_id": record["session_id"],
            "created_at": record["created_at"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "workbench_add_error | error_type=%s | error=%s",
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to add workbench item.") from exc


@app.post("/workbench/session-intake")
async def workbench_session_intake(
    transactions_csv: UploadFile = File(...),
    receipts: Optional[list[UploadFile]] = File(default=None),
) -> dict[str, Any]:
    """Run synchronous intake and add non-clean results to in-memory workbench queue."""
    if not transactions_csv.filename:
        raise HTTPException(status_code=400, detail="transactions_csv file is required.")

    with tempfile.TemporaryDirectory(prefix="workbench-session-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        csv_name = Path(transactions_csv.filename).name or "transactions.csv"
        csv_path = tmp_path / csv_name

        try:
            await _save_upload(transactions_csv, csv_path)
            transactions_df = load_transactions(str(csv_path))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to load transactions CSV: {exc}",
            ) from exc

        receipt_files = [upload for upload in (receipts or []) if upload and upload.filename]
        receipt_paths: list[Path] = []
        for idx, upload in enumerate(receipt_files):
            safe_name = Path(upload.filename).name or f"receipt_{idx + 1}.bin"
            upload_path = tmp_path / f"{idx + 1:03d}_{safe_name}"
            try:
                await _save_upload(upload, upload_path)
                receipt_paths.append(upload_path)
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to read receipt file '{safe_name}': {exc}",
                ) from exc

        session_id = _generate_session_id()
        total_processed = 0
        exceptions_added = 0

        for row_position, (idx, row) in enumerate(transactions_df.iterrows()):
            total_processed += 1
            try:
                if row_position < len(receipt_paths):
                    extracted = extract_receipt(str(receipt_paths[row_position]))
                    payload, _matches = _run_pipeline_for_receipt(
                        receipt=extracted,
                        transactions_df=transactions_df,
                        receipt_preview=_default_receipt_preview(),
                    )
                else:
                    payload = _build_no_match_payload_from_row(row)
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Session intake failed at row {idx}: {exc}",
                ) from exc

            match_state = exception_queue._status_from_payload(payload)
            if match_state in WORKBENCH_EXCEPTION_STATES:
                exception_queue.add_payload(payload=payload, session_id=session_id)
                exceptions_added += 1

        if exceptions_added > 0:
            _persist_workspace_snapshot()

        return {
            "session_id": session_id,
            "total_processed": total_processed,
            "exceptions_added": exceptions_added,
        }


@app.get("/workbench/{item_id}")
def get_workbench_item(item_id: str) -> dict[str, Any]:
    """Return full diagnosis payload for a queue item."""
    payload = exception_queue.get_payload(item_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Workbench item not found: {item_id}")
    return payload


@app.post("/diagnose")
async def diagnose_endpoint(
    receipt: UploadFile = File(...),
    csv: UploadFile = File(...),
    manual_vendor: Optional[str] = Form(default=None),
    manual_date: Optional[str] = Form(default=None),
    manual_total: Optional[str] = Form(default=None),
) -> JSONResponse:
    """Run the existing diagnostic pipeline and return structured JSON."""
    if not receipt.filename:
        raise HTTPException(status_code=400, detail="Receipt file is required.")
    if not csv.filename:
        raise HTTPException(status_code=400, detail="CSV file is required.")

    debug_enabled = _is_debug_enabled()

    with tempfile.TemporaryDirectory(prefix="diagnostic-agent-") as tmp_dir:
        tmp_path = Path(tmp_dir)

        receipt_name = Path(receipt.filename).name
        csv_name = Path(csv.filename).name
        if not receipt_name:
            receipt_name = f"receipt{Path(receipt.filename).suffix or '.bin'}"
        if not csv_name:
            csv_name = f"transactions{Path(csv.filename).suffix or '.csv'}"

        receipt_path = tmp_path / receipt_name
        csv_path = tmp_path / csv_name

        try:
            await _save_upload(receipt, receipt_path)
            await _save_upload(csv, csv_path)

            extracted = extract_receipt(str(receipt_path))
            prepared_receipt = _apply_manual_overrides(
                extracted,
                manual_vendor=manual_vendor,
                manual_date=manual_date,
                manual_total=manual_total,
            )

            transactions_df = load_transactions(str(csv_path))
            payload, matches = _run_pipeline_for_receipt(
                receipt=prepared_receipt,
                transactions_df=transactions_df,
                receipt_preview=_build_receipt_preview(receipt_path, receipt, debug_enabled),
            )

            if debug_enabled:
                payload["ui"]["debug_trace"] = {
                    "manual_overrides_used": {
                        "manual_vendor": bool(manual_vendor and manual_vendor.strip()),
                        "manual_date": bool(manual_date and manual_date.strip()),
                        "manual_total": bool(manual_total and manual_total.strip()),
                    },
                    "candidate_count": len(matches),
                    "debug_enabled": True,
                }

            return JSONResponse(content=payload)
        except HTTPException:
            raise
        except FileNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.error(
                "api_diagnose_error | error_type=%s | error=%s",
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Unexpected server error while processing diagnosis.",
            ) from exc


if __name__ == "__main__":
    setup_logging()
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("phase9_api:app", host="0.0.0.0", port=port, reload=False)

"""
inbox.py - Recon Inbox scanner + processed-manifest utilities (Phase 15).

Phase 15 scope:
- Scan a local folder drop inbox for one CSV + optional receipt files.
- Build a deterministic batch descriptor for ingestion.
- Archive processed files and track processed signatures for idempotency.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logging_config import get_logger

logger = get_logger(__name__)

SUPPORTED_RECEIPT_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".tiff",
    ".tif",
    ".bmp",
    ".webp",
}
SUPPORTED_CSV_EXTENSIONS = {".csv"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_mtime_ns(path: Path) -> int:
    try:
        return int(path.stat().st_mtime_ns)
    except Exception:
        return 0


def file_signature(path: Path) -> dict[str, Any]:
    """Return stable v1 signature metadata for idempotency checks."""
    stat = path.stat()
    return {
        "name": path.name,
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def signature_key(signature: dict[str, Any]) -> str:
    return f"{signature.get('name','')}::{signature.get('size',0)}::{signature.get('mtime_ns',0)}"


class InboxScanner:
    """File-system scanner for Recon Inbox folder-drop ingestion."""

    def __init__(self, inbox_path: str, archive_path: str, max_files_per_run: int = 50) -> None:
        self.inbox_path = Path(inbox_path).resolve()
        self.archive_path = Path(archive_path).resolve()
        self.max_files_per_run = max(1, int(max_files_per_run))
        self.manifest_path = self.archive_path / "manifest.json"
        self.ensure_directories()

    def ensure_directories(self) -> None:
        self.inbox_path.mkdir(parents=True, exist_ok=True)
        self.archive_path.mkdir(parents=True, exist_ok=True)

    def load_manifest(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            return {"processed": {}, "updated_at": None}
        try:
            raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            processed = raw.get("processed")
            if not isinstance(processed, dict):
                processed = {}
            return {
                "processed": processed,
                "updated_at": raw.get("updated_at"),
            }
        except Exception as exc:
            logger.warning(
                "inbox_manifest_load_warning | path=%s | error_type=%s | error=%s | fallback='empty'",
                self.manifest_path,
                type(exc).__name__,
                exc,
            )
            return {"processed": {}, "updated_at": None}

    def save_manifest(self, manifest: dict[str, Any]) -> None:
        self.archive_path.mkdir(parents=True, exist_ok=True)
        normalized = {
            "processed": manifest.get("processed", {}),
            "updated_at": _utc_now_iso(),
        }
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(self.archive_path),
            delete=False,
            prefix="manifest-",
            suffix=".tmp",
        ) as tmp_file:
            json.dump(normalized, tmp_file, ensure_ascii=False, indent=2)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            tmp_path = Path(tmp_file.name)
        os.replace(tmp_path, self.manifest_path)

    def _iter_inbox_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self.inbox_path.iterdir():
            if path.is_dir():
                continue
            if path.name.startswith("."):
                continue
            ext = path.suffix.lower()
            if ext in SUPPORTED_CSV_EXTENSIONS or ext in SUPPORTED_RECEIPT_EXTENSIONS:
                files.append(path)
        files.sort(key=lambda item: (_safe_mtime_ns(item), item.name), reverse=True)
        return files

    def _is_processed(self, path: Path, manifest: dict[str, Any]) -> bool:
        processed = manifest.get("processed", {})
        if not isinstance(processed, dict):
            return False
        key = signature_key(file_signature(path))
        return key in processed

    def scan_batch(self) -> dict[str, Any]:
        """Return deterministic inbox scan result with status + optional batch object."""
        discovered_at = _utc_now_iso()
        manifest = self.load_manifest()
        candidates = self._iter_inbox_files()
        if not candidates:
            return {
                "status": "NO_BATCH",
                "reason_code": "EMPTY_INBOX",
                "discovered_at": discovered_at,
                "new_files_count": 0,
                "batch": None,
            }

        fresh_files = [path for path in candidates if not self._is_processed(path, manifest)]
        if not fresh_files:
            return {
                "status": "NO_BATCH",
                "reason_code": "EMPTY_INBOX",
                "discovered_at": discovered_at,
                "new_files_count": 0,
                "batch": None,
            }

        csv_files = [path for path in fresh_files if path.suffix.lower() in SUPPORTED_CSV_EXTENSIONS]
        receipt_files = [path for path in fresh_files if path.suffix.lower() in SUPPORTED_RECEIPT_EXTENSIONS]

        if not csv_files:
            return {
                "status": "NO_BATCH",
                "reason_code": "MISSING_CSV",
                "discovered_at": discovered_at,
                "new_files_count": len(fresh_files),
                "batch": None,
            }

        selected_csv = csv_files[0]  # newest CSV by mtime desc
        receipts_sorted = sorted(receipt_files, key=lambda item: (_safe_mtime_ns(item), item.name), reverse=True)
        max_receipts = max(0, self.max_files_per_run - 1)
        selected_receipts = receipts_sorted[:max_receipts]

        batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{secrets.token_hex(2)}"
        batch_files = [selected_csv, *selected_receipts]
        batch = {
            "batch_id": batch_id,
            "csv_path": str(selected_csv),
            "receipt_paths": [str(path) for path in selected_receipts],
            "discovered_at": discovered_at,
            "counts": {
                "csv_files": 1,
                "receipt_files": len(selected_receipts),
                "batch_files": len(batch_files),
                "new_files": len(fresh_files),
            },
            "file_names": [path.name for path in batch_files],
            "signatures": [file_signature(path) for path in batch_files],
        }
        return {
            "status": "BATCH_FOUND",
            "reason_code": None,
            "discovered_at": discovered_at,
            "new_files_count": len(fresh_files),
            "batch": batch,
        }

    def archive_processed_batch(self, batch: dict[str, Any]) -> list[str]:
        """Move processed files to archive path and persist signatures to manifest."""
        batch_id = str(batch.get("batch_id") or "").strip()
        if not batch_id:
            raise ValueError("batch_id is required for archive.")

        target_dir = self.archive_path / batch_id
        target_dir.mkdir(parents=True, exist_ok=True)

        moved_file_names: list[str] = []
        file_names = batch.get("file_names", [])
        if not isinstance(file_names, list):
            file_names = []

        for name in file_names:
            safe_name = str(name).strip()
            if not safe_name:
                continue
            source = self.inbox_path / safe_name
            if not source.exists():
                continue
            destination = target_dir / safe_name
            if destination.exists():
                stem = destination.stem
                suffix = destination.suffix
                candidate = 1
                while True:
                    alt = target_dir / f"{stem}_{candidate}{suffix}"
                    if not alt.exists():
                        destination = alt
                        break
                    candidate += 1
            shutil.move(str(source), str(destination))
            moved_file_names.append(destination.name)

        signatures = batch.get("signatures", [])
        manifest = self.load_manifest()
        processed = manifest.get("processed")
        if not isinstance(processed, dict):
            processed = {}
        if isinstance(signatures, list):
            for signature in signatures:
                if not isinstance(signature, dict):
                    continue
                processed[signature_key(signature)] = signature
        manifest["processed"] = processed
        self.save_manifest(manifest)
        return moved_file_names

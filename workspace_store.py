"""
workspace_store.py - Simple persisted workspace storage for Phase 14.

Stores a single workspace snapshot in a local JSON file.
No auth, no multi-user state, no background workers.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from logging_config import get_logger

logger = get_logger(__name__)


class WorkspaceState(BaseModel):
    """Persisted state for the default workbench workspace."""

    model_config = ConfigDict(extra="ignore")

    workspace_id: str = "default"
    workbench_queue: list[dict[str, Any]] = Field(default_factory=list)
    resolution_state: dict[str, str] = Field(default_factory=dict)
    decision_notes: dict[str, str] = Field(default_factory=dict)
    alias_memory: dict[str, str] = Field(default_factory=dict)
    pattern_memory: dict[str, int] = Field(default_factory=dict)
    last_selected_exception_id: Optional[str] = None
    show_only_unresolved: bool = False
    updated_at: Optional[str] = None

    @field_validator("workspace_id", mode="before")
    @classmethod
    def _workspace_id_default(cls, value: Any) -> str:
        text = str(value or "").strip()
        return text or "default"

    @field_validator("resolution_state", mode="before")
    @classmethod
    def _normalize_resolution_state(cls, value: Any) -> dict[str, str]:
        source = value if isinstance(value, dict) else {}
        result: dict[str, str] = {}
        for key, raw in source.items():
            item_id = str(key).strip()
            if not item_id:
                continue
            text = str(raw or "").strip().lower()
            if text in {"accepted", "ignored", "follow_up", "unreviewed"}:
                result[item_id] = text
        return result

    @field_validator("decision_notes", mode="before")
    @classmethod
    def _normalize_decision_notes(cls, value: Any) -> dict[str, str]:
        source = value if isinstance(value, dict) else {}
        result: dict[str, str] = {}
        for key, raw in source.items():
            item_id = str(key).strip()
            if not item_id:
                continue
            text = str(raw or "")
            if text:
                result[item_id] = text
        return result

    @field_validator("alias_memory", mode="before")
    @classmethod
    def _normalize_alias_memory(cls, value: Any) -> dict[str, str]:
        source = value if isinstance(value, dict) else {}
        result: dict[str, str] = {}
        for key, raw in source.items():
            card_vendor = str(key or "").strip().upper()
            receipt_vendor = str(raw or "").strip()
            if card_vendor and receipt_vendor:
                result[card_vendor] = receipt_vendor
        return result

    @field_validator("pattern_memory", mode="before")
    @classmethod
    def _normalize_pattern_memory(cls, value: Any) -> dict[str, int]:
        source = value if isinstance(value, dict) else {}
        result: dict[str, int] = {}
        for key, raw in source.items():
            diagnosis = str(key or "").strip().upper()
            if not diagnosis:
                continue
            try:
                count = int(raw)
            except (TypeError, ValueError):
                continue
            if count >= 0:
                result[diagnosis] = count
        return result


class WorkspaceStore:
    """Disk-backed workspace store using one JSON file and atomic writes."""

    def __init__(self, path: Optional[str] = None) -> None:
        target = path or os.getenv("WORKSPACE_FILE", "data/workspace.json")
        self.path = Path(target).resolve()

    @staticmethod
    def default_workspace() -> WorkspaceState:
        return WorkspaceState(workspace_id="default")

    def load_workspace(self) -> WorkspaceState:
        """Load workspace from disk, returning defaults if missing/unreadable."""
        if not self.path.exists():
            return self.default_workspace()

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            state = WorkspaceState.model_validate(raw)
            state.workbench_queue = state.workbench_queue or []
            return state
        except Exception as exc:
            logger.warning(
                "workspace_load_warning | path=%s | error_type=%s | error=%s | fallback='default'",
                self.path,
                type(exc).__name__,
                exc,
            )
            return self.default_workspace()

    def save_workspace(self, state: WorkspaceState | dict[str, Any]) -> None:
        """Persist workspace atomically via temp-file + replace."""
        normalized = WorkspaceState.model_validate(state)
        normalized.updated_at = datetime.now(timezone.utc).isoformat()

        self.path.parent.mkdir(parents=True, exist_ok=True)

        payload = normalized.model_dump(mode="json")
        tmp_dir = str(self.path.parent)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=tmp_dir,
            delete=False,
            suffix=".tmp",
            prefix="workspace-",
        ) as tmp_file:
            json.dump(payload, tmp_file, ensure_ascii=False, indent=2)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            tmp_path = Path(tmp_file.name)

        os.replace(tmp_path, self.path)

    def reset_workspace(self) -> None:
        """Remove persisted workspace file if present."""
        try:
            if self.path.exists():
                self.path.unlink()
        except Exception as exc:
            logger.warning(
                "workspace_reset_warning | path=%s | error_type=%s | error=%s",
                self.path,
                type(exc).__name__,
                exc,
            )

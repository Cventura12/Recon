"""
test_phase14_workspace.py - Phase 14 persistence checks.

Usage:
    python test_phase14_workspace.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import phase9_api
from workspace_store import WorkspaceState, WorkspaceStore


def _symbols() -> tuple[str, str, str]:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        "✓✗═".encode(sys.stdout.encoding or "utf-8")
        return "✓", "✗", "═"
    except Exception:
        return "[OK]", "[FAIL]", "="


PASS, FAIL, LINE = _symbols()


def _configure_temp_workspace(path: Path) -> None:
    phase9_api.workspace_store = WorkspaceStore(str(path))
    phase9_api.workspace_state = phase9_api.workspace_store.default_workspace()
    phase9_api.exception_queue.clear()


def _sample_payload() -> dict:
    return {
        "status": "match_found",
        "confidence": 84.3,
        "diagnosis": {
            "labels": ["vendor_descriptor_mismatch"],
            "label_names": ["Vendor Descriptor Mismatch"],
            "label_summary": "Vendor Descriptor Mismatch",
            "is_compound": False,
            "is_clean_match": False,
        },
        "evidence": ["Vendor names differ."],
        "receipt": {
            "vendor": "El Agave Mexican Restaurant",
            "total": 47.50,
            "date": "2026-01-12",
        },
        "top_match": {
            "merchant": "ELAGAVE*1847 CHATT TN",
            "amount": 47.50,
            "date": "2026-01-12",
            "scores": {
                "vendor_score": 60.9,
                "amount_diff": 0.0,
                "amount_pct_diff": 0.0,
                "date_diff": 0,
                "overall_confidence": 84.3,
            },
        },
        "ui": {"match_state_badge": "POSSIBLE"},
    }


def main() -> None:
    passed = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"    {PASS} {name}")
        else:
            failed += 1
            print(f"    {FAIL} {name}")

    print(LINE * 62)
    print("  Phase 14: Workspace Persistence Tests")
    print(LINE * 62)

    with tempfile.TemporaryDirectory(prefix="phase14-workspace-") as tmp:
        root = Path(tmp)
        workspace_file = root / "workspace.json"

        print("\n  Store Save/Load:")
        store = WorkspaceStore(str(workspace_file))
        seed = WorkspaceState(
            workspace_id="default",
            workbench_queue=[{"id": "ex_001", "merchant": "A", "result_payload": {}}],
            resolution_state={"ex_001": "accepted"},
            decision_notes={"ex_001": "Confirmed by client."},
            alias_memory={"YUM! BRANDS": "Taco Bell"},
            pattern_memory={"TIP_TAX_VARIANCE": 3},
            show_only_unresolved=True,
            last_selected_exception_id="ex_001",
        )
        store.save_workspace(seed)
        loaded = store.load_workspace()
        check("Saving then loading returns identical queue", loaded.workbench_queue == seed.workbench_queue)
        check(
            "Saving then loading returns identical metadata",
            loaded.resolution_state == seed.resolution_state
            and loaded.decision_notes == seed.decision_notes
            and loaded.alias_memory == seed.alias_memory
            and loaded.pattern_memory == seed.pattern_memory
            and loaded.show_only_unresolved == seed.show_only_unresolved
            and loaded.last_selected_exception_id == seed.last_selected_exception_id,
        )

        print("\n  Missing Workspace File:")
        missing_store = WorkspaceStore(str(root / "missing.json"))
        missing = missing_store.load_workspace()
        check("Missing workspace file returns default empty state", missing.workspace_id == "default" and missing.workbench_queue == [])

        print("\n  Atomic Write:")
        atomic_store = WorkspaceStore(str(root / "atomic.json"))
        atomic_store.save_workspace(seed)
        tmp_leftovers = list(root.glob("workspace-*.tmp"))
        check("Atomic write creates final file", (root / "atomic.json").exists())
        check("Atomic write leaves no temp files", len(tmp_leftovers) == 0)

        print("\n  End-to-End API Save/Reload:")
        _configure_temp_workspace(workspace_file)
        client = TestClient(phase9_api.app)

        reset_response = client.post("/workspace/reset")
        check("POST /workspace/reset returns 200", reset_response.status_code == 200)

        add_response = client.post("/workbench/add", json=_sample_payload())
        check("POST /workbench/add returns 200", add_response.status_code == 200)
        added = add_response.json() if add_response.status_code == 200 else {}
        added_id = str(added.get("id") or "")

        load_before = client.get("/workspace/load")
        snapshot = load_before.json() if load_before.status_code == 200 else {}
        snapshot["resolution_state"] = {added_id: "accepted"} if added_id else {}
        snapshot["decision_notes"] = {added_id: "Client approved this mapping."} if added_id else {}
        save_response = client.post("/workspace/save", json=snapshot)
        check("POST /workspace/save returns 200", save_response.status_code == 200)

        phase9_api.exception_queue.clear()
        phase9_api.workspace_state = phase9_api.workspace_store.default_workspace()

        load_after = client.get("/workspace/load")
        loaded_snapshot = load_after.json() if load_after.status_code == 200 else {}
        queue_after = loaded_snapshot.get("workbench_queue", [])
        check("GET /workspace/load after restart returns 200", load_after.status_code == 200)
        check("Queue persists across reload", isinstance(queue_after, list) and len(queue_after) >= 1)
        check(
            "Resolution and notes persist across reload",
            loaded_snapshot.get("resolution_state", {}).get(added_id) == "accepted"
            and loaded_snapshot.get("decision_notes", {}).get(added_id) == "Client approved this mapping.",
        )

        workbench_after = client.get("/workbench")
        workbench_items = workbench_after.json() if workbench_after.status_code == 200 else []
        check("Queue rehydrates in-memory workbench", workbench_after.status_code == 200 and len(workbench_items) >= 1)

    print(f"\n{LINE * 62}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print(f"  Phase 14 workspace checks complete {PASS}")
    else:
        print(f"  Phase 14 workspace checks failed: {failed}")
    print(LINE * 62)


if __name__ == "__main__":
    main()

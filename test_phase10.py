"""
test_phase10.py - Phase 10 Exception Workbench API checks.

Usage:
    python test_phase10.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phase9_api import app, exception_queue


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
    print("  Phase 10: Exception Workbench Queue Tests")
    print(LINE * 62)

    base_dir = Path(__file__).resolve().parent
    receipt_path = base_dir / "test_data" / "receipts" / "receipt_02_vendor_mismatch.png"
    csv_path = base_dir / "test_data" / "transactions.csv"

    original_key = os.environ.pop("VISION_AGENT_API_KEY", None)
    exception_queue.clear()

    try:
        client = TestClient(app)

        response = client.get("/workbench")
        check("GET /workbench returns 200", response.status_code == 200)
        baseline_items = response.json() if response.status_code == 200 else []
        check("Queue starts empty", isinstance(baseline_items, list) and len(baseline_items) == 0)

        with receipt_path.open("rb") as receipt_file, csv_path.open("rb") as csv_file:
            diagnose_response = client.post(
                "/diagnose",
                files={
                    "receipt": ("receipt_02_vendor_mismatch.png", receipt_file, "image/png"),
                    "csv": ("transactions.csv", csv_file, "text/csv"),
                },
            )
        check("POST /diagnose returns 200", diagnose_response.status_code == 200)

        diagnose_payload = diagnose_response.json() if diagnose_response.status_code == 200 else {}
        add_response = client.post("/workbench/add", json=diagnose_payload)
        check("POST /workbench/add returns 200", add_response.status_code == 200)
        added = add_response.json() if add_response.status_code == 200 else {}
        added_id = added.get("id")
        check("Added item has queue id", isinstance(added_id, str) and added_id.startswith("ex_"))
        check("Added item includes match_state", "match_state" in added)
        check("Added item includes diagnosis", "diagnosis" in added)
        check("Added item includes confidence_pct", "confidence_pct" in added)

        list_after = client.get("/workbench")
        check("GET /workbench after add returns 200", list_after.status_code == 200)
        items_after = list_after.json() if list_after.status_code == 200 else []
        check("Queue has one item after add", isinstance(items_after, list) and len(items_after) == 1)
        check("Queue summary contains inserted id", any(item.get("id") == added_id for item in items_after))

        detail_response = client.get(f"/workbench/{added_id}")
        check("GET /workbench/{id} returns 200", detail_response.status_code == 200)
        detail_payload = detail_response.json() if detail_response.status_code == 200 else {}
        check("Detail payload has status", "status" in detail_payload)
        check("Detail payload has diagnosis section", "diagnosis" in detail_payload)

        missing_response = client.get("/workbench/ex_999")
        check("GET missing queue item returns 404", missing_response.status_code == 404)
    finally:
        if original_key is not None:
            os.environ["VISION_AGENT_API_KEY"] = original_key

    print(f"\n{LINE * 62}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print(f"  Phase 10 queue checks complete {PASS}")
    else:
        print(f"  Phase 10 queue checks failed: {failed}")
    print(f"{LINE * 62}")


if __name__ == "__main__":
    main()

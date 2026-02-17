"""
test_phase11_session_intake.py - Phase 11 session intake checks.

Usage:
    python test_phase11_session_intake.py
"""

from __future__ import annotations

import csv
import os
import sys
import tempfile
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


def _make_subset_csv(source_csv: Path, rows: int) -> Path:
    with source_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = list(csv.DictReader(handle))
    subset_rows = reader[:rows]

    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", newline="")
    with temp:
        writer = csv.DictWriter(temp, fieldnames=["merchant", "amount", "date", "description", "transaction_id"])
        writer.writeheader()
        writer.writerows(subset_rows)
    return Path(temp.name)


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
    print("  Phase 11: Session Intake Tests")
    print(LINE * 62)

    base_dir = Path(__file__).resolve().parent
    transactions_csv = base_dir / "test_data" / "transactions.csv"
    subset_csv = _make_subset_csv(transactions_csv, rows=2)

    original_key = os.environ.pop("VISION_AGENT_API_KEY", None)
    exception_queue.clear()

    try:
        client = TestClient(app)

        with transactions_csv.open("rb") as csv_file:
            intake_response = client.post(
                "/workbench/session-intake",
                files={
                    "transactions_csv": ("transactions.csv", csv_file, "text/csv"),
                },
            )
        check("POST /workbench/session-intake returns 200", intake_response.status_code == 200)

        intake_payload = intake_response.json() if intake_response.status_code == 200 else {}
        session_id_1 = intake_payload.get("session_id")
        total_processed = intake_payload.get("total_processed")
        exceptions_added = intake_payload.get("exceptions_added")

        check("Session id is returned", isinstance(session_id_1, str) and session_id_1.startswith("sess_"))
        check("Total processed equals CSV rows (10)", total_processed == 10)
        check("Exceptions added count is numeric", isinstance(exceptions_added, int))

        queue_response = client.get("/workbench")
        queue_items = queue_response.json() if queue_response.status_code == 200 else []
        check("GET /workbench returns 200", queue_response.status_code == 200)
        check("Queue length equals exceptions_added", len(queue_items) == exceptions_added)
        check(
            "Queue contains no CLEAN_MATCH states",
            all(str(item.get("match_state")) != "CLEAN_MATCH" for item in queue_items),
        )
        check(
            "Queue items include session_id and created_at",
            all(item.get("session_id") and item.get("created_at") for item in queue_items),
        )

        with subset_csv.open("rb") as subset_file:
            intake_response_2 = client.post(
                "/workbench/session-intake",
                files={
                    "transactions_csv": ("subset.csv", subset_file, "text/csv"),
                },
            )
        check("Second session intake returns 200", intake_response_2.status_code == 200)
        intake_payload_2 = intake_response_2.json() if intake_response_2.status_code == 200 else {}
        session_id_2 = intake_payload_2.get("session_id")
        exceptions_added_2 = intake_payload_2.get("exceptions_added")

        clear_response = client.delete(f"/workbench/session/{session_id_1}")
        clear_payload = clear_response.json() if clear_response.status_code == 200 else {}
        check("DELETE /workbench/session/{id} returns 200", clear_response.status_code == 200)
        check("Clear response removed count matches first session", clear_payload.get("removed") == exceptions_added)

        queue_after_clear = client.get("/workbench")
        queue_after_items = queue_after_clear.json() if queue_after_clear.status_code == 200 else []
        check("Queue after clear still returns 200", queue_after_clear.status_code == 200)
        check(
            "Only second session items remain",
            all(item.get("session_id") == session_id_2 for item in queue_after_items),
        )
        check(
            "Remaining count matches second session additions",
            len(queue_after_items) == exceptions_added_2,
        )
    finally:
        try:
            subset_csv.unlink(missing_ok=True)
        except Exception:
            pass
        if original_key is not None:
            os.environ["VISION_AGENT_API_KEY"] = original_key

    print(f"\n{LINE * 62}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print(f"  Phase 11: COMPLETE {PASS}")
    else:
        print(f"  Phase 11: {failed} failed")
    print(f"{LINE * 62}")


if __name__ == "__main__":
    main()

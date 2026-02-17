"""
test_phase15_inbox.py - Phase 15 Recon Inbox checks.

Usage:
    python test_phase15_inbox.py
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import phase9_api
from inbox import InboxScanner
from workspace_store import WorkspaceStore


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


def _touch_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _configure_test_state(root: Path, inbox_path: Path, archive_path: Path) -> None:
    phase9_api.workspace_store = WorkspaceStore(str(root / "workspace.json"))
    phase9_api.workspace_state = phase9_api.workspace_store.default_workspace()
    phase9_api.exception_queue.clear()
    phase9_api.inbox_scanner = InboxScanner(
        inbox_path=str(inbox_path),
        archive_path=str(archive_path),
        max_files_per_run=50,
    )


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
    print("  Phase 15: Recon Inbox Tests")
    print(LINE * 62)

    base_dir = Path(__file__).resolve().parent
    source_csv = base_dir / "test_data" / "transactions.csv"
    source_receipt = base_dir / "test_data" / "receipts" / "receipt_02_vendor_mismatch.png"

    print("\n  Scanner Grouping:")
    with tempfile.TemporaryDirectory(prefix="phase15-scan-") as tmp:
        root = Path(tmp)
        inbox_path = root / "recon_inbox"
        archive_path = inbox_path / "_processed"
        scanner = InboxScanner(str(inbox_path), str(archive_path), max_files_per_run=50)

        empty_result = scanner.scan_batch()
        check(
            "empty folder -> NO_BATCH/EMPTY_INBOX",
            empty_result.get("status") == "NO_BATCH" and empty_result.get("reason_code") == "EMPTY_INBOX",
        )

        _touch_file(inbox_path / "receipt_01_clean_match.png", b"placeholder")
        receipts_only = scanner.scan_batch()
        check(
            "receipts only -> NO_BATCH/MISSING_CSV",
            receipts_only.get("status") == "NO_BATCH" and receipts_only.get("reason_code") == "MISSING_CSV",
        )

    with tempfile.TemporaryDirectory(prefix="phase15-scan-csv-") as tmp:
        root = Path(tmp)
        inbox_path = root / "recon_inbox"
        archive_path = inbox_path / "_processed"
        scanner = InboxScanner(str(inbox_path), str(archive_path), max_files_per_run=50)

        _copy_file(source_csv, inbox_path / "transactions_only.csv")
        csv_only = scanner.scan_batch()
        batch = csv_only.get("batch") or {}
        check("csv only -> BATCH_FOUND", csv_only.get("status") == "BATCH_FOUND")
        check("csv only batch has 0 receipts", len(batch.get("receipt_paths") or []) == 0)

    with tempfile.TemporaryDirectory(prefix="phase15-scan-mixed-") as tmp:
        root = Path(tmp)
        inbox_path = root / "recon_inbox"
        archive_path = inbox_path / "_processed"
        scanner = InboxScanner(str(inbox_path), str(archive_path), max_files_per_run=50)

        old_csv = inbox_path / "transactions_old.csv"
        new_csv = inbox_path / "transactions_new.csv"
        _copy_file(source_csv, old_csv)
        _copy_file(source_csv, new_csv)
        _touch_file(inbox_path / "receipt_02_vendor_mismatch.png", b"placeholder")
        _touch_file(inbox_path / "receipt_06_no_match.png", b"placeholder")

        # Ensure deterministic "newest CSV" selection.
        os.utime(old_csv, (old_csv.stat().st_atime, old_csv.stat().st_mtime - 10))
        os.utime(new_csv, (new_csv.stat().st_atime, new_csv.stat().st_mtime))

        mixed = scanner.scan_batch()
        mixed_batch = mixed.get("batch") or {}
        check("csv + receipts -> BATCH_FOUND", mixed.get("status") == "BATCH_FOUND")
        check(
            "newest csv selected",
            Path(str(mixed_batch.get("csv_path", ""))).name == "transactions_new.csv",
        )
        check("receipt paths discovered", len(mixed_batch.get("receipt_paths") or []) >= 1)

    print("\n  Endpoint Integration:")
    with tempfile.TemporaryDirectory(prefix="phase15-intake-csv-only-") as tmp:
        root = Path(tmp)
        inbox_path = root / "recon_inbox"
        archive_path = inbox_path / "_processed"
        _configure_test_state(root, inbox_path, archive_path)
        _copy_file(source_csv, inbox_path / "transactions.csv")

        original_poll = phase9_api.INBOX_POLL_ON_START
        phase9_api.INBOX_POLL_ON_START = False
        try:
            client = TestClient(phase9_api.app)
            csv_only_ingest = client.post("/inbox/ingest")
            csv_only_payload = csv_only_ingest.json() if csv_only_ingest.status_code == 200 else {}
            check("csv-only ingest returns 200", csv_only_ingest.status_code == 200)
            check("csv-only ingest status=INGESTED", csv_only_payload.get("inbox_status") == "INGESTED")
            check("csv-only ingest receipts_count=0", int(csv_only_payload.get("receipts_count", -1)) == 0)
        finally:
            phase9_api.INBOX_POLL_ON_START = original_poll

    with tempfile.TemporaryDirectory(prefix="phase15-intake-") as tmp:
        root = Path(tmp)
        inbox_path = root / "recon_inbox"
        archive_path = inbox_path / "_processed"
        _configure_test_state(root, inbox_path, archive_path)

        _copy_file(source_csv, inbox_path / "transactions.csv")
        _copy_file(source_receipt, inbox_path / "receipt_02_vendor_mismatch.png")

        original_poll = phase9_api.INBOX_POLL_ON_START
        original_vision_key = os.environ.pop("VISION_AGENT_API_KEY", None)
        phase9_api.INBOX_POLL_ON_START = False
        try:
            client = TestClient(phase9_api.app)
            ingest = client.post("/inbox/ingest")
            check("POST /inbox/ingest returns 200", ingest.status_code == 200)
            payload = ingest.json() if ingest.status_code == 200 else {}

            check("inbox_status=INGESTED", payload.get("inbox_status") == "INGESTED")
            check("session_id returned", isinstance(payload.get("session_id"), str) and payload.get("session_id", "").startswith("sess_"))
            check("new_exceptions_count numeric", isinstance(payload.get("new_exceptions_count"), int))
            check(
                "processed files listed",
                isinstance(payload.get("processed_files"), list) and len(payload.get("processed_files")) >= 1,
            )

            queue_response = client.get("/workbench")
            queue_items = queue_response.json() if queue_response.status_code == 200 else []
            check("queue endpoint returns 200", queue_response.status_code == 200)
            check(
                "queue populated with only non-clean outcomes",
                len(queue_items) == payload.get("new_exceptions_count")
                and all(item.get("match_state") != "CLEAN_MATCH" for item in queue_items),
            )

            batch_id = str(payload.get("batch_id") or "")
            archived_dir = archive_path / batch_id
            check("files archived to _processed/<batch_id>/", bool(batch_id) and archived_dir.exists())
            check("manifest file created", (archive_path / "manifest.json").exists())

            second = client.post("/inbox/ingest")
            second_payload = second.json() if second.status_code == 200 else {}
            queue_after = client.get("/workbench").json() if queue_response.status_code == 200 else []
            check("second ingest returns 200", second.status_code == 200)
            check("second ingest returns NO_BATCH", second_payload.get("inbox_status") == "NO_BATCH")
            check("second ingest does not duplicate queue", len(queue_after) == len(queue_items))
        finally:
            phase9_api.INBOX_POLL_ON_START = original_poll
            if original_vision_key is not None:
                os.environ["VISION_AGENT_API_KEY"] = original_vision_key

    print(f"\n{LINE * 62}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print(f"  Phase 15: COMPLETE {PASS}")
    else:
        print(f"  Phase 15: {failed} failed")
        sys.exit(1)
    print(LINE * 62)


if __name__ == "__main__":
    main()

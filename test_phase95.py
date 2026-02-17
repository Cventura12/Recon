"""
test_phase95.py - Phase 9.5 UI/API regression checks.

Focus:
1) Bounding-box scaling math
2) /diagnose response grounding payload
3) UI grounding controls/container presence

Usage:
    python test_phase95.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phase9_api import _scale_bbox_for_display, app


def _configure_symbols() -> tuple[str, str, str]:
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


PASS, FAIL, LINE = _configure_symbols()


def _close(actual: float, expected: float, tolerance: float = 1e-6) -> bool:
    return abs(actual - expected) <= tolerance


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
    print("  Phase 9.5: UI/API Grounding Regression")
    print(LINE * 62)

    base_dir = Path(__file__).resolve().parent

    # --------------------------------------------------------------
    # Category 1: Bounding-box scaling math
    # --------------------------------------------------------------
    print("\n  Bounding Box Scaling:")
    scaled_norm = _scale_bbox_for_display(
        bbox={"x": 0.10, "y": 0.20, "width": 0.30, "height": 0.40, "normalized": True},
        natural_width=1000.0,
        natural_height=500.0,
        display_width=500.0,
        display_height=250.0,
    )
    check("normalized x scaled", _close(scaled_norm["x"], 50.0))
    check("normalized y scaled", _close(scaled_norm["y"], 50.0))
    check("normalized width scaled", _close(scaled_norm["width"], 150.0))
    check("normalized height scaled", _close(scaled_norm["height"], 100.0))

    scaled_abs = _scale_bbox_for_display(
        bbox={"x": 100.0, "y": 400.0, "width": 300.0, "height": 200.0, "normalized": False},
        natural_width=1000.0,
        natural_height=2000.0,
        display_width=250.0,
        display_height=500.0,
    )
    check("absolute x scaled", _close(scaled_abs["x"], 25.0))
    check("absolute y scaled", _close(scaled_abs["y"], 100.0))
    check("absolute width scaled", _close(scaled_abs["width"], 75.0))
    check("absolute height scaled", _close(scaled_abs["height"], 50.0))

    # --------------------------------------------------------------
    # Category 2: /diagnose includes grounding view
    # --------------------------------------------------------------
    print("\n  API Grounding Payload:")
    previous_key = os.environ.pop("VISION_AGENT_API_KEY", None)
    try:
        client = TestClient(app)
        receipt_path = base_dir / "test_data" / "receipts" / "receipt_02_vendor_mismatch.png"
        csv_path = base_dir / "test_data" / "transactions.csv"

        with receipt_path.open("rb") as receipt_file, csv_path.open("rb") as csv_file:
            response = client.post(
                "/diagnose",
                files={
                    "receipt": ("receipt_02_vendor_mismatch.png", receipt_file, "image/png"),
                    "csv": ("transactions.csv", csv_file, "text/csv"),
                },
            )

        check("POST /diagnose status 200", response.status_code == 200)
        payload = response.json() if response.status_code == 200 else {}

        ui = payload.get("ui", {})
        grounding_view = ui.get("grounding_view", {})
        fields = grounding_view.get("fields", {})
        vendor_field = fields.get("vendor", {})
        date_field = fields.get("date", {})
        total_field = fields.get("total", {})

        check("ui.grounding_view present", isinstance(grounding_view, dict))
        check("grounding fields include vendor/date/total", all(k in fields for k in ("vendor", "date", "total")))
        check("vendor field has chunk_ids", "chunk_ids" in vendor_field)
        check("date field has bounding_boxes", "bounding_boxes" in date_field)
        check("total field has availability flag", "available" in total_field)
        check("ui.match_state_badge present", "match_state_badge" in ui)
    finally:
        if previous_key is not None:
            os.environ["VISION_AGENT_API_KEY"] = previous_key

    # --------------------------------------------------------------
    # Category 3: UI containers/toggles for grounding viewer
    # --------------------------------------------------------------
    print("\n  UI Grounding Controls:")
    # Phase 14+ architecture keeps investigation UI in the workbench page.
    # Fall back to legacy single-diagnosis page if needed.
    workbench_html_path = base_dir / "web" / "workbench" / "index.html"
    legacy_html_path = base_dir / "web" / "index.html"
    html_path = workbench_html_path if workbench_html_path.exists() else legacy_html_path
    html = html_path.read_text(encoding="utf-8")

    legacy_js = (base_dir / "web" / "app.js").read_text(encoding="utf-8")
    workbench_js = (base_dir / "web" / "workbench" / "workbench.js").read_text(encoding="utf-8")
    js_bundle = "\n".join([legacy_js, workbench_js])

    has_toggle = ('id="grounding-toggle"' in html) or ('id="detail-grounding-toggle"' in html)
    has_container = (
        'id="receipt-viewer-container"' in html
        or 'id="detail-receipt-viewer-container"' in html
    )
    has_overlay = ('id="overlay-layer"' in html) or ('id="detail-overlay-layer"' in html)
    has_pills = (
        'data-field="vendor"' in html
        and 'data-field="date"' in html
        and 'data-field="total"' in html
    )

    check("index includes grounding toggle", has_toggle)
    check("index includes viewer container", has_container)
    check("index includes overlay layer", has_overlay)
    check("index includes field pills", has_pills)
    check("app.js includes scaleBoundingBox()", "function scaleBoundingBox" in js_bundle)
    check(
        "app.js binds grounding interactions",
        ("bindGroundingInteractions" in js_bundle) or ("bindGroundingEvents" in js_bundle),
    )

    print(f"\n{LINE * 62}")
    print(f"  Results: {passed}/{passed + failed} passed")
    if failed == 0:
        print(f"  Phase 9.5: COMPLETE {PASS}")
    else:
        print(f"  Phase 9.5: {failed} failed")
    print(f"{LINE * 62}")


if __name__ == "__main__":
    main()

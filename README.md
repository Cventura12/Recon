# Diagnostic Agent for Accounting Exceptions

An AI-powered tool that explains **why** accounting mismatches happen between receipts and bank transactions.

## The Problem

Accounting platforms like QuickBooks and BlackLine can auto-match many transactions, but exceptions still happen every day.  
When matching fails, the exception queue usually shows no root-cause explanation, only "not matched."  
Bookkeepers then do manual investigation case by case, often spending 5-15 minutes on each exception.  
A team processing 300+ transactions per day can easily see 50+ exceptions that need review.  
The investigation is repetitive: compare vendor names, check amount deltas, inspect posting dates, and decode bank descriptors.

## The Solution

This diagnostic agent sits **after** a transaction fails to match.  
It takes one receipt plus a transaction CSV, then extracts, normalizes, scores, classifies, and explains the mismatch.  
It does not replace accounting software matching engines; it explains the cases they cannot resolve automatically.  
The human still makes the final accounting decision.

## How It Works

```text
Receipt Image (.png/.jpg/.pdf)
        |
        v
extract.py   -> ReceiptData
        |
        v
normalize.py -> normalized vendor/date/amount (both sides)
        |
        v
match.py     -> list[MatchCandidate] (ranked + evidence)
        |
        v
diagnose.py  -> Diagnosis (labels + confidence + audit trail)
        |
        v
explain.py   -> human-readable explanation
        |
        v
main.py      -> CLI entrypoint (single receipt or batch)
```

- `extract.py`: Parses receipt files and returns validated `ReceiptData` (ADE-backed with mock fallback).
- `normalize.py`: Applies pure, deterministic normalization to vendor/date/amount on both receipt and transaction data.
- `match.py`: Scores each transaction candidate across vendor, amount, and date dimensions.
- `diagnose.py`: Applies deterministic rule thresholds to classify mismatch archetypes (including compound labels).
- `explain.py`: Formats a `Diagnosis` into clear, reviewer-friendly output.
- `main.py`: Orchestrates the full pipeline via CLI flags.

## Mismatch Types

| Type | What Happened | Real-World Example |
| --- | --- | --- |
| `vendor_descriptor_mismatch` | Merchant descriptor from bank processor does not resemble receipt vendor text. | Receipt: `El Agave Mexican Restaurant` -> Bank: `ELAGAVE*1847 CHATT TN` |
| `settlement_delay` | Posting date is delayed by normal card settlement timing (1-3 days). | Receipt on Friday, bank post on Monday |
| `tip_tax_variance` | Final posted amount differs due to tip/tax adjustments after authorization. | Receipt: `$47.50` -> Bank: `$54.63` |
| `partial_match` | Some dimensions match, but no single archetype explains the discrepancy cleanly. | Good vendor score, but amount/date signals conflict |
| `no_match` | No transaction in CSV meets minimum confidence threshold. | Receipt has no close candidate in account/date window |

## Example Output

```text
========================================================
  Probable Match - 84%
========================================================

  Receipt:      El Agave Mexican Restaurant
                $47.50  |  2026-01-12

  Best Match:   ELAGAVE*1847 CHATT TN
                $47.50  |  2026-01-12

  Evidence:
    - Vendor names differ: 'el agave mexican' vs 'elagave' (score: 61)
    - Exact amount match: $47.50
    - Same date: 2026-01-12

  Diagnosis: Vendor Descriptor Mismatch
========================================================
```

## Quick Start

```bash
# 1. Clone
git clone [repo-url]
cd receipt-diagnostic-agent

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 3. Install
pip install -r requirements.txt

# 4. Configure (optional - works without API key using mock data)
# .env is already included in this repo.
# Add your ADE API key from https://va.landing.ai if available.

# 5. Run
python main.py --receipt test_data/receipts/receipt_02_vendor_mismatch.png --csv test_data/transactions.csv

# 6. Run all test receipts
python main.py --all --csv test_data/transactions.csv

# 7. Run web API + operator UI (Phase 9/9.5)
uvicorn phase9_api:app --host 0.0.0.0 --port 8000
# Open web/index.html in your browser (or serve the web folder with Live Server)
# Optional API override when using a different backend port:
#   http://127.0.0.1:5500/?api=http://127.0.0.1:9000
```

## Web Operator Interface (Phase 9.5)

Phase 9.5 adds a finance-operator-focused interface in `web/`:

- Two-column workflow (inputs/actions on left, persistent results on right)
- Status badge + confidence + diagnosis summary
- Evidence bullets and candidate scoring card
- Collapsed runner-up candidates
- Audit note block with copy/download actions
- Grounding viewer with field toggles (`Vendor`, `Date`, `Total`)

### Grounding Viewer

The backend returns `ui.grounding_view` and `ui.receipt_preview` in `POST /diagnose`.

- `ui.grounding_view.fields.<field>.bounding_boxes` can contain one or more boxes.
- Each box has:
  - `x`, `y`, `width`, `height`
  - `normalized` boolean
- Scaling in the UI:
  - If `normalized=true`, coordinates are treated as 0-1 ratios of displayed image width/height.
  - If `normalized=false`, coordinates are treated as source-image pixels and scaled by:
    - `display_width / natural_width`
    - `display_height / natural_height`
- If no bounding boxes are available, the UI explicitly shows:
  - `Grounding not available for this extraction.`

## Workbench Review Flow + Shortcuts (Phase 10.5)

Phase 10.5 adds operator-speed workflow on top of the existing in-memory Exception Workbench.

- Queue entry point: `web/workbench/index.html`
- Route behavior:
  - `/workbench` list view
  - `/workbench/:id` detail view semantics (also supports `?id=...` in static hosting)
- No database persistence. Queue remains in memory and resets when the API process restarts.

### Review controls

- Client-side queue controls:
  - Search (merchant/vendor/diagnosis)
  - Filter pills: `All`, `Probable`, `Possible`, `No Confident`
  - Sort: `Confidence desc` (default), `Amount desc`, `Date desc`
  - `Hide reviewed` toggle
- Local resolution state (browser `localStorage`, keyed by exception id):
  - `Reviewed`
  - `Needs follow-up`

### Keyboard shortcuts

List view:

- `J`: move selection down
- `K`: move selection up
- `Enter`: open selected item
- `/`: focus search box
- `Esc`: clear search focus

Detail view:

- `J`: next item
- `K`: previous item
- `C`: copy audit memo
- `Shift+C`: copy memo and move to next item
- `Esc`: back to list

Shortcuts are disabled while typing in `input` / `textarea` / `select` fields.

## Session Intake (Phase 11)

Phase 11 adds a lightweight session intake flow to preload the workbench queue.

- Endpoint: `POST /workbench/session-intake`
- Request (`multipart/form-data`):
  - `transactions_csv` (required)
  - `receipts` (optional, multiple files)
- Response:
  - `session_id`
  - `total_processed`
  - `exceptions_added`

Only non-clean outcomes are added to the queue:

- `PROBABLE_MATCH`
- `POSSIBLE_MATCH`
- `NO_CONFIDENT_MATCH`

Queue items include:

- `session_id`
- `created_at`

Session utilities:

- `GET /workbench/sessions`
- `DELETE /workbench/session/{session_id}`

Session intake inserts queue items into the backend queue and can now be persisted via Phase 14 workspace save/load.

## Persistence for 1-Week Pilot (Phase 14)

Phase 14 adds lightweight continuity for daily accounting use.

- Backend persistence store: `data/workspace.json` (single workspace: `default`)
- Atomic writes: temp file + rename
- New API endpoints:
  - `GET /workspace/load`
  - `POST /workspace/save`
  - `POST /workspace/reset`

Persisted workspace fields:

- `workbench_queue` (includes `result_payload`, `session_id`, `created_at`)
- `resolution_state`
- `decision_notes`
- `alias_memory`
- `pattern_memory`
- optional UI continuity fields:
  - `last_selected_exception_id`
  - `show_only_unresolved`

Frontend behavior:

- Workbench hydrates from `GET /workspace/load` on page load
- Auto-save uses debounced `POST /workspace/save` calls (no save spam while typing)
- Header shows subtle save state: `Saving...` / `Saved`
- Queue, decisions, and notes survive browser refresh and API restart

Operator-facing copy intentionally stays honest:

- `Stored locally for this workspace test.`

## Project Structure

```text
receipt-diagnostic-agent/
├── models.py          # Pydantic data schemas (ReceiptData, Transaction, MatchCandidate, Diagnosis)
├── extract.py         # Receipt extraction via ADE (with mock fallback)
├── normalize.py       # Vendor, date, amount normalization
├── match.py           # Transaction candidate scoring engine
├── diagnose.py        # Mismatch classification (deterministic rules)
├── explain.py         # Human-readable output formatting
├── main.py            # CLI entry point
├── test_data/         # Test receipts + transactions CSV
├── requirements.txt   # Python dependencies
└── .env               # API key configuration
```

## Tech Stack

| Technology | Purpose |
| --- | --- |
| Python 3.11+ | Core language and runtime |
| Pydantic v2 | Typed models, validation, schema contracts |
| Pandas | Transaction CSV loading and tabular processing |
| RapidFuzz | Fast fuzzy string similarity for vendor scoring |
| LandingAI ADE | Receipt extraction (parse + schema-based field extraction) |

## Development Status

- [x] Phase 1: Foundation
- [x] Phase 2: Extraction
- [x] Phase 3: Normalization
- [x] Phase 4: Matching
- [x] Phase 5: Diagnosis
- [x] Phase 6: Explanation
- [x] Phase 7: CLI Integration
- [x] Phase 8: End-to-End Validation
- [x] Phase 9: Web UI
- [x] Phase 9.5: Operator UI / Grounding Viewer
- [x] Phase 10: Exception Workbench Queue
- [x] Phase 10.5: Operator Speed Layer
- [x] Phase 11: Session Intake
- [x] Phase 12: Resolution + Decision Notes
- [x] Phase 13: Local Memory Indicators
- [x] Phase 14: Workspace Persistence

## What This Is NOT

- Not a transaction matching system (QuickBooks/BlackLine already do matching).
- Not a fraud detection engine.
- Not full accounting automation.
- Not a multi-agent platform.
- The agent explains; the human decides.

# Expected Results - Diagnostic Agent Test Plan (Phase 1E)

This document defines expected outcomes for each placeholder receipt in `test_data/receipts/` against `test_data/transactions.csv`.

## Purpose

- Validate each mismatch archetype during module development (Phases 2-7).
- Provide regression expectations for end-to-end testing (Phase 8).
- Reduce ambiguity by documenting expected labels, confidence ranges, and evidence signals.

## Shared Assumptions

- Matching returns candidates with `overall_confidence >= 30`.
- Vendor descriptor mismatch threshold is `vendor_score < 80`.
- Settlement delay window is `date_diff` between 1 and 3 days.
- Tip/tax variance is expected when amount difference is explainable; current default threshold is 25% (known edge case in Receipt 03).
- `NO_MATCH` is expected when no candidate meets the minimum confidence threshold.

## Case 01 - `receipt_01_clean_match.png`

- Input values:
  - Vendor: `Amazon.com`
  - Total: `89.97`
  - Date: `2026-01-10`
  - Confidence: `0.98`
- Expected match target: `TXN001` (`Amazon`, `89.97`, `2026-01-10`)
- Expected mismatch labels: `[]` (clean match)
- Expected confidence range: `>85`
- Expected key evidence strings:
  - Vendor names highly similar after normalization (`amazon.com` vs `amazon`)
  - Exact amount match: `$89.97`
  - Same date: `2026-01-10`
- Validates:
  - Clean match flow with no mismatch labels
  - Correct handling of minor vendor formatting differences
- Known edge cases:
  - Confirms the system does not over-label a valid match

## Case 02 - `receipt_02_vendor_mismatch.png`

- Input values:
  - Vendor: `El Agave Mexican Restaurant`
  - Total: `47.50`
  - Date: `2026-01-12`
  - Tax: `3.50`
  - Tip: `7.00`
  - Subtotal: `37.00`
  - Confidence: `0.95`
- Expected match target: `TXN002` (`ELAGAVE*1847 CHATT TN`, `47.50`, `2026-01-12`)
- Expected mismatch labels: `[VENDOR_MISMATCH]`
- Expected confidence range: `>75`
- Expected key evidence strings:
  - Vendor names differ materially (`el agave mexican restaurant` vs `elagave` family token)
  - Vendor score below mismatch threshold (`<80`)
  - Exact amount match: `$47.50`
  - Same date: `2026-01-12`
- Validates:
  - Vendor normalization and fuzzy matching for processor descriptors
- Known edge cases:
  - Ensures vendor mismatch can be flagged even when amount/date are perfect

## Case 03 - `receipt_03_tip_tax_variance.png`

- Input values:
  - Vendor: `Starbucks`
  - Total: `5.25`
  - Date: `2026-01-14`
  - Tax: `0.35`
  - Confidence: `0.97`
- Expected match target: `TXN003` (`Starbucks`, `6.83`, `2026-01-14`)
- Expected mismatch labels: `[TIP_TAX_VARIANCE]` or `[PARTIAL_MATCH]`
- Expected confidence range: `>50`
- Expected key evidence strings:
  - Strong vendor match (`starbucks` vs `starbucks`)
  - Same date: `2026-01-14`
  - Amount difference: `$1.58` (~`30.1%` of receipt total)
  - If strict 25% threshold remains: evidence should indicate threshold exceedance
- Validates:
  - Amount variance logic and threshold boundary behavior
- Known edge cases:
  - This case intentionally sits above the 25% default and may classify as `PARTIAL_MATCH`

## Case 04 - `receipt_04_settlement_delay.png`

- Input values:
  - Vendor: `Home Depot`
  - Total: `234.67`
  - Date: `2026-01-15`
  - Tax: `18.67`
  - Confidence: `0.96`
- Expected match target: `TXN004` (`THE HOME DEPOT #4821`, `234.67`, `2026-01-17`)
- Expected mismatch labels: `[SETTLEMENT_DELAY]`
- Expected confidence range: `>85`
- Expected key evidence strings:
  - High vendor similarity after normalization (`home depot`)
  - Exact amount match: `$234.67`
  - Date difference: `2 days`
- Validates:
  - Settlement delay detection independent of amount/vendor correctness
- Known edge cases:
  - Weekend/bank-posting lag behavior should remain in a normal 1-3 day window

## Case 05 - `receipt_05_combined_mismatch.png`

- Input values:
  - Vendor: `Fastenal`
  - Total: `178.23`
  - Date: `2026-01-18`
  - Tax: `13.23`
  - Confidence: `0.72` (intentionally low)
- Expected match target: `TXN005` (`FASTENAL CO01 CHATT`, `182.59`, `2026-01-20`)
- Expected mismatch labels:
  - `[VENDOR_MISMATCH, SETTLEMENT_DELAY, TIP_TAX_VARIANCE]`
- Expected confidence range: `60-80`
- Expected key evidence strings:
  - Vendor descriptor mismatch (score below `80`)
  - Date difference: `2 days`
  - Amount difference: `$4.36` (~`2.4%`)
  - Extraction confidence warning trigger (`0.72 < 0.80`)
- Validates:
  - Compound labeling with multiple simultaneous archetypes
  - Low extraction confidence warning path
- Known edge cases:
  - Ensure diagnosis evidence merges both match-level and diagnosis-level rationale

## Case 06 - `receipt_06_no_match.png`

- Input values:
  - Vendor: `Bob's Local Hardware`
  - Total: `45.00`
  - Date: `2026-01-22`
  - Tax: `3.00`
  - Confidence: `0.93`
- Expected match target: `none`
- Expected mismatch labels: `[NO_MATCH]`
- Expected confidence range: `95`
- Expected key evidence strings:
  - No candidates met minimum confidence threshold
  - No transaction close on vendor + amount + date simultaneously
- Validates:
  - Correct `NO_MATCH` classification behavior
  - False-positive resistance in the matcher
- Known edge cases:
  - Ensure similar merchant noise rows (for example `AMZN MKTP US*2K4RF`) do not match unrelated receipts

## Noise Transaction Intent (`TXN006` to `TXN010`)

- These rows intentionally should not become top matches for the six target receipts.
- Special attention: `TXN010` is Amazon-like but should not match `receipt_01_clean_match.png` because amount/date are far apart.
- If a noise row becomes top match, treat as likely bug in scoring weights or threshold logic.

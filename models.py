"""
models.py - Data Models for the Diagnostic Agent Pipeline

This file defines ALL data structures used across the diagnostic agent.
Every module in the pipeline communicates exclusively through these models:

    extract.py  ->  ReceiptData
    match.py    ->  list[MatchCandidate]
    diagnose.py ->  Diagnosis
    explain.py  ->  str (uses Diagnosis as input)

Design principles:
1. Each layer's output is the next layer's input
2. Models carry evidence strings so reasoning is traceable end-to-end
3. Changing a model here affects every downstream module
4. All fields have descriptions - they serve as documentation AND
   improve ADE extraction accuracy (ADE uses field descriptions
   to understand what to extract from the document)

Schema relationships:
    MismatchType --used by--> Diagnosis.labels
    ReceiptData  --used by--> Diagnosis.receipt
    Transaction  --used by--> MatchCandidate.transaction
    MatchCandidate --used by--> Diagnosis.top_match
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MismatchType(str, Enum):
    """Five archetypes describing why a receipt fails to match a bank transaction."""

    # Most common in production bookkeeping.
    # Apply when vendor similarity is below 80/100 while amount/date align tightly.
    # Examples:
    # Receipt: "El Agave Mexican Restaurant" -> Bank: "ELAGAVE*1847 CHATT TN"
    # Receipt: "Starbucks Coffee #14892" -> Bank: "SBUX 14892 CHATTANOOG"
    # Receipt: "The Home Depot" -> Bank: "THE HOME DEPOT #4821"
    # Receipt: "Joe's Pizza" -> Bank: "SQ *JOE'S PIZZA GRILL"
    # Receipt: "Amazon.com" -> Bank: "AMZN MKTP US*2K4RF83J0"
    VENDOR_MISMATCH = "vendor_descriptor_mismatch"

    # Card networks and banks often post 1-3 business days after purchase.
    # Apply when date differs by 1-3 days while vendor/amount still match well.
    # Friday purchases commonly settle on Monday/Tuesday.
    SETTLEMENT_DELAY = "settlement_delay"

    # Restaurants/services can settle a higher final amount after tip/tax adjustment.
    # Apply when amount differs by less than 25% and vendor/date are good matches.
    # V1 keeps a generous threshold to capture realistic edge cases.
    TIP_TAX_VARIANCE = "tip_tax_variance"

    # Candidate passes minimum scoring but does not cleanly fit another archetype.
    # Apply when evidence is contradictory or multiple dimensions are weak.
    PARTIAL_MATCH = "partial_match"

    # No credible candidate found in the transaction CSV.
    # Apply when the best overall confidence is below 30%.
    # Common causes: pending post, wrong account/card, personal purchase, wrong period.
    NO_MATCH = "no_match"


class ReceiptData(BaseModel):
    """Validated output from ADE receipt extraction.

    This model represents what we know about a receipt AFTER the extraction
    engine has processed the image. Each field maps to a specific piece of
    information printed on the physical receipt.

    Visual grounding: The chunk_ids field traces each extracted value back
    to its source location on the receipt image. This enables the UI to
    show WHERE on the receipt each number came from - critical for building
    trust with users who need to verify the agent's work.

    Confidence: The confidence field (0.0 to 1.0) reflects the extraction
    engine's certainty about its output. Values below 0.8 trigger a warning
    in the explanation output telling the user to manually verify the data.
    Common causes of low confidence: blurry receipt, crumpled paper,
    handwritten amounts, thermal print fade, non-English text.

    This model is intentionally simple - it stores exactly what's on the
    receipt and nothing more. Normalization, matching, and diagnosis happen
    in separate modules using their own models.
    """

    vendor: str = Field(
        ...,
        description=(
            "Vendor or merchant name exactly as printed on the receipt "
            "header or footer. This is the raw extracted text before any "
            "normalization. Examples: 'El Agave Mexican Restaurant', "
            "'THE HOME DEPOT #4821', 'Starbucks #14892'"
        ),
    )
    total: float = Field(
        ...,
        ge=0,
        description=(
            "Final total amount paid including tax and tip. This is the "
            "number that gets compared against the bank transaction amount. "
            "Look for labels like 'Total', 'Amount Due', 'Grand Total', "
            "or 'Balance Due' on the receipt. If multiple totals appear, "
            "use the largest one (it's usually the final amount)."
        ),
    )
    date: Optional[str] = Field(
        default=None,
        description=(
            "Transaction date as printed on the receipt, in whatever format "
            "it appears. Gets normalized to YYYY-MM-DD by normalize.py later. "
            "Common formats: '01/15/2026', 'Jan 15, 2026', '2026-01-15', "
            "'1/15/26'. None when the date is missing, illegible, or the "
            "extraction engine couldn't find it."
        ),
    )
    tax: Optional[float] = Field(
        default=None,
        ge=0,
        description=(
            "Tax amount if listed as a separate line item on the receipt. "
            "Useful for diagnosing tip/tax variance - when the bank amount "
            "differs from the receipt, knowing the tax helps determine "
            "whether the difference is a tip or a tax adjustment."
        ),
    )
    tip: Optional[float] = Field(
        default=None,
        ge=0,
        description=(
            "Tip or gratuity amount if present on the receipt. Common on "
            "restaurant receipts. When present, it directly explains why "
            "the bank amount is higher than the receipt subtotal. "
            "Note: many receipts show a tip LINE but the amount is "
            "handwritten and harder to extract."
        ),
    )
    subtotal: Optional[float] = Field(
        default=None,
        ge=0,
        description=(
            "Subtotal before tax and tip, if listed separately. When both "
            "subtotal and total are available, the difference reveals how "
            "much of the total is tax/tip - useful context for diagnosis."
        ),
    )
    currency: str = Field(
        default="USD",
        description="ISO 4217 currency code. Defaults to USD for US receipts.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Extraction confidence from 0.0 (no confidence) to 1.0 (certain). "
            "Set by the extraction engine. Values below 0.8 trigger a warning "
            "in the explanation output: 'Low extraction confidence - verify "
            "manually.' Common causes of low confidence: blurry receipt, "
            "crumpled paper, handwritten amounts, thermal print fade."
        ),
    )
    chunk_ids: list[str] = Field(
        default_factory=list,
        description=(
            "ADE chunk IDs that trace each extracted value back to its source "
            "location on the receipt image. Enables visual grounding - the "
            "ability to highlight WHERE on the receipt each number came from. "
            "Empty list when using mock extraction (no API key) or when the "
            "extraction engine doesn't support grounding."
        ),
    )
    raw_text: Optional[str] = Field(
        default=None,
        description=(
            "Raw OCR markdown text from the ADE parse step. Stored for "
            "debugging when extraction produces unexpected results. Can be "
            "inspected to understand what the OCR engine 'saw' on the receipt."
        ),
    )

    @property
    def has_tip(self) -> bool:
        """Whether this receipt includes a non-zero tip amount."""
        return self.tip is not None and self.tip > 0

    @property
    def has_tax(self) -> bool:
        """Whether this receipt includes a non-zero tax amount."""
        return self.tax is not None and self.tax > 0

    @property
    def is_low_confidence(self) -> bool:
        """Whether extraction confidence is below the warning threshold (0.8)."""
        return self.confidence < 0.8

    @property
    def tax_tip_total(self) -> float:
        """Sum of tax and tip if known, for diagnosing amount variances."""
        return (self.tax or 0.0) + (self.tip or 0.0)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "vendor": "El Agave Mexican Restaurant",
                    "total": 47.50,
                    "date": "2026-01-12",
                    "tax": 3.50,
                    "tip": 7.00,
                    "subtotal": 37.00,
                    "currency": "USD",
                    "confidence": 0.95,
                    "chunk_ids": ["chunk_010", "chunk_011", "chunk_012"],
                    "raw_text": (
                        "El Agave Mexican Restaurant\n1847 Rossville Blvd\n"
                        "Subtotal: $37.00\nTax: $3.50\nTip: $7.00\nTotal: $47.50"
                    ),
                }
            ]
        }
    )


class Transaction(BaseModel):
    """Single transaction from a bank or credit card CSV export.

    Represents how the BANK sees a transaction - which is often different
    from how the RECEIPT shows it. The merchant name, amount, and date
    may all differ from the corresponding receipt due to payment processing:

    - Merchant names get abbreviated and coded by payment processors
      ("El Agave Mexican Restaurant" -> "ELAGAVE*1847 CHATT TN")
    - Amounts change when tips are added after authorization
      ($5.25 receipt -> $6.83 bank post)
    - Dates shift 1-3 business days during settlement
      (receipt Jan 15 -> bank Jan 17)

    These differences are exactly what the diagnostic agent exists to explain.
    """

    merchant: str = Field(
        ...,
        description=(
            "Merchant name as it appears on the bank or credit card statement. "
            "Often abbreviated, coded, or truncated by the payment processor. "
            "May include store numbers, location codes, or transaction IDs that "
            "don't appear on the receipt. "
            "Examples: "
            "'ELAGAVE*1847 CHATT TN' (El Agave restaurant), "
            "'AMZN MKTP US*2K4RF83J0' (Amazon purchase), "
            "'SQ *JOE'S PIZZA GRILL' (Square POS merchant), "
            "'PP*JOHNDEEREFINAN' (PayPal payment to John Deere), "
            "'THE HOME DEPOT #4821' (Home Depot store 4821)"
        ),
    )
    amount: float = Field(
        ...,
        ge=0,
        description=(
            "Transaction amount as posted by the bank. May differ from the "
            "receipt total due to: (1) tips added after receipt was printed, "
            "(2) tax adjustments between authorization and settlement, "
            "(3) currency conversion fees, (4) partial refunds or credits. "
            "This is the SETTLED amount, not the authorization amount."
        ),
    )
    date: str = Field(
        ...,
        description=(
            "Transaction date as recorded by the bank. This is the POSTING "
            "date (when the bank processed the settlement), not the "
            "transaction date (when you made the purchase). May differ from "
            "the receipt date by 1-3 business days. Weekend purchases "
            "typically post on Monday or Tuesday."
        ),
    )
    description: Optional[str] = Field(
        default=None,
        description=(
            "Additional transaction description or memo provided by the bank. "
            "Sometimes contains category labels ('Restaurant', 'Groceries'), "
            "reference numbers, or additional merchant details not in the "
            "merchant name field. Not always present in bank CSV exports."
        ),
    )
    transaction_id: Optional[str] = Field(
        default=None,
        description=(
            "Unique transaction identifier from the bank. Used for "
            "deduplication (ensuring the same transaction isn't matched "
            "twice) and audit trail (tracing a diagnosis back to the "
            "original bank record). Format varies by bank."
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "merchant": "ELAGAVE*1847 CHATT TN",
                    "amount": 47.50,
                    "date": "2026-01-12",
                    "description": "Restaurant",
                    "transaction_id": "TXN002",
                }
            ]
        }
    )


class MatchCandidate(BaseModel):
    """One potential transaction match with full scoring detail.

    The matching engine (match.py) evaluates every transaction in the CSV
    as a potential match for the receipt. For each candidate, it computes
    three sub-scores:

    1. Vendor similarity (0-100): How closely the vendor names match after
       normalization. Uses fuzzy string matching (RapidFuzz). Weight: 40%.
    2. Amount proximity (0-100): How close the amounts are. Exact match = 100,
       25% difference = 0. Weight: 35%.
    3. Date proximity (0-100): How close the dates are. Same day = 100,
       5+ days apart = 0. Weight: 25%.

    These combine into an overall_confidence score (0-100) that ranks
    candidates. Only candidates scoring above 30% are returned.

    The evidence list is CRITICAL - it carries the reasoning through the
    pipeline from matching -> diagnosis -> explanation. Every sub-score
    produces a human-readable evidence string so the final output can show
    the user exactly what matched and what didn't. Without evidence, the
    agent would be a black box that says "86% match" with no explanation.
    """

    transaction: Transaction = Field(
        ...,
        description="The candidate transaction from the CSV being evaluated.",
    )
    vendor_score: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Vendor name similarity from 0-100. Computed by RapidFuzz "
            "fuzz.ratio() on NORMALIZED vendor names (after both sides go "
            "through normalize_vendor). Interpretation: "
            "95-100 = essentially identical, "
            "80-94 = likely same vendor with minor formatting differences, "
            "50-79 = possibly same vendor with significant descriptor differences, "
            "below 50 = probably different vendors."
        ),
    )
    amount_diff: float = Field(
        ...,
        ge=0,
        description=(
            "Absolute dollar difference between receipt total and transaction "
            "amount. Always non-negative. Example: receipt $47.50, transaction "
            "$50.00 -> amount_diff = 2.50. Used by the diagnosis engine to "
            "determine if the variance is consistent with a tip or tax adjustment."
        ),
    )
    amount_pct_diff: float = Field(
        ...,
        ge=0,
        description=(
            "Amount difference as a percentage of the receipt total. "
            "Example: receipt $47.50, transaction $50.00 -> pct_diff = 5.3%. "
            "The diagnosis engine uses this to detect tip/tax variance: "
            "under 25% = possible tip or tax adjustment, over 25% = too "
            "large to be explained by tip alone."
        ),
    )
    date_diff: int = Field(
        ...,
        ge=0,
        description=(
            "Number of calendar days between the receipt date and the "
            "transaction posting date. Always non-negative. "
            "0 = same day (no settlement delay). "
            "1-3 = typical settlement delay (normal for credit cards). "
            "4+ = unusual gap, likely not the same transaction."
        ),
    )
    overall_confidence: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Weighted confidence score combining: vendor similarity (40%), "
            "amount proximity (35%), and date proximity (25%). This is the "
            "primary ranking metric - higher is better. Interpretation: "
            "80-100 = probable match, "
            "50-79 = possible match, needs review, "
            "30-49 = weak match, low confidence, "
            "below 30 = not returned (filtered out)."
        ),
    )
    evidence: list[str] = Field(
        default_factory=list,
        description=(
            "Human-readable evidence strings explaining each sub-score. "
            "These carry the 'why' through the pipeline so the explanation "
            "layer can show the user exactly what matched and what didn't. "
            "Typically contains 3 strings (one per dimension): "
            "['Vendor names differ: el agave mexican vs elagave (score: 61)', "
            "'Exact amount match: $47.50', "
            "'Same date: 2026-01-12']. "
            "The diagnosis engine adds its own evidence strings on top of these."
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "transaction": {
                        "merchant": "ELAGAVE*1847 CHATT TN",
                        "amount": 47.50,
                        "date": "2026-01-12",
                        "description": "Restaurant",
                        "transaction_id": "TXN002",
                    },
                    "vendor_score": 60.9,
                    "amount_diff": 0.0,
                    "amount_pct_diff": 0.0,
                    "date_diff": 0,
                    "overall_confidence": 84.3,
                    "evidence": [
                        "Vendor names differ: 'el agave mexican' vs 'elagave' (score: 60.9)",
                        "Exact amount match: $47.50",
                        "Same date: 2026-01-12",
                    ],
                }
            ]
        }
    )


class Diagnosis(BaseModel):
    """Final diagnostic output of the pipeline.

    This model is the end product of the entire diagnostic agent. It contains:
    1. The classification (what type of mismatch)
    2. The confidence (how sure we are)
    3. The complete evidence trail (why we think this)
    4. The best match (which transaction we think it is)
    5. The original receipt (for side-by-side comparison in the output)

    Key design decisions:

    - labels is a LIST because mismatches can be compound. A single receipt
      can have VENDOR_MISMATCH + SETTLEMENT_DELAY simultaneously (the bank
      mangled the name AND posted 2 days late). The diagnosis engine
      evaluates each archetype independently.

    - evidence contains the COMPLETE audit trail - both the match-level
      evidence (from MatchCandidate.evidence) and the diagnosis-level
      evidence (which rules triggered and why). This makes every diagnosis
      fully explainable.

    - explanation starts empty. The diagnose.py module fills labels,
      confidence, evidence, and top_match. The explain.py module then reads
      this Diagnosis and fills the explanation field with formatted text.
      This separation of concerns keeps classification logic separate from
      presentation logic.

    Usage in the pipeline:
        diagnosis = diagnose(matches, receipt)          # fills everything except explanation
        diagnosis.explanation = format_explanation(diagnosis)  # fills explanation
        print(diagnosis.explanation)                    # show to user
    """

    labels: list[MismatchType] = Field(
        default_factory=list,
        description=(
            "One or more mismatch archetypes that apply to this exception. "
            "Supports compound labels - a single exception can trigger multiple "
            "archetypes simultaneously. For example, a receipt from 'Fastenal' "
            "matching 'FASTENAL CO01 CHATT' at a different amount 2 days later "
            "would have labels=[VENDOR_MISMATCH, SETTLEMENT_DELAY, TIP_TAX_VARIANCE]. "
            "Empty list means clean match - no mismatch detected. "
            "[NO_MATCH] means no candidate transaction was found at all."
        ),
    )
    confidence: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description=(
            "Overall diagnosis confidence from 0-100. When a match is found, "
            "this is inherited from the top MatchCandidate's overall_confidence. "
            "When no match is found (NO_MATCH), this is set to 95 (we're "
            "confident that nothing matches). Interpretation: "
            "80-100 = high confidence diagnosis, act on it; "
            "50-79 = moderate confidence, review recommended; "
            "30-49 = low confidence, manual investigation needed."
        ),
    )
    evidence: list[str] = Field(
        default_factory=list,
        description=(
            "Complete evidence trail for the diagnosis. Contains two categories: "
            "(1) Match-level evidence from the scoring engine - what matched "
            "and what didn't on vendor, amount, and date dimensions. "
            "(2) Diagnosis-level evidence - which classification rules triggered "
            "and the specific thresholds that were crossed. "
            "Example: ["
            "  'Vendor names differ: el agave vs elagave (score: 61)', "
            "  'Exact amount match: $47.50', "
            "  'Same date: 2026-01-12', "
            "  'Vendor descriptor mismatch: score 61 below threshold 80' "
            "]. "
            "This list is the full audit trail - everything explain.py needs "
            "to generate the human-readable output."
        ),
    )
    top_match: Optional[MatchCandidate] = Field(
        default=None,
        description=(
            "The highest-scoring match candidate, if any exist above the 30% "
            "confidence threshold. Contains the full MatchCandidate with "
            "transaction details, sub-scores, and evidence. None when the "
            "diagnosis is NO_MATCH (nothing in the CSV was close enough). "
            "The explain.py module uses this to display the matched transaction "
            "details alongside the receipt for comparison."
        ),
    )
    receipt: Optional[ReceiptData] = Field(
        default=None,
        description=(
            "Original receipt data, carried through the pipeline for context. "
            "The explain.py module uses this to display the receipt vendor, "
            "total, and date alongside the matched transaction for "
            "side-by-side comparison in the output. Also used to check "
            "extraction confidence for the low-confidence warning."
        ),
    )
    explanation: str = Field(
        default="",
        description=(
            "Human-readable explanation string. LEFT EMPTY by diagnose.py "
            "and FILLED by explain.py. This separation keeps classification "
            "logic (diagnose.py) independent from presentation logic "
            "(explain.py). After explain.py fills this field, the Diagnosis "
            "object is complete and ready for display."
        ),
    )

    @property
    def is_match(self) -> bool:
        """Whether any match was found (vs NO_MATCH or no candidates)."""
        return MismatchType.NO_MATCH not in self.labels and self.top_match is not None

    @property
    def is_clean_match(self) -> bool:
        """Whether this is a clean match with no mismatch labels."""
        return len(self.labels) == 0 and self.top_match is not None

    @property
    def is_compound(self) -> bool:
        """Whether multiple mismatch types were detected simultaneously."""
        return len(self.labels) > 1

    @property
    def label_names(self) -> list[str]:
        """Human-readable label names for display."""
        names = {
            MismatchType.VENDOR_MISMATCH: "Vendor Descriptor Mismatch",
            MismatchType.SETTLEMENT_DELAY: "Settlement Delay",
            MismatchType.TIP_TAX_VARIANCE: "Tip/Tax Variance",
            MismatchType.PARTIAL_MATCH: "Partial Match",
            MismatchType.NO_MATCH: "No Match Found",
        }
        return [names.get(label, label.value) for label in self.labels]

    @property
    def label_summary(self) -> str:
        """Single-line summary of all labels, joined with ' + '."""
        if not self.labels:
            return "Clean Match"
        return " + ".join(self.label_names)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "labels": ["vendor_descriptor_mismatch"],
                    "confidence": 84.3,
                    "evidence": [
                        "Vendor names differ: 'el agave mexican' vs 'elagave' (score: 60.9)",
                        "Exact amount match: $47.50",
                        "Same date: 2026-01-12",
                        "Vendor descriptor mismatch: score 60.9 below threshold 80",
                    ],
                    "top_match": {
                        "transaction": {
                            "merchant": "ELAGAVE*1847 CHATT TN",
                            "amount": 47.50,
                            "date": "2026-01-12",
                        },
                        "vendor_score": 60.9,
                        "amount_diff": 0.0,
                        "amount_pct_diff": 0.0,
                        "date_diff": 0,
                        "overall_confidence": 84.3,
                        "evidence": [
                            "Vendor names differ: 'el agave mexican' vs 'elagave' (score: 60.9)",
                            "Exact amount match: $47.50",
                            "Same date: 2026-01-12",
                        ],
                    },
                    "receipt": {
                        "vendor": "El Agave Mexican Restaurant",
                        "total": 47.50,
                        "date": "2026-01-12",
                    },
                    "explanation": "",
                }
            ]
        }
    )


if __name__ == "__main__":
    """
    End-to-end smoke test for all models.

    Simulates the full pipeline flow:
    1. Create a ReceiptData (what extract.py would produce)
    2. Create Transactions (what CSV loading would produce)
    3. Create MatchCandidates (what match.py would produce)
    4. Create a Diagnosis (what diagnose.py would produce)
    5. Verify all properties and nested access work
    """
    print("=" * 50)
    print("  models.py - End-to-End Smoke Test")
    print("=" * 50)
    counts = {"passed": 0, "failed": 0}

    def check(name: str, condition: bool) -> None:
        if condition:
            print(f"  [OK] {name}")
            counts["passed"] += 1
        else:
            print(f"  [FAIL] {name}")
            counts["failed"] += 1

    # -- MismatchType --
    print("\n  MismatchType:")
    check("Has 5 variants", len(MismatchType) == 5)
    check("Is string enum", isinstance(MismatchType.VENDOR_MISMATCH, str))
    check("Value matches", MismatchType.NO_MATCH.value == "no_match")

    # -- ReceiptData (full) --
    print("\n  ReceiptData:")
    receipt = ReceiptData(
        vendor="El Agave Mexican Restaurant",
        total=47.50,
        date="2026-01-12",
        tax=3.50,
        tip=7.00,
        subtotal=37.00,
        confidence=0.95,
        chunk_ids=["chunk_010", "chunk_011"],
    )
    check("Vendor stored", receipt.vendor == "El Agave Mexican Restaurant")
    check("Total stored", receipt.total == 47.50)
    check("has_tip = True", receipt.has_tip is True)
    check("has_tax = True", receipt.has_tax is True)
    check("is_low_confidence = False", receipt.is_low_confidence is False)
    check("tax_tip_total = 10.50", receipt.tax_tip_total == 10.50)

    # -- ReceiptData (minimal) --
    receipt_min = ReceiptData(vendor="Starbucks", total=5.25)
    check("Minimal creates OK", receipt_min.date is None)
    check("Default confidence = 1.0", receipt_min.confidence == 1.0)
    check("Default chunk_ids = []", receipt_min.chunk_ids == [])
    check("has_tip = False (no tip)", receipt_min.has_tip is False)

    # -- ReceiptData (low confidence) --
    receipt_low = ReceiptData(vendor="Fast3nal", total=178.23, confidence=0.65)
    check("Low confidence detected", receipt_low.is_low_confidence is True)

    # -- Transaction --
    print("\n  Transaction:")
    txn = Transaction(
        merchant="ELAGAVE*1847 CHATT TN",
        amount=47.50,
        date="2026-01-12",
        description="Restaurant",
        transaction_id="TXN002",
    )
    check("Merchant stored", txn.merchant == "ELAGAVE*1847 CHATT TN")
    check("Amount stored", txn.amount == 47.50)

    txn_min = Transaction(merchant="Amazon", amount=89.97, date="2026-01-10")
    check("Minimal creates OK", txn_min.description is None)

    # -- MatchCandidate --
    print("\n  MatchCandidate:")
    candidate = MatchCandidate(
        transaction=txn,
        vendor_score=60.9,
        amount_diff=0.0,
        amount_pct_diff=0.0,
        date_diff=0,
        overall_confidence=84.3,
        evidence=[
            "Vendor names differ: 'el agave mexican' vs 'elagave' (score: 60.9)",
            "Exact amount match: $47.50",
            "Same date: 2026-01-12",
        ],
    )
    check("Confidence stored", candidate.overall_confidence == 84.3)
    check("Evidence has 3 items", len(candidate.evidence) == 3)
    check("Nested transaction access", candidate.transaction.merchant == "ELAGAVE*1847 CHATT TN")

    # -- Diagnosis (vendor mismatch) --
    print("\n  Diagnosis:")
    diag_vendor = Diagnosis(
        labels=[MismatchType.VENDOR_MISMATCH],
        confidence=84.3,
        evidence=candidate.evidence + [
            "Vendor descriptor mismatch: score 60.9 below threshold 80"
        ],
        top_match=candidate,
        receipt=receipt,
    )
    check("is_match = True", diag_vendor.is_match is True)
    check("is_clean_match = False", diag_vendor.is_clean_match is False)
    check("is_compound = False", diag_vendor.is_compound is False)
    check("label_summary correct", diag_vendor.label_summary == "Vendor Descriptor Mismatch")
    check("Evidence has 4 items", len(diag_vendor.evidence) == 4)

    # -- Diagnosis (compound) --
    diag_compound = Diagnosis(
        labels=[
            MismatchType.VENDOR_MISMATCH,
            MismatchType.SETTLEMENT_DELAY,
            MismatchType.TIP_TAX_VARIANCE,
        ],
        confidence=70.0,
        top_match=candidate,
    )
    check("is_compound = True", diag_compound.is_compound is True)
    check("3 labels stored", len(diag_compound.labels) == 3)
    check("label_summary has +", "+" in diag_compound.label_summary)

    # -- Diagnosis (no match) --
    diag_none = Diagnosis(
        labels=[MismatchType.NO_MATCH],
        confidence=95.0,
        evidence=["No transactions within date window match this receipt"],
    )
    check("is_match = False", diag_none.is_match is False)
    check("top_match is None", diag_none.top_match is None)
    check("label_summary correct", diag_none.label_summary == "No Match Found")

    # -- Diagnosis (clean match) --
    diag_clean = Diagnosis(
        labels=[],
        confidence=92.0,
        top_match=candidate,
        receipt=receipt,
    )
    check("is_clean_match = True", diag_clean.is_clean_match is True)
    check("label_summary = Clean Match", diag_clean.label_summary == "Clean Match")

    # -- JSON serialization --
    print("\n  Serialization:")
    json_str = diag_vendor.model_dump_json()
    check("JSON serialization works", "vendor_descriptor_mismatch" in json_str)

    dict_data = diag_vendor.model_dump()
    check("Dict conversion works", isinstance(dict_data, dict))
    check("Nested dict access", dict_data["top_match"]["transaction"]["merchant"] == "ELAGAVE*1847 CHATT TN")

    # -- Validation --
    print("\n  Validation:")
    try:
        ReceiptData(vendor="Test", total=-5.0)
        check("Negative total rejected", False)
    except Exception:
        check("Negative total rejected", True)

    try:
        MatchCandidate(
            transaction=txn_min,
            vendor_score=150,
            amount_diff=0,
            amount_pct_diff=0,
            date_diff=0,
            overall_confidence=50,
        )
        check("vendor_score > 100 rejected", False)
    except Exception:
        check("vendor_score > 100 rejected", True)

    try:
        ReceiptData(vendor="Test", total=10.0, confidence=1.5)
        check("confidence > 1.0 rejected", False)
    except Exception:
        check("confidence > 1.0 rejected", True)

    # -- Summary --
    print(f"\n{'=' * 50}")
    print(f"  Results: {counts['passed']} passed, {counts['failed']} failed")
    if counts["failed"] == 0:
        print("  [OK] ALL MODELS VERIFIED - Phase 1B/1C/1D complete")
    else:
        print(f"  [FAIL] {counts['failed']} CHECK(S) FAILED - fix before proceeding")
    print(f"{'=' * 50}")

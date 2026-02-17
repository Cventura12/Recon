"use strict";

const logic = require("./web/workbench/workbench_logic.js");

function symbols() {
  try {
    "✓✗═".encode;
    return { pass: "✓", fail: "✗", line: "═" };
  } catch (_unused) {
    return { pass: "[OK]", fail: "[FAIL]", line: "=" };
  }
}

const S = symbols();
let passed = 0;
let failed = 0;

function check(name, condition) {
  if (condition) {
    passed += 1;
    console.log(`    ${S.pass} ${name}`);
  } else {
    failed += 1;
    console.log(`    ${S.fail} ${name}`);
  }
}

console.log(S.line.repeat(62));
console.log("  Phase 10.5: Workbench Operator-Speed Tests");
console.log(S.line.repeat(62));

console.log("\n  Keyboard Shortcuts:");
check(
  "List J -> move_down",
  logic.getShortcutAction({
    mode: "list",
    key: "j",
    shiftKey: false,
    isInputFocused: false,
    searchFocused: false,
    modalOpen: false,
  }) === "move_down"
);
check(
  "List K -> move_up",
  logic.getShortcutAction({
    mode: "list",
    key: "k",
    shiftKey: false,
    isInputFocused: false,
    searchFocused: false,
    modalOpen: false,
  }) === "move_up"
);
check(
  "List Enter -> open_selected",
  logic.getShortcutAction({
    mode: "list",
    key: "Enter",
    shiftKey: false,
    isInputFocused: false,
    searchFocused: false,
    modalOpen: false,
  }) === "open_selected"
);
check(
  "List slash -> focus_search",
  logic.getShortcutAction({
    mode: "list",
    key: "/",
    shiftKey: false,
    isInputFocused: false,
    searchFocused: false,
    modalOpen: false,
  }) === "focus_search"
);
check(
  "List Esc with focused search -> clear_search_focus",
  logic.getShortcutAction({
    mode: "list",
    key: "Escape",
    shiftKey: false,
    isInputFocused: true,
    searchFocused: true,
    modalOpen: false,
  }) === "clear_search_focus"
);
check(
  "List shortcuts disabled while typing",
  logic.getShortcutAction({
    mode: "list",
    key: "j",
    shiftKey: false,
    isInputFocused: true,
    searchFocused: false,
    modalOpen: false,
  }) === null
);
check(
  "Detail C -> copy_memo",
  logic.getShortcutAction({
    mode: "detail",
    key: "c",
    shiftKey: false,
    isInputFocused: false,
    searchFocused: false,
    modalOpen: false,
  }) === "copy_memo"
);
check(
  "Detail Shift+C -> copy_and_next",
  logic.getShortcutAction({
    mode: "detail",
    key: "C",
    shiftKey: true,
    isInputFocused: false,
    searchFocused: false,
    modalOpen: false,
  }) === "copy_and_next"
);
check(
  "Detail Esc -> back_to_list",
  logic.getShortcutAction({
    mode: "detail",
    key: "Escape",
    shiftKey: false,
    isInputFocused: false,
    searchFocused: false,
    modalOpen: false,
  }) === "back_to_list"
);
check(
  "Modal Esc -> close_shortcuts_modal",
  logic.getShortcutAction({
    mode: "list",
    key: "Escape",
    shiftKey: false,
    isInputFocused: false,
    searchFocused: false,
    modalOpen: true,
  }) === "close_shortcuts_modal"
);

console.log("\n  Deterministic Memo:");
const memoPayload = {
  confidence: 86.0,
  diagnosis: { label_summary: "Tip/Tax Variance" },
  evidence: ["Evidence A", "Evidence B"],
  ui: {
    analysis_timestamp_utc: "2026-02-16T12:00:00Z",
    match_state_badge: "PROBABLE",
    top_candidate: {
      merchant: "SQ *SHOPNAME",
      amount: 18.48,
      date: "2026-02-14",
      vendor_similarity_score: 93.2,
      amount_delta_pct: 6.8,
      date_delta_days: 0,
    },
  },
};
const memo = logic.buildAuditMemo(memoPayload);
check("Memo includes state/confidence", memo.includes("PROBABLE - 86.0%"));
check("Memo includes diagnosis line", memo.includes("Diagnosis: Tip/Tax Variance"));
check("Memo includes candidate line", memo.includes("SQ *SHOPNAME"));
check("Memo includes deterministic timestamp", memo.includes("2026-02-16T12:00:00Z"));

console.log("\n  Review State + Hide Reviewed:");
let reviewState = logic.parseReviewState(null);
reviewState = logic.setReviewState(reviewState, "ex_001", "reviewed");
reviewState = logic.setReviewState(reviewState, "ex_002", "needs_follow_up");
const queue = [
  { id: "ex_001", merchant: "A", diagnosis: "D1", match_state: "PROBABLE", confidence_pct: 90, amount: 10, date: "2026-01-02" },
  { id: "ex_002", merchant: "B", diagnosis: "D2", match_state: "POSSIBLE", confidence_pct: 70, amount: 30, date: "2026-01-03" },
  { id: "ex_003", merchant: "C", diagnosis: "D3", match_state: "NO MATCH", confidence_pct: 20, amount: 20, date: "2026-01-01" },
];
const visibleWithHide = logic.filterAndSortQueue(queue, {
  query: "",
  matchFilter: "all",
  sortKey: "confidence_desc",
  hideReviewed: true,
}, reviewState);
check("Reviewed item hidden when toggle on", visibleWithHide.every((item) => item.id !== "ex_001"));
check("Needs follow-up item remains visible", visibleWithHide.some((item) => item.id === "ex_002"));
const serialized = logic.serializeReviewState(reviewState);
const reparsed = logic.parseReviewState(serialized);
check(
  "Review state roundtrip parses",
  (reparsed.ex_001 === "reviewed" || reparsed.ex_001 === "accepted")
    && (reparsed.ex_002 === "needs_follow_up" || reparsed.ex_002 === "follow_up")
);

console.log("\n  Queue Navigation Order:");
const ids = ["ex_010", "ex_011", "ex_012"];
check("Next from middle is correct", logic.getNextQueueId(ids, "ex_011") === "ex_012");
check("Prev from middle is correct", logic.getPrevQueueId(ids, "ex_011") === "ex_010");
check("Next from last is null", logic.getNextQueueId(ids, "ex_012") === null);
check("Prev from first is null", logic.getPrevQueueId(ids, "ex_010") === null);

console.log(`\n${S.line.repeat(62)}`);
console.log(`  Results: ${passed}/${passed + failed} passed`);
if (failed === 0) {
  console.log(`  Phase 10.5 checks complete ${S.pass}`);
} else {
  console.log(`  Phase 10.5 checks failed: ${failed}`);
  process.exitCode = 1;
}
console.log(S.line.repeat(62));

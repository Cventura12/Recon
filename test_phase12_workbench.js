"use strict";

const WorkbenchLogic = require("./web/workbench/workbench_logic.js");
const DecisionState = require("./web/workbench/decision_state.js");

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
console.log("  Phase 12: Resolution State Tests");
console.log(S.line.repeat(62));

console.log("\n  Resolution Persistence:");
let resolution = DecisionState.parseResolutionState(null);
resolution = DecisionState.setResolutionState(resolution, "ex_001", "accepted");
resolution = DecisionState.setResolutionState(resolution, "ex_002", "follow_up");
const rawResolution = DecisionState.serializeResolutionState(resolution);
const parsedResolution = DecisionState.parseResolutionState(rawResolution);
check(
  "Resolution state survives refresh serialization",
  DecisionState.getResolutionState(parsedResolution, "ex_001") === "accepted"
    && DecisionState.getResolutionState(parsedResolution, "ex_002") === "follow_up"
);
check(
  "Missing resolution defaults to unreviewed",
  DecisionState.getResolutionState(parsedResolution, "ex_003") === "unreviewed"
);

console.log("\n  Decision Note Persistence:");
let notes = DecisionState.parseDecisionNotes(null);
notes = DecisionState.setDecisionNote(notes, "ex_001", "Client confirmed tip added.");
const rawNotes = DecisionState.serializeDecisionNotes(notes);
const parsedNotes = DecisionState.parseDecisionNotes(rawNotes);
check(
  "Decision note loads correctly when reopening item",
  DecisionState.getDecisionNote(parsedNotes, "ex_001") === "Client confirmed tip added."
);
check(
  "Blank notes are removed from state",
  Object.prototype.hasOwnProperty.call(
    DecisionState.setDecisionNote(parsedNotes, "ex_001", "   "),
    "ex_001"
  ) === false
);

console.log("\n  Focus Mode (Show only unresolved):");
const queue = [
  { id: "ex_001", merchant: "A", diagnosis: "D1", match_state: "PROBABLE", confidence_pct: 90, amount: 10, date: "2026-01-02" },
  { id: "ex_002", merchant: "B", diagnosis: "D2", match_state: "POSSIBLE", confidence_pct: 70, amount: 30, date: "2026-01-03" },
  { id: "ex_003", merchant: "C", diagnosis: "D3", match_state: "NO MATCH", confidence_pct: 20, amount: 20, date: "2026-01-01" },
];
const resolutionState = {
  ex_001: "accepted",
  ex_002: "follow_up",
};
const visible = WorkbenchLogic.filterAndSortQueue(queue, {
  query: "",
  matchFilter: "all",
  sortKey: "confidence_desc",
  showOnlyUnresolved: true,
}, resolutionState);
check("Focus mode hides resolved items", visible.length === 1 && visible[0].id === "ex_003");

console.log("\n  Keyboard Navigation Regression:");
check(
  "List J remains move_down",
  WorkbenchLogic.getShortcutAction({
    mode: "list",
    key: "j",
    shiftKey: false,
    isInputFocused: false,
    searchFocused: false,
    modalOpen: false,
  }) === "move_down"
);
check(
  "Detail K remains prev_item",
  WorkbenchLogic.getShortcutAction({
    mode: "detail",
    key: "k",
    shiftKey: false,
    isInputFocused: false,
    searchFocused: false,
    modalOpen: false,
  }) === "prev_item"
);
check(
  "Shortcuts still disabled while typing in input/textarea",
  WorkbenchLogic.getShortcutAction({
    mode: "detail",
    key: "c",
    shiftKey: false,
    isInputFocused: true,
    searchFocused: false,
    modalOpen: false,
  }) === null
);

console.log(`\n${S.line.repeat(62)}`);
console.log(`  Results: ${passed}/${passed + failed} passed`);
if (failed === 0) {
  console.log(`  Phase 12 checks complete ${S.pass}`);
} else {
  console.log(`  Phase 12 checks failed: ${failed}`);
  process.exitCode = 1;
}
console.log(S.line.repeat(62));

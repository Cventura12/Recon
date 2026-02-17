"use strict";

const MemoryState = require("./web/workbench/memory_state.js");
const WorkbenchLogic = require("./web/workbench/workbench_logic.js");

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
console.log("  Phase 13: Local Memory Tests");
console.log(S.line.repeat(62));

console.log("\n  Alias Memory:");
let memoryState = { aliasMemory: {}, patternMemory: {} };
memoryState = MemoryState.recordAcceptedDecision(memoryState, {
  cardVendor: "YUM! BRANDS",
  receiptVendor: "Taco Bell",
  diagnosisKey: "TIP_TAX_VARIANCE",
});
check(
  "Accepting an item updates alias_memory",
  MemoryState.getAliasMapping(memoryState.aliasMemory, "YUM! BRANDS") === "Taco Bell"
);

console.log("\n  Pattern Frequency:");
memoryState = MemoryState.recordAcceptedDecision(memoryState, {
  cardVendor: "YUM! BRANDS",
  receiptVendor: "Taco Bell",
  diagnosisKey: "TIP_TAX_VARIANCE",
});
check(
  "Accepting multiple items increments pattern_memory count",
  MemoryState.getPatternCount(memoryState.patternMemory, "TIP_TAX_VARIANCE") === 2
);
check(
  "\"Seen Before\" condition is true when count >= 1",
  MemoryState.hasSeenBefore(memoryState.patternMemory, "TIP_TAX_VARIANCE") === true
);

console.log("\n  Persistence:");
const aliasRaw = MemoryState.serializeAliasMemory(memoryState.aliasMemory);
const patternRaw = MemoryState.serializePatternMemory(memoryState.patternMemory);
const aliasRoundtrip = MemoryState.parseAliasMemory(aliasRaw);
const patternRoundtrip = MemoryState.parsePatternMemory(patternRaw);
check(
  "Memory survives page refresh (localStorage roundtrip)",
  MemoryState.getAliasMapping(aliasRoundtrip, "YUM! BRANDS") === "Taco Bell"
    && MemoryState.getPatternCount(patternRoundtrip, "TIP_TAX_VARIANCE") === 2
);

console.log("\n  Keyboard Regression:");
check(
  "Keyboard navigation still works after memory UI",
  WorkbenchLogic.getShortcutAction({
    mode: "list",
    key: "j",
    shiftKey: false,
    isInputFocused: false,
    searchFocused: false,
    modalOpen: false,
  }) === "move_down"
);

console.log(`\n${S.line.repeat(62)}`);
console.log(`  Results: ${passed}/${passed + failed} passed`);
if (failed === 0) {
  console.log(`  Phase 13 checks complete ${S.pass}`);
} else {
  console.log(`  Phase 13 checks failed: ${failed}`);
  process.exitCode = 1;
}
console.log(S.line.repeat(62));

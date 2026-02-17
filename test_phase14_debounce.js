"use strict";

const WorkspaceSync = require("./web/workbench/workspace_sync.js");

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

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function main() {
  console.log(S.line.repeat(62));
  console.log("  Phase 14: Debounced Save Tests");
  console.log(S.line.repeat(62));

  let saveCalls = 0;
  const debounced = WorkspaceSync.createDebouncedAction(function () {
    saveCalls += 1;
  }, 80);

  console.log("\n  Debounce Behavior:");
  debounced.schedule("a");
  debounced.schedule("b");
  debounced.schedule("c");
  await wait(140);
  check("Rapid updates trigger one save call", saveCalls === 1);

  debounced.schedule("d");
  await wait(20);
  debounced.schedule("e");
  await wait(140);
  check("Second burst triggers one additional save call", saveCalls === 2);

  console.log("\n  Flush / Cancel:");
  debounced.schedule("f");
  debounced.cancel();
  await wait(140);
  check("Cancel prevents pending save", saveCalls === 2);

  debounced.schedule("g");
  debounced.flush();
  await wait(20);
  check("Flush executes pending save immediately", saveCalls === 3);

  console.log(`\n${S.line.repeat(62)}`);
  console.log(`  Results: ${passed}/${passed + failed} passed`);
  if (failed === 0) {
    console.log(`  Phase 14 debounce checks complete ${S.pass}`);
  } else {
    console.log(`  Phase 14 debounce checks failed: ${failed}`);
    process.exitCode = 1;
  }
  console.log(S.line.repeat(62));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

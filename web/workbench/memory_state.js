(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.MemoryState = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const STORAGE_KEYS = {
    alias: "alias_memory",
    pattern: "pattern_memory",
  };

  function parseObject(raw) {
    if (!raw) {
      return {};
    }
    try {
      const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
      if (!parsed || typeof parsed !== "object") {
        return {};
      }
      return parsed;
    } catch (_unused) {
      return {};
    }
  }

  function normalizeCardVendor(value) {
    return String(value || "").trim().replace(/\s+/g, " ").toUpperCase();
  }

  function normalizeDiagnosisKey(value) {
    return String(value || "")
      .trim()
      .toUpperCase()
      .replace(/\s+/g, "_");
  }

  function parseAliasMemory(raw) {
    const parsed = parseObject(raw);
    const result = {};
    Object.keys(parsed).forEach(function (key) {
      const normalizedKey = normalizeCardVendor(key);
      const vendor = String(parsed[key] || "").trim();
      if (normalizedKey && vendor) {
        result[normalizedKey] = vendor;
      }
    });
    return result;
  }

  function serializeAliasMemory(memory) {
    return JSON.stringify(memory || {});
  }

  function setAliasMapping(memory, cardVendor, receiptVendor) {
    const next = Object.assign({}, memory || {});
    const normalizedCard = normalizeCardVendor(cardVendor);
    const receiptText = String(receiptVendor || "").trim();
    if (!normalizedCard || !receiptText) {
      return next;
    }
    next[normalizedCard] = receiptText;
    return next;
  }

  function getAliasMapping(memory, cardVendor) {
    const normalizedCard = normalizeCardVendor(cardVendor);
    if (!normalizedCard) {
      return "";
    }
    const value = memory ? memory[normalizedCard] : "";
    return typeof value === "string" ? value : "";
  }

  function parsePatternMemory(raw) {
    const parsed = parseObject(raw);
    const result = {};
    Object.keys(parsed).forEach(function (key) {
      const normalizedKey = normalizeDiagnosisKey(key);
      const count = Number(parsed[key]);
      if (normalizedKey && Number.isFinite(count) && count > 0) {
        result[normalizedKey] = Math.floor(count);
      }
    });
    return result;
  }

  function serializePatternMemory(memory) {
    return JSON.stringify(memory || {});
  }

  function incrementPatternCount(memory, diagnosisKey) {
    const next = Object.assign({}, memory || {});
    const normalizedKey = normalizeDiagnosisKey(diagnosisKey);
    if (!normalizedKey) {
      return next;
    }
    const current = Number(next[normalizedKey]);
    next[normalizedKey] = Number.isFinite(current) && current > 0
      ? Math.floor(current) + 1
      : 1;
    return next;
  }

  function getPatternCount(memory, diagnosisKey) {
    const normalizedKey = normalizeDiagnosisKey(diagnosisKey);
    if (!normalizedKey || !memory) {
      return 0;
    }
    const count = Number(memory[normalizedKey]);
    if (!Number.isFinite(count) || count < 1) {
      return 0;
    }
    return Math.floor(count);
  }

  function hasSeenBefore(memory, diagnosisKey) {
    return getPatternCount(memory, diagnosisKey) >= 1;
  }

  function recordAcceptedDecision(memoryState, context) {
    const safeState = memoryState || {};
    const ctx = context || {};
    const aliasMemory = setAliasMapping(
      safeState.aliasMemory || {},
      ctx.cardVendor,
      ctx.receiptVendor
    );
    const patternMemory = incrementPatternCount(
      safeState.patternMemory || {},
      ctx.diagnosisKey
    );
    return {
      aliasMemory: aliasMemory,
      patternMemory: patternMemory,
    };
  }

  return {
    STORAGE_KEYS: STORAGE_KEYS,
    normalizeCardVendor: normalizeCardVendor,
    normalizeDiagnosisKey: normalizeDiagnosisKey,
    parseAliasMemory: parseAliasMemory,
    serializeAliasMemory: serializeAliasMemory,
    setAliasMapping: setAliasMapping,
    getAliasMapping: getAliasMapping,
    parsePatternMemory: parsePatternMemory,
    serializePatternMemory: serializePatternMemory,
    incrementPatternCount: incrementPatternCount,
    getPatternCount: getPatternCount,
    hasSeenBefore: hasSeenBefore,
    recordAcceptedDecision: recordAcceptedDecision,
  };
});

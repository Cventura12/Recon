(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.DecisionState = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const STORAGE_KEYS = {
    resolution: "workbench_resolution_state_v1",
    note: "workbench_decision_note_v1",
  };

  function normalizeResolution(value) {
    const text = String(value || "").trim().toLowerCase();
    if (text === "accepted" || text === "accept") {
      return "accepted";
    }
    if (text === "ignored" || text === "ignore") {
      return "ignored";
    }
    if (text === "follow_up" || text === "needs_follow_up" || text === "followup") {
      return "follow_up";
    }
    if (text === "reviewed") {
      return "accepted";
    }
    return "unreviewed";
  }

  function parseObjectMap(raw) {
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

  function parseResolutionState(raw) {
    const parsed = parseObjectMap(raw);
    const result = {};
    Object.keys(parsed).forEach(function (key) {
      const normalized = normalizeResolution(parsed[key]);
      if (normalized !== "unreviewed") {
        result[key] = normalized;
      }
    });
    return result;
  }

  function serializeResolutionState(state) {
    return JSON.stringify(state || {});
  }

  function getResolutionState(state, itemId) {
    if (!state || !itemId) {
      return "unreviewed";
    }
    return normalizeResolution(state[itemId]);
  }

  function setResolutionState(state, itemId, value) {
    const next = Object.assign({}, state || {});
    if (!itemId) {
      return next;
    }
    const normalized = normalizeResolution(value);
    if (normalized === "unreviewed") {
      delete next[itemId];
    } else {
      next[itemId] = normalized;
    }
    return next;
  }

  function parseDecisionNotes(raw) {
    const parsed = parseObjectMap(raw);
    const result = {};
    Object.keys(parsed).forEach(function (key) {
      const value = parsed[key];
      if (typeof value === "string") {
        result[key] = value;
      }
    });
    return result;
  }

  function serializeDecisionNotes(notes) {
    return JSON.stringify(notes || {});
  }

  function getDecisionNote(notes, itemId) {
    if (!notes || !itemId) {
      return "";
    }
    const value = notes[itemId];
    return typeof value === "string" ? value : "";
  }

  function setDecisionNote(notes, itemId, value) {
    const next = Object.assign({}, notes || {});
    if (!itemId) {
      return next;
    }
    const text = String(value || "");
    if (!text.trim()) {
      delete next[itemId];
    } else {
      next[itemId] = text;
    }
    return next;
  }

  function shouldHideResolved(itemId, resolutionState, showOnlyUnresolved) {
    return !!showOnlyUnresolved && getResolutionState(resolutionState, itemId) !== "unreviewed";
  }

  return {
    STORAGE_KEYS: STORAGE_KEYS,
    parseResolutionState: parseResolutionState,
    serializeResolutionState: serializeResolutionState,
    getResolutionState: getResolutionState,
    setResolutionState: setResolutionState,
    parseDecisionNotes: parseDecisionNotes,
    serializeDecisionNotes: serializeDecisionNotes,
    getDecisionNote: getDecisionNote,
    setDecisionNote: setDecisionNote,
    shouldHideResolved: shouldHideResolved,
  };
});

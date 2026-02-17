(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.WorkbenchLogic = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function normalizeText(value) {
    return String(value || "").trim().toLowerCase();
  }

  function toNumber(value, fallback) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
    return fallback;
  }

  function itemConfidencePct(item) {
    if (Object.prototype.hasOwnProperty.call(item || {}, "confidence_pct")) {
      return toNumber(item.confidence_pct, 0);
    }
    if (Object.prototype.hasOwnProperty.call(item || {}, "confidence")) {
      const confidence = toNumber(item.confidence, 0);
      return confidence <= 1.0 ? confidence * 100 : confidence;
    }
    return 0;
  }

  function normalizeMatchState(state) {
    const raw = normalizeText(state).replace(/\s+/g, "_");
    if (raw === "probable" || raw === "probable_match") {
      return "probable";
    }
    if (raw === "possible" || raw === "possible_match") {
      return "possible";
    }
    if (
      raw === "no_match"
      || raw === "no_confident"
      || raw === "no_confidence"
      || raw === "no_confident_match"
      || raw === "clean_match"
    ) {
      return "no_confident";
    }
    return "no_confident";
  }

  function parseDateForSort(value) {
    const text = String(value || "").trim();
    if (!text) {
      return 0;
    }
    const ts = Date.parse(text);
    if (!Number.isFinite(ts)) {
      return 0;
    }
    return ts;
  }

  function parseReviewState(raw) {
    if (!raw) {
      return {};
    }
    try {
      const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
      if (!parsed || typeof parsed !== "object") {
        return {};
      }
      const result = {};
      Object.keys(parsed).forEach(function (key) {
        const value = normalizeResolution(parsed[key]);
        if (value !== "unreviewed") {
          result[key] = value;
        }
      });
      return result;
    } catch (_unused) {
      return {};
    }
  }

  function normalizeResolution(value) {
    const text = normalizeText(value).replace(/\s+/g, "_");
    if (text === "accepted" || text === "reviewed" || text === "accept") {
      return "accepted";
    }
    if (text === "ignored" || text === "ignore") {
      return "ignored";
    }
    if (text === "follow_up" || text === "needs_follow_up" || text === "followup") {
      return "follow_up";
    }
    return "unreviewed";
  }

  function serializeReviewState(reviewState) {
    return JSON.stringify(reviewState || {});
  }

  function setReviewState(reviewState, itemId, value) {
    const next = Object.assign({}, reviewState || {});
    if (!itemId) {
      return next;
    }
    const normalized = normalizeResolution(value);
    if (normalized !== "unreviewed") {
      next[itemId] = normalized;
    } else {
      delete next[itemId];
    }
    return next;
  }

  function getReviewState(reviewState, itemId) {
    if (!itemId || !reviewState) {
      return "unreviewed";
    }
    return normalizeResolution(reviewState[itemId]);
  }

  function isReviewed(reviewState, itemId) {
    return getReviewState(reviewState, itemId) === "accepted";
  }

  function shouldHideReviewedItem(itemId, reviewState, hideReviewed) {
    return !!hideReviewed && isReviewed(reviewState, itemId);
  }

  function shouldHideResolvedItem(itemId, reviewState, showOnlyUnresolved) {
    if (!showOnlyUnresolved) {
      return false;
    }
    return getReviewState(reviewState, itemId) !== "unreviewed";
  }

  function filterAndSortQueue(items, controls, reviewState) {
    const source = Array.isArray(items) ? items.slice() : [];
    const query = normalizeText(controls && controls.query);
    const matchFilter = normalizeText((controls && controls.matchFilter) || "all");
    const hideReviewed = !!(controls && controls.hideReviewed);
    const showOnlyUnresolved = !!(controls && controls.showOnlyUnresolved);
    const sortKey = normalizeText((controls && controls.sortKey) || "confidence_desc");

    const filtered = source.filter(function (item) {
      const id = String(item && item.id ? item.id : "");
      if (shouldHideResolvedItem(id, reviewState, showOnlyUnresolved)) {
        return false;
      }
      if (shouldHideReviewedItem(id, reviewState, hideReviewed)) {
        return false;
      }

      const state = normalizeMatchState(item && item.match_state);
      if (matchFilter !== "all" && state !== matchFilter) {
        return false;
      }

      if (!query) {
        return true;
      }

      const haystack = [
        item && item.merchant,
        item && item.vendor,
        item && item.diagnosis,
        item && item.id,
      ]
        .map(normalizeText)
        .join(" ");
      return haystack.includes(query);
    });

    filtered.sort(function (a, b) {
      if (sortKey === "amount_desc") {
        return toNumber(b && b.amount, 0) - toNumber(a && a.amount, 0);
      }
      if (sortKey === "date_desc") {
        return parseDateForSort(b && b.date) - parseDateForSort(a && a.date);
      }
      return itemConfidencePct(b) - itemConfidencePct(a);
    });

    return filtered;
  }

  function getNextQueueId(ids, currentId) {
    const arr = Array.isArray(ids) ? ids : [];
    const idx = arr.indexOf(currentId);
    if (idx < 0 || idx >= arr.length - 1) {
      return null;
    }
    return arr[idx + 1];
  }

  function getPrevQueueId(ids, currentId) {
    const arr = Array.isArray(ids) ? ids : [];
    const idx = arr.indexOf(currentId);
    if (idx <= 0) {
      return null;
    }
    return arr[idx - 1];
  }

  function isTypingTarget(target) {
    if (!target) {
      return false;
    }
    const tag = String(target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") {
      return true;
    }
    return !!target.isContentEditable;
  }

  function getShortcutAction(context) {
    const mode = normalizeText(context && context.mode) || "list";
    const rawKey = context && context.key ? String(context.key) : "";
    const key = rawKey.toLowerCase();
    const shift = !!(context && context.shiftKey);
    const isInputFocused = !!(context && context.isInputFocused);
    const searchFocused = !!(context && context.searchFocused);
    const modalOpen = !!(context && context.modalOpen);

    if (modalOpen) {
      if (key === "escape" || key === "esc") {
        return "close_shortcuts_modal";
      }
      return null;
    }

    if (mode === "list") {
      if ((key === "escape" || key === "esc") && searchFocused) {
        return "clear_search_focus";
      }
      if (isInputFocused) {
        return null;
      }
      if (key === "j") {
        return "move_down";
      }
      if (key === "k") {
        return "move_up";
      }
      if (key === "enter") {
        return "open_selected";
      }
      if (rawKey === "/" || key === "/") {
        return "focus_search";
      }
      if (key === "escape" || key === "esc") {
        return "clear_search_focus";
      }
      return null;
    }

    if (mode === "detail") {
      if (isInputFocused) {
        return null;
      }
      if (key === "j") {
        return "next_item";
      }
      if (key === "k") {
        return "prev_item";
      }
      if (key === "c") {
        return shift ? "copy_and_next" : "copy_memo";
      }
      if (key === "escape" || key === "esc") {
        return "back_to_list";
      }
      return null;
    }

    return null;
  }

  function buildAuditMemo(payload) {
    const safePayload = payload || {};
    const ui = safePayload.ui || {};
    const diagnosis = safePayload.diagnosis || {};
    const topCandidate = ui.top_candidate || safePayload.top_match || null;

    let state = String(ui.match_state_badge || "").toUpperCase();
    if (!state) {
      const confidence = toNumber(safePayload.confidence, 0);
      if (safePayload.status === "no_match" || confidence < 50) {
        state = "NO MATCH";
      } else if (confidence >= 80) {
        state = "PROBABLE";
      } else {
        state = "POSSIBLE";
      }
    }
    if (state === "NO CONFIDENT") {
      state = "NO MATCH";
    }

    const confidenceNum = toNumber(safePayload.confidence, 0);
    const label = String(diagnosis.label_summary || "Unclassified");
    const timestamp = String(ui.analysis_timestamp_utc || new Date().toISOString());

    const lines = [];
    lines.push(state + " - " + confidenceNum.toFixed(1) + "%");
    lines.push("Diagnosis: " + label);

    if (topCandidate) {
      const merchant = String(topCandidate.merchant || "--");
      const amount = toNumber(topCandidate.amount, NaN);
      const amountText = Number.isNaN(amount) ? "--" : "$" + amount.toFixed(2);
      const date = String(topCandidate.date || "--");

      const vendorScore = toNumber(topCandidate.vendor_similarity_score, NaN);
      const amountPct = toNumber(topCandidate.amount_delta_pct, NaN);
      const dateDelta = topCandidate.date_delta_days;

      lines.push("Candidate: " + merchant + " | " + amountText + " | " + date);
      lines.push(
        "Scores: vendor "
          + (Number.isNaN(vendorScore) ? "--" : vendorScore.toFixed(1))
          + ", amount_delta_pct "
          + (Number.isNaN(amountPct) ? "--" : amountPct.toFixed(1) + "%")
          + ", date_delta "
          + (typeof dateDelta === "number" ? String(dateDelta) : "--")
          + " day(s)"
      );
    }

    const evidence = Array.isArray(safePayload.evidence) ? safePayload.evidence.slice(0, 4) : [];
    if (evidence.length) {
      lines.push("Evidence:");
      evidence.forEach(function (item) {
        lines.push("- " + String(item));
      });
    }
    lines.push("Analysis timestamp (UTC): " + timestamp);
    return lines.join("\n");
  }

  return {
    filterAndSortQueue: filterAndSortQueue,
    getNextQueueId: getNextQueueId,
    getPrevQueueId: getPrevQueueId,
    getShortcutAction: getShortcutAction,
    isTypingTarget: isTypingTarget,
    normalizeResolution: normalizeResolution,
    parseReviewState: parseReviewState,
    serializeReviewState: serializeReviewState,
    setReviewState: setReviewState,
    getReviewState: getReviewState,
    shouldHideReviewedItem: shouldHideReviewedItem,
    shouldHideResolvedItem: shouldHideResolvedItem,
    buildAuditMemo: buildAuditMemo,
  };
});

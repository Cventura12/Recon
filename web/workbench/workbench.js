(function () {
  const DEFAULT_API_BASE = "http://127.0.0.1:8000";
  const API_BASE_STORAGE_KEY = "diagnosticApiBase";
  const Decision = window.DecisionState;
  const Memory = window.MemoryState;
  const WorkspaceSync = window.WorkspaceSync;
  const WORKSPACE_ID = "default";
  const SAVE_DEBOUNCE_MS = 800;

  const queueStatusEl = document.getElementById("queue-status");
  const queueBodyEl = document.getElementById("queue-body");
  const queueSearchEl = document.getElementById("queue-search");
  const queueFilterPillsEl = document.getElementById("queue-filter-pills");
  const queueSortEl = document.getElementById("queue-sort");
  const showOnlyUnresolvedEl = document.getElementById("show-only-unresolved");
  const openDiagnoseLinkEl = document.getElementById("open-diagnose-link");
  const sessionIntakeFormEl = document.getElementById("session-intake-form");
  const intakeTransactionsCsvEl = document.getElementById("intake-transactions-csv");
  const intakeReceiptsEl = document.getElementById("intake-receipts");
  const intakeSubmitBtn = document.getElementById("session-intake-submit");
  const intakeStatusEl = document.getElementById("session-intake-status");
  const currentSessionLabelEl = document.getElementById("current-session-label");
  const clearCurrentSessionBtn = document.getElementById("clear-current-session");
  const workspaceSaveStatusEl = document.getElementById("workspace-save-status");

  const detailEmptyEl = document.getElementById("detail-empty");
  const detailViewEl = document.getElementById("detail-view");
  const detailMatchStateEl = document.getElementById("detail-match-state");
  const detailConfidenceEl = document.getElementById("detail-confidence");
  const detailDiagnosisEl = document.getElementById("detail-diagnosis");
  const detailKnownAliasBadgeEl = document.getElementById("detail-known-alias-badge");
  const detailPatternHintEl = document.getElementById("detail-pattern-hint");
  const detailEvidenceEl = document.getElementById("detail-evidence");
  const detailResolutionStateEl = document.getElementById("detail-resolution-state");
  const detailResolutionOptionsEl = document.getElementById("detail-resolution-options");
  const detailResolutionClearBtn = document.getElementById("detail-resolution-clear");
  const detailAliasMemorySectionEl = document.getElementById("detail-alias-memory-section");
  const detailAliasMemoryTextEl = document.getElementById("detail-alias-memory-text");

  const detailMerchantEl = document.getElementById("detail-merchant");
  const detailAmountEl = document.getElementById("detail-amount");
  const detailDateEl = document.getElementById("detail-date");
  const detailTransactionIdEl = document.getElementById("detail-transaction-id");
  const detailVendorScoreEl = document.getElementById("detail-vendor-score");
  const detailAmountPctEl = document.getElementById("detail-amount-pct");
  const detailDateDaysEl = document.getElementById("detail-date-days");
  const detailAuditNoteEl = document.getElementById("detail-audit-note");
  const detailDecisionNoteEl = document.getElementById("detail-decision-note");

  const backToWorkbenchBtn = document.getElementById("back-to-workbench");
  const prevItemBtn = document.getElementById("prev-item");
  const nextItemBtn = document.getElementById("next-item");
  const copySummaryBtn = document.getElementById("detail-copy-summary");
  const copyNextBtn = document.getElementById("detail-copy-next");
  const downloadJsonBtn = document.getElementById("detail-download-json");

  const shortcutHelpLinkEl = document.getElementById("shortcut-help-link");
  const shortcutModalEl = document.getElementById("shortcut-modal");
  const shortcutModalCloseEl = document.getElementById("shortcut-modal-close");
  const toastEl = document.getElementById("toast");

  const state = {
    queueItems: [],
    visibleItems: [],
    selectedId: null,
    currentId: null,
    currentPayload: null,
    resolutionState: {},
    decisionNotes: {},
    aliasMemory: {},
    patternMemory: {},
    controls: {
      query: "",
      matchFilter: "all",
      sortKey: "confidence_desc",
      showOnlyUnresolved: false,
    },
    toastTimer: null,
    modalOpen: false,
    currentSessionId: null,
    saveStatus: "Saved",
    workspaceLoaded: false,
    workspaceSaver: null,
  };

  function apiBase() {
    const params = new URLSearchParams(window.location.search);
    const paramApi = params.get("api");
    if (paramApi && paramApi.trim()) {
      const normalized = paramApi.trim().replace(/\/+$/, "");
      localStorage.setItem(API_BASE_STORAGE_KEY, normalized);
      return normalized;
    }
    const stored = localStorage.getItem(API_BASE_STORAGE_KEY);
    if (stored && stored.trim()) {
      return stored.trim().replace(/\/+$/, "");
    }
    return DEFAULT_API_BASE;
  }

  function workbenchBasePath() {
    const segments = window.location.pathname.split("/");
    const idx = segments.findIndex(function (segment) {
      return segment === "workbench";
    });
    if (idx === -1) {
      return "/workbench";
    }
    const base = segments.slice(0, idx + 1).join("/");
    return base || "/workbench";
  }

  function listUrl() {
    return `${workbenchBasePath()}/?api=${encodeURIComponent(apiBase())}`;
  }

  function detailUrl(itemId) {
    return `${workbenchBasePath()}/${encodeURIComponent(itemId)}?api=${encodeURIComponent(apiBase())}`;
  }

  function parseRouteId() {
    const segments = window.location.pathname.split("/").filter(Boolean);
    const idx = segments.lastIndexOf("workbench");
    if (idx >= 0 && segments.length > idx + 1) {
      const maybeId = segments[idx + 1];
      if (maybeId && maybeId !== "index.html") {
        return decodeURIComponent(maybeId);
      }
    }
    const params = new URLSearchParams(window.location.search);
    const queryId = params.get("id");
    if (queryId && queryId.trim()) {
      return queryId.trim();
    }
    return null;
  }

  function formatCurrency(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return "--";
    }
    return `$${numeric.toFixed(2)}`;
  }

  function formatPercent(value, digits) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return "--";
    }
    return `${numeric.toFixed(digits)}%`;
  }

  function resolutionLabel(value) {
    if (value === "accepted") {
      return "Accepted";
    }
    if (value === "ignored") {
      return "Ignored";
    }
    if (value === "follow_up") {
      return "Needs Follow-up";
    }
    return "Unreviewed";
  }

  function resolutionIcon(value) {
    if (value === "accepted") {
      return "\u2713";
    }
    if (value === "follow_up") {
      return "\u26A0";
    }
    if (value === "ignored") {
      return "\u2298";
    }
    return "";
  }

  function normalizeCardDescriptor(value) {
    if (Memory && Memory.normalizeCardVendor) {
      return Memory.normalizeCardVendor(value);
    }
    return String(value || "").trim().replace(/\s+/g, " ").toUpperCase();
  }

  function normalizeDiagnosisKey(value) {
    if (Memory && Memory.normalizeDiagnosisKey) {
      return Memory.normalizeDiagnosisKey(value);
    }
    return String(value || "").trim().toUpperCase().replace(/\s+/g, "_");
  }

  function diagnosisKeyFromPayloadOrItem(payload, item) {
    const labels = payload && payload.diagnosis && Array.isArray(payload.diagnosis.labels)
      ? payload.diagnosis.labels
      : [];
    if (labels.length > 0) {
      return normalizeDiagnosisKey(labels[0]);
    }
    if (item && item.diagnosis) {
      return normalizeDiagnosisKey(item.diagnosis);
    }
    const summary = payload && payload.diagnosis ? payload.diagnosis.label_summary : "";
    return normalizeDiagnosisKey(summary);
  }

  function cardDescriptorFromPayloadOrItem(payload, item) {
    if (payload && payload.ui && payload.ui.top_candidate && payload.ui.top_candidate.merchant) {
      return String(payload.ui.top_candidate.merchant);
    }
    if (payload && payload.top_match && payload.top_match.merchant) {
      return String(payload.top_match.merchant);
    }
    if (item && item.merchant) {
      return String(item.merchant);
    }
    return "";
  }

  function receiptVendorFromPayloadOrItem(payload, item) {
    if (payload && payload.receipt && payload.receipt.vendor) {
      return String(payload.receipt.vendor);
    }
    if (item && item.vendor) {
      return String(item.vendor);
    }
    return "";
  }

  function queueBadgeClass(matchState) {
    const stateText = String(matchState || "").toUpperCase();
    if (stateText === "PROBABLE" || stateText === "PROBABLE_MATCH") {
      return "queue-badge-probable";
    }
    if (stateText === "POSSIBLE" || stateText === "POSSIBLE_MATCH") {
      return "queue-badge-possible";
    }
    return "queue-badge-no-match";
  }

  function queueBadgeText(matchState) {
    const stateText = String(matchState || "").toUpperCase();
    if (stateText === "PROBABLE_MATCH" || stateText === "PROBABLE") {
      return "PROBABLE";
    }
    if (stateText === "POSSIBLE_MATCH" || stateText === "POSSIBLE") {
      return "POSSIBLE";
    }
    return "NO CONFIDENT";
  }

  function detailBadgeState(payload) {
    if (payload && payload.ui && payload.ui.match_state_badge) {
      const badge = String(payload.ui.match_state_badge || "").toUpperCase();
      if (badge === "NO CONFIDENT") {
        return "NO MATCH";
      }
      return badge;
    }
    if (!payload || payload.status === "no_match") {
      return "NO MATCH";
    }
    const confidence = Number(payload.confidence || 0);
    if (confidence >= 80) {
      return "PROBABLE";
    }
    if (confidence >= 50) {
      return "POSSIBLE";
    }
    return "NO MATCH";
  }

  function applyDetailBadge(stateText) {
    detailMatchStateEl.textContent = stateText;
    detailMatchStateEl.className = "badge";
    if (stateText === "PROBABLE") {
      detailMatchStateEl.classList.add("badge-probable");
    } else if (stateText === "POSSIBLE") {
      detailMatchStateEl.classList.add("badge-possible");
    } else {
      detailMatchStateEl.classList.add("badge-no-confident");
    }
  }

  function setQueueStatus(message, isError) {
    queueStatusEl.textContent = message || "";
    queueStatusEl.classList.toggle("error", !!isError);
  }

  function setIntakeStatus(message, isError) {
    if (!intakeStatusEl) {
      return;
    }
    intakeStatusEl.textContent = message || "";
    intakeStatusEl.classList.toggle("error", !!isError);
  }

  function updateSessionLabel() {
    const label = state.currentSessionId ? `Session: ${state.currentSessionId}` : "Session: --";
    currentSessionLabelEl.textContent = label;
    clearCurrentSessionBtn.disabled = !state.currentSessionId;
  }

  function showToast(message) {
    if (!toastEl) {
      return;
    }
    toastEl.textContent = message;
    toastEl.hidden = false;
    toastEl.classList.add("visible");
    if (state.toastTimer) {
      clearTimeout(state.toastTimer);
    }
    state.toastTimer = setTimeout(function () {
      toastEl.classList.remove("visible");
      toastEl.hidden = true;
    }, 1350);
  }

  function setWorkspaceSaveStatus(text, isError) {
    state.saveStatus = text;
    if (!workspaceSaveStatusEl) {
      return;
    }
    workspaceSaveStatusEl.textContent = text;
    workspaceSaveStatusEl.classList.toggle("error", !!isError);
  }

  function buildWorkspaceSnapshot() {
    return {
      workspace_id: WORKSPACE_ID,
      workbench_queue: state.queueItems.slice(),
      resolution_state: Object.assign({}, state.resolutionState || {}),
      decision_notes: Object.assign({}, state.decisionNotes || {}),
      alias_memory: Object.assign({}, state.aliasMemory || {}),
      pattern_memory: Object.assign({}, state.patternMemory || {}),
      last_selected_exception_id: state.currentId || state.selectedId || null,
      show_only_unresolved: !!state.controls.showOnlyUnresolved,
    };
  }

  function applyWorkspaceSnapshot(snapshot) {
    const data = snapshot && typeof snapshot === "object" ? snapshot : {};
    const queue = Array.isArray(data.workbench_queue) ? data.workbench_queue : [];
    state.queueItems = queue.slice();

    if (Decision && Decision.parseResolutionState) {
      state.resolutionState = Decision.parseResolutionState(data.resolution_state || {});
    } else {
      state.resolutionState = WorkbenchLogic.parseReviewState(data.resolution_state || {});
    }
    if (Decision && Decision.parseDecisionNotes) {
      state.decisionNotes = Decision.parseDecisionNotes(data.decision_notes || {});
    } else {
      state.decisionNotes = {};
    }
    if (Memory && Memory.parseAliasMemory) {
      state.aliasMemory = Memory.parseAliasMemory(data.alias_memory || {});
    } else {
      state.aliasMemory = {};
    }
    if (Memory && Memory.parsePatternMemory) {
      state.patternMemory = Memory.parsePatternMemory(data.pattern_memory || {});
    } else {
      state.patternMemory = {};
    }

    state.controls.showOnlyUnresolved = !!data.show_only_unresolved;

    const selected = typeof data.last_selected_exception_id === "string"
      ? data.last_selected_exception_id.trim()
      : "";
    if (selected) {
      state.selectedId = selected;
    }
  }

  async function fetchWorkspaceLoad() {
    const response = await fetch(`${apiBase()}/workspace/load`, { method: "GET" });
    if (!response.ok) {
      throw new Error(`Failed to load workspace (${response.status})`);
    }
    return response.json();
  }

  async function postWorkspaceSave(snapshot) {
    const response = await fetch(`${apiBase()}/workspace/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(snapshot),
    });
    if (!response.ok) {
      let detail = `Failed to save workspace (${response.status})`;
      try {
        const body = await response.json();
        if (body && body.detail) {
          detail = String(body.detail);
        }
      } catch (_unused) {
        // Keep fallback detail.
      }
      throw new Error(detail);
    }
    return response.json();
  }

  async function persistWorkspaceNow(reason) {
    try {
      setWorkspaceSaveStatus("Saving...", false);
      await postWorkspaceSave(buildWorkspaceSnapshot());
      setWorkspaceSaveStatus("Saved", false);
    } catch (error) {
      setWorkspaceSaveStatus("Save failed", true);
      setQueueStatus(error.message || `Workspace save failed (${reason || "update"})`, true);
    }
  }

  function scheduleWorkspaceSave(reason) {
    if (!state.workspaceLoaded || !state.workspaceSaver) {
      return;
    }
    setWorkspaceSaveStatus("Saving...", false);
    state.workspaceSaver.schedule(reason || "update");
  }

  function getResolution(itemId) {
    if (Decision && Decision.getResolutionState) {
      return Decision.getResolutionState(state.resolutionState, itemId);
    }
    return WorkbenchLogic.getReviewState(state.resolutionState, itemId);
  }

  function setResolution(itemId, value) {
    if (Decision && Decision.setResolutionState) {
      state.resolutionState = Decision.setResolutionState(state.resolutionState, itemId, value);
    } else {
      state.resolutionState = WorkbenchLogic.setReviewState(state.resolutionState, itemId, value);
    }
    scheduleWorkspaceSave("resolution");
  }

  function getDecisionNote(itemId) {
    if (Decision && Decision.getDecisionNote) {
      return Decision.getDecisionNote(state.decisionNotes, itemId);
    }
    return "";
  }

  function setDecisionNote(itemId, value) {
    if (Decision && Decision.setDecisionNote) {
      state.decisionNotes = Decision.setDecisionNote(state.decisionNotes, itemId, value);
    } else {
      const next = Object.assign({}, state.decisionNotes || {});
      if (!String(value || "").trim()) {
        delete next[itemId];
      } else {
        next[itemId] = String(value || "");
      }
      state.decisionNotes = next;
    }
    scheduleWorkspaceSave("decision_note");
  }

  function getAliasForCardDescriptor(cardDescriptor) {
    if (Memory && Memory.getAliasMapping) {
      return Memory.getAliasMapping(state.aliasMemory, cardDescriptor);
    }
    const key = normalizeCardDescriptor(cardDescriptor);
    return state.aliasMemory[key] || "";
  }

  function getPatternCountForDiagnosis(diagnosisKey) {
    if (Memory && Memory.getPatternCount) {
      return Memory.getPatternCount(state.patternMemory, diagnosisKey);
    }
    const key = normalizeDiagnosisKey(diagnosisKey);
    const value = Number(state.patternMemory[key]);
    return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
  }

  function updateMemoryOnAcceptedTransition(itemId, previousResolution, nextResolution) {
    if (previousResolution === "accepted" || nextResolution !== "accepted") {
      return;
    }

    const item = state.queueItems.find(function (queueItem) {
      return queueItem.id === itemId;
    }) || null;
    const payload = state.currentPayload;

    const cardVendor = cardDescriptorFromPayloadOrItem(payload, item);
    const receiptVendor = receiptVendorFromPayloadOrItem(payload, item);
    const diagnosisKey = diagnosisKeyFromPayloadOrItem(payload, item);

    if (Memory && Memory.recordAcceptedDecision) {
      const updated = Memory.recordAcceptedDecision(
        {
          aliasMemory: state.aliasMemory,
          patternMemory: state.patternMemory,
        },
        {
          cardVendor: cardVendor,
          receiptVendor: receiptVendor,
          diagnosisKey: diagnosisKey,
        }
      );
      state.aliasMemory = updated.aliasMemory;
      state.patternMemory = updated.patternMemory;
    } else {
      const aliasKey = normalizeCardDescriptor(cardVendor);
      if (aliasKey && receiptVendor) {
        state.aliasMemory[aliasKey] = receiptVendor;
      }
      const patternKey = normalizeDiagnosisKey(diagnosisKey);
      if (patternKey) {
        const current = Number(state.patternMemory[patternKey]);
        state.patternMemory[patternKey] = Number.isFinite(current) && current > 0
          ? Math.floor(current) + 1
          : 1;
      }
    }

    scheduleWorkspaceSave("memory_update");
  }

  function updateResolutionControls() {
    const resolution = getResolution(state.currentId);
    detailResolutionStateEl.textContent = `Resolution: ${resolutionLabel(resolution)}`;

    const radios = detailResolutionOptionsEl
      ? detailResolutionOptionsEl.querySelectorAll("input[name='detail-resolution']")
      : [];
    radios.forEach(function (radio) {
      radio.checked = radio.value === resolution;
    });
    if (resolution === "unreviewed") {
      radios.forEach(function (radio) {
        radio.checked = false;
      });
    }
  }

  function updateDecisionNoteInput() {
    if (!detailDecisionNoteEl) {
      return;
    }
    detailDecisionNoteEl.value = state.currentId ? getDecisionNote(state.currentId) : "";
  }

  function renderMemoryHints(payload, item) {
    const diagnosisKey = diagnosisKeyFromPayloadOrItem(payload, item);
    const patternCount = getPatternCountForDiagnosis(diagnosisKey);
    if (detailPatternHintEl) {
      if (patternCount > 0) {
        const suffix = patternCount === 1 ? "" : "s";
        detailPatternHintEl.textContent = `Previously accepted ${patternCount} time${suffix}.`;
        detailPatternHintEl.hidden = false;
      } else {
        detailPatternHintEl.textContent = "";
        detailPatternHintEl.hidden = true;
      }
    }

    const cardVendor = cardDescriptorFromPayloadOrItem(payload, item);
    const normalizedCard = normalizeCardDescriptor(cardVendor);
    const alias = getAliasForCardDescriptor(cardVendor);
    const hasAlias = !!(normalizedCard && alias);

    if (detailKnownAliasBadgeEl) {
      detailKnownAliasBadgeEl.hidden = !hasAlias;
    }

    if (detailAliasMemorySectionEl && detailAliasMemoryTextEl) {
      if (hasAlias) {
        detailAliasMemoryTextEl.textContent =
          `Card descriptor '${normalizedCard}' previously matched to '${alias}'.`;
        detailAliasMemorySectionEl.hidden = false;
      } else {
        detailAliasMemoryTextEl.textContent = "";
        detailAliasMemorySectionEl.hidden = true;
      }
    }
  }

  function setQueueRows(items) {
    queueBodyEl.innerHTML = "";
    if (!items.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 5;
      cell.className = "queue-empty";
      cell.textContent = "No exceptions in queue for current filters.";
      row.appendChild(cell);
      queueBodyEl.appendChild(row);
      return;
    }

    items.forEach(function (item) {
      const row = document.createElement("tr");
      row.className = "queue-row";
      if (item.id === state.selectedId) {
        row.classList.add("selected");
      }

      const resolution = getResolution(item.id);
      if (resolution === "accepted") {
        row.classList.add("resolution-accepted");
      } else if (resolution === "follow_up") {
        row.classList.add("resolution-follow-up");
      } else if (resolution === "ignored") {
        row.classList.add("resolution-ignored");
      }

      row.addEventListener("click", function () {
        state.selectedId = item.id;
        openDetail(item.id, true);
      });

      const statusCell = document.createElement("td");
      const statusBadge = document.createElement("span");
      statusBadge.className = `queue-badge ${queueBadgeClass(item.match_state)}`;
      statusBadge.textContent = queueBadgeText(item.match_state);
      statusCell.appendChild(statusBadge);

      const merchantCell = document.createElement("td");
      const merchantLine = document.createElement("div");
      merchantLine.className = "queue-merchant-line";

      const icon = resolutionIcon(resolution);
      if (icon) {
        const iconEl = document.createElement("span");
        iconEl.className = `queue-resolution-icon resolution-icon-${resolution}`;
        iconEl.textContent = icon;
        iconEl.setAttribute("aria-hidden", "true");
        merchantLine.appendChild(iconEl);
      }

      const merchantValue = document.createElement("span");
      merchantValue.className = "queue-merchant";
      merchantValue.textContent = item.merchant || "--";
      merchantLine.appendChild(merchantValue);
      merchantCell.appendChild(merchantLine);

      if (resolution !== "unreviewed") {
        const resolutionLine = document.createElement("div");
        resolutionLine.className = "queue-resolution";
        resolutionLine.textContent = resolutionLabel(resolution);
        merchantCell.appendChild(resolutionLine);
      }

      const alias = getAliasForCardDescriptor(item.merchant || "");
      if (alias) {
        const aliasBadge = document.createElement("span");
        aliasBadge.className = "memory-badge queue-memory-badge";
        aliasBadge.textContent = "Known alias (from prior review)";
        merchantCell.appendChild(aliasBadge);
      }

      const amountCell = document.createElement("td");
      amountCell.textContent = formatCurrency(item.amount);

      const diagnosisCell = document.createElement("td");
      const diagnosisWrap = document.createElement("div");
      diagnosisWrap.className = "queue-diagnosis-wrap";
      const diagnosisText = document.createElement("span");
      diagnosisText.className = "queue-diagnosis-text";
      diagnosisText.textContent = item.diagnosis || "--";
      diagnosisWrap.appendChild(diagnosisText);

      if (getPatternCountForDiagnosis(item.diagnosis || "") >= 1) {
        const seenBadge = document.createElement("span");
        seenBadge.className = "memory-badge seen-before-badge";
        seenBadge.textContent = "Seen Before";
        diagnosisWrap.appendChild(seenBadge);
      }
      diagnosisCell.appendChild(diagnosisWrap);

      const confidenceCell = document.createElement("td");
      confidenceCell.textContent = formatPercent(Number(item.confidence_pct || 0), 0);

      row.appendChild(statusCell);
      row.appendChild(merchantCell);
      row.appendChild(amountCell);
      row.appendChild(diagnosisCell);
      row.appendChild(confidenceCell);
      queueBodyEl.appendChild(row);
    });
  }

  async function fetchQueue() {
    const response = await fetch(`${apiBase()}/workbench`, { method: "GET" });
    if (!response.ok) {
      throw new Error(`Failed to load queue (${response.status})`);
    }
    const data = await response.json();
    return Array.isArray(data) ? data : [];
  }

  async function fetchSessions() {
    const response = await fetch(`${apiBase()}/workbench/sessions`, { method: "GET" });
    if (!response.ok) {
      throw new Error(`Failed to load sessions (${response.status})`);
    }
    const data = await response.json();
    return Array.isArray(data) ? data : [];
  }

  async function clearSession(sessionId) {
    const response = await fetch(`${apiBase()}/workbench/session/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error(`Failed to clear session (${response.status})`);
    }
    return response.json();
  }

  async function runSessionIntake(transactionsCsvFile, receiptFiles) {
    const formData = new FormData();
    formData.append("transactions_csv", transactionsCsvFile);
    receiptFiles.forEach(function (file) {
      formData.append("receipts", file);
    });

    const response = await fetch(`${apiBase()}/workbench/session-intake`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      let detail = `Session intake failed (${response.status})`;
      try {
        const body = await response.json();
        if (body && body.detail) {
          detail = String(body.detail);
        }
      } catch (_unused) {
        // Keep default detail.
      }
      throw new Error(detail);
    }
    return response.json();
  }

  async function fetchDetail(itemId) {
    const response = await fetch(`${apiBase()}/workbench/${encodeURIComponent(itemId)}`, { method: "GET" });
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Queue item not found: ${itemId}`);
      }
      throw new Error(`Failed to load detail (${response.status})`);
    }
    return response.json();
  }

  function extractCandidate(payload) {
    const uiCandidate = payload && payload.ui ? payload.ui.top_candidate : null;
    if (uiCandidate) {
      return {
        merchant: uiCandidate.merchant || "--",
        amount: Number(uiCandidate.amount),
        date: uiCandidate.date || "--",
        transactionId: uiCandidate.transaction_id || "--",
        vendorScore: Number(uiCandidate.vendor_similarity_score),
        amountPct: Number(uiCandidate.amount_delta_pct),
        dateDays: uiCandidate.date_delta_days,
      };
    }
    const topMatch = payload ? payload.top_match : null;
    const scores = topMatch && topMatch.scores ? topMatch.scores : {};
    return {
      merchant: topMatch ? topMatch.merchant || "--" : "--",
      amount: topMatch ? Number(topMatch.amount) : Number.NaN,
      date: topMatch ? topMatch.date || "--" : "--",
      transactionId: topMatch ? topMatch.transaction_id || "--" : "--",
      vendorScore: Number(scores.vendor_score),
      amountPct: Number(scores.amount_pct_diff),
      dateDays: scores.date_diff,
    };
  }

  function renderEvidence(evidence) {
    detailEvidenceEl.innerHTML = "";
    if (!Array.isArray(evidence) || !evidence.length) {
      const li = document.createElement("li");
      li.textContent = "No evidence recorded.";
      detailEvidenceEl.appendChild(li);
      return;
    }
    evidence.forEach(function (item) {
      const li = document.createElement("li");
      li.textContent = item;
      detailEvidenceEl.appendChild(li);
    });
  }

  function renderDetail(payload) {
    state.currentPayload = payload;
    detailEmptyEl.hidden = true;
    detailViewEl.hidden = false;
    const currentItem = state.queueItems.find(function (item) {
      return item.id === state.currentId;
    }) || null;

    const badgeState = detailBadgeState(payload);
    applyDetailBadge(badgeState);

    detailConfidenceEl.textContent = formatPercent(Number(payload.confidence || 0), 1);
    detailDiagnosisEl.textContent = payload && payload.diagnosis
      ? payload.diagnosis.label_summary || "Unclassified"
      : "Unclassified";

    renderEvidence(payload.evidence || []);
    const candidate = extractCandidate(payload);

    detailMerchantEl.textContent = candidate.merchant;
    detailAmountEl.textContent = formatCurrency(candidate.amount);
    detailDateEl.textContent = candidate.date;
    detailTransactionIdEl.textContent = candidate.transactionId;
    detailVendorScoreEl.textContent = Number.isFinite(candidate.vendorScore) ? candidate.vendorScore.toFixed(1) : "--";
    detailAmountPctEl.textContent = Number.isFinite(candidate.amountPct) ? `${candidate.amountPct.toFixed(1)}%` : "--";
    detailDateDaysEl.textContent = typeof candidate.dateDays === "number" ? String(candidate.dateDays) : "--";

    detailAuditNoteEl.value = WorkbenchLogic.buildAuditMemo(payload);
    updateResolutionControls();
    updateDecisionNoteInput();
    renderMemoryHints(payload, currentItem);
  }

  function hideDetail() {
    state.currentId = null;
    state.currentPayload = null;
    detailViewEl.hidden = true;
    detailEmptyEl.hidden = false;
    detailAuditNoteEl.value = "";
    if (detailDecisionNoteEl) {
      detailDecisionNoteEl.value = "";
    }
    if (detailPatternHintEl) {
      detailPatternHintEl.textContent = "";
      detailPatternHintEl.hidden = true;
    }
    if (detailKnownAliasBadgeEl) {
      detailKnownAliasBadgeEl.hidden = true;
    }
    if (detailAliasMemorySectionEl) {
      detailAliasMemorySectionEl.hidden = true;
    }
    if (detailAliasMemoryTextEl) {
      detailAliasMemoryTextEl.textContent = "";
    }
    updateResolutionControls();
  }

  function queueOrderIds() {
    return state.queueItems.map(function (item) {
      return item.id;
    });
  }

  function updateNavButtons() {
    if (!state.currentId) {
      prevItemBtn.disabled = true;
      nextItemBtn.disabled = true;
      return;
    }
    const ids = queueOrderIds();
    prevItemBtn.disabled = !WorkbenchLogic.getPrevQueueId(ids, state.currentId);
    nextItemBtn.disabled = !WorkbenchLogic.getNextQueueId(ids, state.currentId);
  }

  function ensureSelectedVisible() {
    const visibleIds = state.visibleItems.map(function (item) {
      return item.id;
    });
    if (!visibleIds.length) {
      state.selectedId = null;
      return;
    }
    if (!state.selectedId || visibleIds.indexOf(state.selectedId) === -1) {
      state.selectedId = visibleIds[0];
    }
  }

  function applyControlsAndRenderQueue() {
    state.visibleItems = WorkbenchLogic.filterAndSortQueue(
      state.queueItems,
      state.controls,
      state.resolutionState
    );
    ensureSelectedVisible();
    setQueueRows(state.visibleItems);
  }

  async function openDetail(itemId, pushRoute) {
    try {
      const payload = await fetchDetail(itemId);
      state.currentId = itemId;
      state.selectedId = itemId;
      const selectedItem = state.queueItems.find(function (item) {
        return item.id === itemId;
      });
      if (selectedItem && selectedItem.session_id) {
        state.currentSessionId = selectedItem.session_id;
        updateSessionLabel();
      }
      renderDetail(payload);
      applyControlsAndRenderQueue();
      updateNavButtons();
      if (pushRoute) {
        history.pushState({ id: itemId }, "", detailUrl(itemId));
      }
      scheduleWorkspaceSave("select_detail");
    } catch (error) {
      setQueueStatus(error.message || "Failed to load detail.", true);
    }
  }

  function goToList(pushRoute) {
    hideDetail();
    applyControlsAndRenderQueue();
    updateNavButtons();
    if (pushRoute) {
      history.pushState({}, "", listUrl());
    }
    scheduleWorkspaceSave("back_to_list");
  }

  function openPrevious() {
    if (!state.currentId) {
      return;
    }
    const prevId = WorkbenchLogic.getPrevQueueId(queueOrderIds(), state.currentId);
    if (prevId) {
      openDetail(prevId, true);
    }
  }

  function openNext() {
    if (!state.currentId) {
      return;
    }
    const nextId = WorkbenchLogic.getNextQueueId(queueOrderIds(), state.currentId);
    if (nextId) {
      openDetail(nextId, true);
    }
  }

  async function copyMemo(goNext) {
    const memo = detailAuditNoteEl.value || "";
    if (!memo) {
      return;
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(memo);
      } else {
        detailAuditNoteEl.focus();
        detailAuditNoteEl.select();
        document.execCommand("copy");
      }
      if (goNext) {
        const nextId = WorkbenchLogic.getNextQueueId(queueOrderIds(), state.currentId);
        if (nextId) {
          await openDetail(nextId, true);
          showToast("Copied. Moved to next.");
        } else {
          showToast("Copied. No next item.");
        }
      } else {
        showToast("Copied.");
      }
    } catch (_unused) {
      setQueueStatus("Copy failed. Select and copy manually.", true);
    }
  }

  function downloadPayloadJson() {
    if (!state.currentPayload) {
      return;
    }
    const blob = new Blob([JSON.stringify(state.currentPayload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${state.currentId || "workbench_item"}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  function setActiveFilterPill() {
    const pills = queueFilterPillsEl.querySelectorAll(".filter-pill");
    pills.forEach(function (pill) {
      const value = String(pill.getAttribute("data-filter") || "");
      pill.classList.toggle("active", value === state.controls.matchFilter);
    });
  }

  function openShortcutModal() {
    state.modalOpen = true;
    shortcutModalEl.hidden = false;
  }

  function closeShortcutModal() {
    state.modalOpen = false;
    shortcutModalEl.hidden = true;
  }

  function handleKeyboard(event) {
    const searchFocused = document.activeElement === queueSearchEl;
    const action = WorkbenchLogic.getShortcutAction({
      mode: state.currentId ? "detail" : "list",
      key: event.key,
      shiftKey: event.shiftKey,
      isInputFocused: WorkbenchLogic.isTypingTarget(event.target),
      searchFocused: searchFocused,
      modalOpen: state.modalOpen,
    });
    if (!action) {
      return;
    }
    event.preventDefault();

    if (action === "close_shortcuts_modal") {
      closeShortcutModal();
      return;
    }

    if (action === "focus_search") {
      queueSearchEl.focus();
      queueSearchEl.select();
      return;
    }
    if (action === "clear_search_focus") {
      if (document.activeElement === queueSearchEl) {
        queueSearchEl.blur();
      }
      return;
    }

    if (action === "move_down") {
      if (!state.visibleItems.length) {
        return;
      }
      const ids = state.visibleItems.map(function (item) { return item.id; });
      const idx = ids.indexOf(state.selectedId);
      const nextIdx = idx < 0 ? 0 : Math.min(ids.length - 1, idx + 1);
      state.selectedId = ids[nextIdx];
      applyControlsAndRenderQueue();
      return;
    }

    if (action === "move_up") {
      if (!state.visibleItems.length) {
        return;
      }
      const ids = state.visibleItems.map(function (item) { return item.id; });
      const idx = ids.indexOf(state.selectedId);
      const prevIdx = idx < 0 ? 0 : Math.max(0, idx - 1);
      state.selectedId = ids[prevIdx];
      applyControlsAndRenderQueue();
      return;
    }

    if (action === "open_selected") {
      if (state.selectedId) {
        openDetail(state.selectedId, true);
      }
      return;
    }

    if (action === "next_item") {
      openNext();
      return;
    }
    if (action === "prev_item") {
      openPrevious();
      return;
    }
    if (action === "copy_memo") {
      copyMemo(false);
      return;
    }
    if (action === "copy_and_next") {
      copyMemo(true);
      return;
    }
    if (action === "back_to_list") {
      goToList(true);
    }
  }

  async function refreshQueue() {
    try {
      setQueueStatus("Loading queue...", false);
      const [queueItems, sessions] = await Promise.all([fetchQueue(), fetchSessions()]);
      state.queueItems = queueItems;
      applyControlsAndRenderQueue();
      setQueueStatus(`${state.queueItems.length} exception(s) in queue.`, false);
      if (!state.currentSessionId) {
        state.currentSessionId = sessions.length ? sessions[0].session_id : null;
      } else {
        const exists = sessions.some(function (session) {
          return session.session_id === state.currentSessionId;
        });
        if (!exists) {
          state.currentSessionId = sessions.length ? sessions[0].session_id : null;
        }
      }
      updateSessionLabel();
      updateNavButtons();
    } catch (error) {
      setQueueStatus(error.message || "Failed to load queue.", true);
      state.queueItems = [];
      applyControlsAndRenderQueue();
      state.currentSessionId = null;
      updateSessionLabel();
    }
  }

  async function applyRoute() {
    const routeId = parseRouteId();
    if (!routeId) {
      goToList(false);
      return;
    }
    const exists = state.queueItems.some(function (item) {
      return item.id === routeId;
    });
    if (!exists) {
      setQueueStatus(`Queue item not found: ${routeId}`, true);
      goToList(true);
      return;
    }
    await openDetail(routeId, false);
  }

  async function handleSessionIntakeSubmit(event) {
    event.preventDefault();
    const csvFile = intakeTransactionsCsvEl.files && intakeTransactionsCsvEl.files[0];
    if (!csvFile) {
      setIntakeStatus("Select a transactions CSV file.", true);
      return;
    }

    const receiptFiles = intakeReceiptsEl.files ? Array.from(intakeReceiptsEl.files) : [];
    intakeSubmitBtn.disabled = true;
    setIntakeStatus("Running intake...", false);

    try {
      const result = await runSessionIntake(csvFile, receiptFiles);
      state.currentSessionId = result.session_id || null;
      updateSessionLabel();
      setIntakeStatus(
        `Processed ${result.total_processed} row(s), added ${result.exceptions_added} exception(s).`,
        false
      );
      showToast(`${result.exceptions_added} exceptions added to workbench`);
      await refreshQueue();
      await applyRoute();
      scheduleWorkspaceSave("session_intake");
    } catch (error) {
      setIntakeStatus(error.message || "Session intake failed.", true);
    } finally {
      intakeSubmitBtn.disabled = false;
    }
  }

  async function handleClearCurrentSession() {
    if (!state.currentSessionId) {
      return;
    }
    try {
      const result = await clearSession(state.currentSessionId);
      showToast(`Cleared ${result.removed} item(s) from ${state.currentSessionId}`);
      state.currentSessionId = null;
      updateSessionLabel();
      await refreshQueue();
      await applyRoute();
      scheduleWorkspaceSave("clear_session");
    } catch (error) {
      setQueueStatus(error.message || "Failed to clear session.", true);
    }
  }

  function bindControlEvents() {
    queueSearchEl.addEventListener("input", function () {
      state.controls.query = queueSearchEl.value || "";
      applyControlsAndRenderQueue();
    });

    queueFilterPillsEl.addEventListener("click", function (event) {
      const target = event.target;
      if (!(target instanceof HTMLElement) || !target.classList.contains("filter-pill")) {
        return;
      }
      state.controls.matchFilter = String(target.getAttribute("data-filter") || "all");
      setActiveFilterPill();
      applyControlsAndRenderQueue();
    });

    queueSortEl.addEventListener("change", function () {
      state.controls.sortKey = queueSortEl.value || "confidence_desc";
      applyControlsAndRenderQueue();
    });

    showOnlyUnresolvedEl.addEventListener("change", function () {
      state.controls.showOnlyUnresolved = !!showOnlyUnresolvedEl.checked;
      applyControlsAndRenderQueue();
      scheduleWorkspaceSave("toggle_unresolved");
    });
  }

  function bindActions() {
    sessionIntakeFormEl.addEventListener("submit", handleSessionIntakeSubmit);
    clearCurrentSessionBtn.addEventListener("click", handleClearCurrentSession);

    backToWorkbenchBtn.addEventListener("click", function () {
      goToList(true);
    });
    prevItemBtn.addEventListener("click", openPrevious);
    nextItemBtn.addEventListener("click", openNext);
    copySummaryBtn.addEventListener("click", function () {
      copyMemo(false);
    });
    copyNextBtn.addEventListener("click", function () {
      copyMemo(true);
    });
    downloadJsonBtn.addEventListener("click", downloadPayloadJson);

    if (detailResolutionOptionsEl) {
      detailResolutionOptionsEl.addEventListener("change", function (event) {
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) {
          return;
        }
        if (!state.currentId) {
          return;
        }
        const previousResolution = getResolution(state.currentId);
        const nextResolution = target.value;
        setResolution(state.currentId, nextResolution);
        updateMemoryOnAcceptedTransition(state.currentId, previousResolution, nextResolution);
        updateResolutionControls();
        renderMemoryHints(state.currentPayload, state.queueItems.find(function (item) {
          return item.id === state.currentId;
        }) || null);
        applyControlsAndRenderQueue();
      });
    }

    if (detailResolutionClearBtn) {
      detailResolutionClearBtn.addEventListener("click", function () {
        if (!state.currentId) {
          return;
        }
        setResolution(state.currentId, "unreviewed");
        updateResolutionControls();
        applyControlsAndRenderQueue();
      });
    }

    if (detailDecisionNoteEl) {
      detailDecisionNoteEl.addEventListener("input", function () {
        if (!state.currentId) {
          return;
        }
        setDecisionNote(state.currentId, detailDecisionNoteEl.value || "");
      });
    }

    shortcutHelpLinkEl.addEventListener("click", function (event) {
      event.preventDefault();
      openShortcutModal();
    });
    shortcutModalCloseEl.addEventListener("click", function () {
      closeShortcutModal();
    });
    shortcutModalEl.addEventListener("click", function (event) {
      if (event.target === shortcutModalEl) {
        closeShortcutModal();
      }
    });

    window.addEventListener("popstate", function () {
      applyRoute();
    });
    document.addEventListener("keydown", handleKeyboard);
  }

  function initLinks() {
    openDiagnoseLinkEl.href = `../index.html?api=${encodeURIComponent(apiBase())}`;
  }

  function initControls() {
    state.controls.query = state.controls.query || "";
    state.controls.matchFilter = state.controls.matchFilter || "all";
    state.controls.sortKey = state.controls.sortKey || "confidence_desc";
    state.controls.showOnlyUnresolved = !!state.controls.showOnlyUnresolved;

    queueSearchEl.value = state.controls.query;
    queueSortEl.value = state.controls.sortKey;
    showOnlyUnresolvedEl.checked = state.controls.showOnlyUnresolved;
    setActiveFilterPill();
    setIntakeStatus("", false);
    setWorkspaceSaveStatus("Saved", false);
    updateSessionLabel();
    updateResolutionControls();
  }

  async function init() {
    initLinks();
    state.workspaceSaver = WorkspaceSync && WorkspaceSync.createDebouncedAction
      ? WorkspaceSync.createDebouncedAction(persistWorkspaceNow, SAVE_DEBOUNCE_MS)
      : { schedule: persistWorkspaceNow };

    setWorkspaceSaveStatus("Saving...", false);
    try {
      const snapshot = await fetchWorkspaceLoad();
      applyWorkspaceSnapshot(snapshot);
      state.workspaceLoaded = true;
      setWorkspaceSaveStatus("Saved", false);
    } catch (error) {
      setQueueStatus(error.message || "Failed to load workspace.", true);
      state.workspaceLoaded = true;
      setWorkspaceSaveStatus("Save failed", true);
    }

    initControls();
    bindControlEvents();
    bindActions();

    await refreshQueue();
    await applyRoute();
  }

  init();
})();

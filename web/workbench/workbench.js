(function () {
  const DEFAULT_API_BASE = "http://127.0.0.1:8000";
  const API_BASE_STORAGE_KEY = "diagnosticApiBase";
  const Decision = window.DecisionState;
  const Memory = window.MemoryState;
  const WorkspaceSync = window.WorkspaceSync;
  const WORKSPACE_ID = "default";
  const SAVE_DEBOUNCE_MS = 800;
  const PANEL_FADE_OUT_MS = 120;
  const PANEL_FADE_IN_MS = 120;
  const THINKING_CUE_MS = 800;
  const AUDIT_COPY_FLASH_MS = 150;
  const NEW_INTELLIGENCE_MS = 1200;

  const queueStatusEl = document.getElementById("queue-status");
  const queueAlertEl = document.getElementById("queue-alert");
  const queueBodyEl = document.getElementById("queue-body");
  const queueSearchEl = document.getElementById("queue-search");
  const queueFilterPillsEl = document.getElementById("queue-filter-pills");
  const queueSortEl = document.getElementById("queue-sort");
  const showOnlyUnresolvedEl = document.getElementById("show-only-unresolved");
  const sessionIntakeFormEl = document.getElementById("session-intake-form");
  const intakeTransactionsCsvEl = document.getElementById("intake-transactions-csv");
  const intakeReceiptsEl = document.getElementById("intake-receipts");
  const intakeSubmitBtn = document.getElementById("session-intake-submit");
  const intakeStatusEl = document.getElementById("session-intake-status");
  const newSessionDrawerEl = document.getElementById("new-session-drawer");
  const singleDiagnosisToggleEl = document.getElementById("single-diagnosis-toggle");
  const singleDiagnosisPanelEl = document.getElementById("single-diagnosis-panel");
  const singleDiagnosisFormEl = document.getElementById("single-diagnosis-form");
  const singleReceiptFileEl = document.getElementById("single-receipt-file");
  const singleCsvFileEl = document.getElementById("single-csv-file");
  const singleDiagnosisSubmitEl = document.getElementById("single-diagnosis-submit");
  const singleDiagnosisStatusEl = document.getElementById("single-diagnosis-status");
  const singleAdvancedToggleEl = document.getElementById("single-advanced-toggle");
  const singleAdvancedFieldsEl = document.getElementById("single-advanced-fields");
  const singleManualVendorEl = document.getElementById("single-manual-vendor");
  const singleManualDateEl = document.getElementById("single-manual-date");
  const singleManualTotalEl = document.getElementById("single-manual-total");
  const currentSessionLabelEl = document.getElementById("current-session-label");
  const clearCurrentSessionBtn = document.getElementById("clear-current-session");
  const workspaceSaveStatusEl = document.getElementById("workspace-save-status");
  const metricExceptionsTodayEl = document.getElementById("metric-exceptions-today");
  const metricNeedsReviewEl = document.getElementById("metric-needs-review");
  const metricResolvedEl = document.getElementById("metric-resolved");
  const dailyStripSummaryEl = document.getElementById("daily-strip-summary");
  const dailyStripUpdatedEl = document.getElementById("daily-strip-updated");

  const detailEmptyEl = document.getElementById("detail-empty");
  const detailPanelEl = document.querySelector(".detail-panel");
  const detailViewEl = document.getElementById("detail-view");
  const detailSummarySectionEl = document.getElementById("detail-summary-section");
  const detailMatchStateEl = document.getElementById("detail-match-state");
  const detailConfidenceEl = document.getElementById("detail-confidence");
  const detailDiagnosisEl = document.getElementById("detail-diagnosis");
  const detailSummaryEl = document.getElementById("detail-summary");
  const detailNextChecksEl = document.getElementById("detail-next-checks");
  const detailKnownAliasBadgeEl = document.getElementById("detail-known-alias-badge");
  const detailPatternHintEl = document.getElementById("detail-pattern-hint");
  const detailEvidenceEl = document.getElementById("detail-evidence");
  const detailResolutionStateEl = document.getElementById("detail-resolution-state");
  const detailResolutionOptionsEl = document.getElementById("detail-resolution-options");
  const detailResolutionClearBtn = document.getElementById("detail-resolution-clear");
  const detailResolveIgnoreBtn = document.getElementById("detail-resolve-ignore");
  const detailResolveFlagBtn = document.getElementById("detail-resolve-flag");
  const detailResolveAcceptBtn = document.getElementById("detail-resolve-accept");
  const detailAliasMemorySectionEl = document.getElementById("detail-alias-memory-section");
  const detailAliasMemoryTextEl = document.getElementById("detail-alias-memory-text");
  const detailBridgeRowMerchantEl = document.getElementById("detail-bridge-row-merchant");
  const detailBridgeRowMerchantBankEl = document.getElementById("detail-bridge-row-merchant-bank");
  const detailBridgeRowAmountEl = document.getElementById("detail-bridge-row-amount");
  const detailBridgeRowAmountBankEl = document.getElementById("detail-bridge-row-amount-bank");
  const detailBridgeRowDateEl = document.getElementById("detail-bridge-row-date");
  const detailBridgeRowDateBankEl = document.getElementById("detail-bridge-row-date-bank");
  const detailBridgeReceiptMerchantEl = document.getElementById("detail-bridge-receipt-merchant");
  const detailBridgeReceiptAmountEl = document.getElementById("detail-bridge-receipt-amount");
  const detailBridgeReceiptDateEl = document.getElementById("detail-bridge-receipt-date");
  const detailBridgeBankMerchantEl = document.getElementById("detail-bridge-bank-merchant");
  const detailBridgeBankAmountEl = document.getElementById("detail-bridge-bank-amount");
  const detailBridgeBankDateEl = document.getElementById("detail-bridge-bank-date");

  const detailMerchantEl = document.getElementById("detail-merchant");
  const detailAmountEl = document.getElementById("detail-amount");
  const detailDateEl = document.getElementById("detail-date");
  const detailTransactionIdEl = document.getElementById("detail-transaction-id");
  const detailDescriptionEl = document.getElementById("detail-description");
  const detailVendorScoreEl = document.getElementById("detail-vendor-score");
  const detailAmountPctEl = document.getElementById("detail-amount-pct");
  const detailDateDaysEl = document.getElementById("detail-date-days");
  const detailOtherCandidatesEl = document.getElementById("detail-other-candidates");
  const detailOtherCandidateListEl = document.getElementById("detail-other-candidate-list");
  const detailGroundingToggleEl = document.getElementById("detail-grounding-toggle");
  const detailGroundingFieldsEl = document.getElementById("detail-grounding-fields");
  const detailGroundingMessageEl = document.getElementById("detail-grounding-message");
  const detailReceiptViewerContainerEl = document.getElementById("detail-receipt-viewer-container");
  const detailViewerStageEl = document.getElementById("detail-viewer-stage");
  const detailReceiptPreviewImageEl = document.getElementById("detail-receipt-preview-image");
  const detailOverlayLayerEl = document.getElementById("detail-overlay-layer");
  const detailAuditSectionEl = document.getElementById("detail-audit-section");
  const detailAuditNoteEl = document.getElementById("detail-audit-note");
  const detailDecisionNoteEl = document.getElementById("detail-decision-note");

  const backToWorkbenchBtn = document.getElementById("back-to-workbench");
  const prevItemBtn = document.getElementById("prev-item");
  const nextItemBtn = document.getElementById("next-item");
  const copySummaryBtn = document.getElementById("detail-copy-summary");
  const copySummaryBottomBtn = document.getElementById("detail-audit-copy-summary");
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
    currentViewMode: "queue",
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
    singleModeOpen: false,
    saveStatus: "Saved",
    workspaceLoaded: false,
    workspaceSaver: null,
    detailTransitionId: 0,
    thinkingCueTimer: null,
    auditCopyTimer: null,
    resolutionTransitionId: null,
    resolutionTransitionTimer: null,
    recentSessionId: null,
    recentSessionUntil: 0,
    recentSessionTimer: null,
    lastQueueUpdatedAt: null,
    lastSessionCount: 0,
    detailGrounding: {
      fieldMap: null,
      activeField: null,
      showGrounding: true,
    },
  };

  function delay(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

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

  function toDate(value) {
    if (!value) {
      return null;
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return null;
    }
    return parsed;
  }

  function isSameLocalDay(a, b) {
    return (
      a.getFullYear() === b.getFullYear()
      && a.getMonth() === b.getMonth()
      && a.getDate() === b.getDate()
    );
  }

  function countUniqueSessions(items) {
    const set = new Set();
    (items || []).forEach(function (item) {
      const sessionId = item && item.session_id ? String(item.session_id).trim() : "";
      if (sessionId) {
        set.add(sessionId);
      }
    });
    return set.size;
  }

  function countExceptionsToday(items) {
    const now = new Date();
    let datedItems = 0;
    let count = 0;
    (items || []).forEach(function (item) {
      const createdAt = toDate(item && item.created_at);
      if (!createdAt) {
        return;
      }
      datedItems += 1;
      if (isSameLocalDay(createdAt, now)) {
        count += 1;
      }
    });
    return datedItems > 0 ? count : (items || []).length;
  }

  function formatTimeShort(value) {
    const date = value instanceof Date ? value : toDate(value);
    if (!date) {
      return "--";
    }
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
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

  function queueConfidenceTone(confidencePct) {
    const numeric = Number(confidencePct);
    if (!Number.isFinite(numeric)) {
      return "confidence-low";
    }
    if (numeric >= 80) {
      return "confidence-high";
    }
    if (numeric >= 50) {
      return "confidence-possible";
    }
    return "confidence-low";
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

  function setQueueAlert(message) {
    if (!queueAlertEl) {
      return;
    }
    const text = String(message || "").trim();
    if (!text) {
      queueAlertEl.textContent = "";
      queueAlertEl.hidden = true;
      return;
    }
    queueAlertEl.textContent = text;
    queueAlertEl.hidden = false;
  }

  function compactQueueErrorMessage(message) {
    const text = String(message || "").toLowerCase();
    if (text.includes("failed to fetch") || text.includes("networkerror") || text.includes("fetch")) {
      return "Backend not reachable. Start the server and retry.";
    }
    if (text.includes("workspace")) {
      return "Workspace state could not be loaded. You can continue reviewing exceptions.";
    }
    if (text.includes("not found")) {
      return "Selected exception is no longer available in the queue.";
    }
    if (text.includes("save")) {
      return "Workspace save failed. Retry after backend is reachable.";
    }
    return "Backend not reachable. Start the server and retry.";
  }

  function setQueueStatus(message, isError) {
    if (queueStatusEl) {
      if (!isError && message) {
        queueStatusEl.textContent = message;
      }
      if (isError) {
        queueStatusEl.textContent = "Queue unavailable.";
      }
    }
    setQueueAlert(isError ? compactQueueErrorMessage(message) : "");
  }

  function setIntakeStatus(message, isError) {
    if (!intakeStatusEl) {
      return;
    }
    intakeStatusEl.textContent = message || "";
    intakeStatusEl.classList.toggle("error", !!isError);
  }

  function setSingleDiagnosisStatus(message, isError) {
    if (!singleDiagnosisStatusEl) {
      return;
    }
    singleDiagnosisStatusEl.textContent = message || "";
    singleDiagnosisStatusEl.classList.toggle("error", !!isError);
  }

  function updateSessionLabel() {
    const label = state.currentSessionId ? `Session: ${state.currentSessionId}` : "Session: --";
    currentSessionLabelEl.textContent = label;
    clearCurrentSessionBtn.disabled = !state.currentSessionId;
  }

  function updateMorningSurface() {
    const totalItems = state.queueItems.length;
    const exceptionsToday = countExceptionsToday(state.queueItems);
    let resolved = 0;
    state.queueItems.forEach(function (item) {
      if (getResolution(item.id) !== "unreviewed") {
        resolved += 1;
      }
    });
    const needsReview = Math.max(0, totalItems - resolved);
    const sessionCount = state.lastSessionCount > 0
      ? state.lastSessionCount
      : countUniqueSessions(state.queueItems);

    if (metricExceptionsTodayEl) {
      metricExceptionsTodayEl.textContent = String(totalItems);
    }
    if (metricNeedsReviewEl) {
      metricNeedsReviewEl.textContent = String(needsReview);
    }
    if (metricResolvedEl) {
      metricResolvedEl.textContent = String(resolved);
    }

    if (dailyStripSummaryEl) {
      if (totalItems === 0) {
        dailyStripSummaryEl.textContent = "All clear - no mismatches detected.";
        dailyStripSummaryEl.classList.add("is-clear");
      } else {
        const exWord = exceptionsToday === 1 ? "Exception" : "Exceptions";
        const sessionWord = sessionCount === 1 ? "session" : "sessions";
        dailyStripSummaryEl.textContent =
          `${exceptionsToday} ${exWord} detected across ${sessionCount} ${sessionWord}`;
        dailyStripSummaryEl.classList.remove("is-clear");
      }
    }

    if (dailyStripUpdatedEl) {
      const stamp = state.lastQueueUpdatedAt ? formatTimeShort(state.lastQueueUpdatedAt) : "--";
      dailyStripUpdatedEl.textContent = `Last updated: ${stamp}`;
    }
  }

  function syncDetailEmptyState() {
    if (!detailEmptyEl || !detailViewEl || !detailViewEl.hidden) {
      return;
    }
    detailEmptyEl.textContent = "Select a case to begin investigation.";
  }

  function setSingleModeOpen(open) {
    state.singleModeOpen = !!open;
    if (singleDiagnosisPanelEl) {
      singleDiagnosisPanelEl.hidden = !state.singleModeOpen;
    }
    if (singleDiagnosisToggleEl) {
      singleDiagnosisToggleEl.setAttribute("aria-expanded", String(state.singleModeOpen));
      singleDiagnosisToggleEl.textContent = state.singleModeOpen
        ? "Hide single receipt diagnosis"
        : "Single receipt diagnosis";
    }
  }

  function setSingleAdvancedVisible(visible) {
    if (!singleAdvancedFieldsEl || !singleAdvancedToggleEl) {
      return;
    }
    singleAdvancedFieldsEl.hidden = !visible;
    singleAdvancedToggleEl.setAttribute("aria-expanded", String(visible));
    singleAdvancedToggleEl.textContent = visible ? "Hide Advanced" : "Advanced";
  }

  function showThinkingCue() {
    if (!detailPanelEl) {
      return;
    }
    detailPanelEl.classList.add("is-thinking");
    if (state.thinkingCueTimer) {
      clearTimeout(state.thinkingCueTimer);
    }
    state.thinkingCueTimer = setTimeout(function () {
      detailPanelEl.classList.remove("is-thinking");
      state.thinkingCueTimer = null;
    }, THINKING_CUE_MS);
  }

  function flashAuditCopyMoment() {
    if (!detailAuditSectionEl) {
      return;
    }
    detailAuditSectionEl.classList.add("audit-copied-flash");
    if (state.auditCopyTimer) {
      clearTimeout(state.auditCopyTimer);
    }
    state.auditCopyTimer = setTimeout(function () {
      detailAuditSectionEl.classList.remove("audit-copied-flash");
      state.auditCopyTimer = null;
    }, AUDIT_COPY_FLASH_MS);
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
    state.lastSessionCount = countUniqueSessions(state.queueItems);
    state.lastQueueUpdatedAt = new Date();
    updateMorningSurface();
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
    state.resolutionTransitionId = itemId || null;
    if (state.resolutionTransitionTimer) {
      clearTimeout(state.resolutionTransitionTimer);
    }
    state.resolutionTransitionTimer = setTimeout(function () {
      state.resolutionTransitionId = null;
      state.resolutionTransitionTimer = null;
      applyControlsAndRenderQueue();
    }, 240);
    updateMorningSurface();
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

  function applyResolutionSelection(nextResolution) {
    if (!state.currentId) {
      return;
    }
    const previousResolution = getResolution(state.currentId);
    setResolution(state.currentId, nextResolution);
    updateMemoryOnAcceptedTransition(state.currentId, previousResolution, nextResolution);
    updateResolutionControls();
    renderMemoryHints(state.currentPayload, state.queueItems.find(function (item) {
      return item.id === state.currentId;
    }) || null);
    applyControlsAndRenderQueue();
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

    if (detailResolveIgnoreBtn) {
      detailResolveIgnoreBtn.classList.toggle("active", resolution === "ignored");
    }
    if (detailResolveFlagBtn) {
      detailResolveFlagBtn.classList.toggle("active", resolution === "follow_up");
    }
    if (detailResolveAcceptBtn) {
      detailResolveAcceptBtn.classList.toggle("active", resolution === "accepted");
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
    if (detailDiagnosisEl) {
      detailDiagnosisEl.classList.toggle("seen-before-dotted", patternCount > 0);
      if (patternCount > 0) {
        detailDiagnosisEl.title = "Based on prior review";
      } else {
        detailDiagnosisEl.removeAttribute("title");
      }
    }
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

      if (
        state.recentSessionId
        && item.session_id === state.recentSessionId
        && Date.now() < Number(state.recentSessionUntil || 0)
      ) {
        row.classList.add("new-intelligence");
      }

      const resolution = getResolution(item.id);
      if (resolution === "accepted") {
        row.classList.add("resolution-accepted");
      } else if (resolution === "follow_up") {
        row.classList.add("resolution-follow-up");
      } else if (resolution === "ignored") {
        row.classList.add("resolution-ignored");
      }
      if (state.resolutionTransitionId && state.resolutionTransitionId === item.id) {
        row.classList.add("resolution-transition");
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
        const memoryGlyph = document.createElement("span");
        memoryGlyph.className = "memory-glyph";
        memoryGlyph.textContent = "M";
        memoryGlyph.title = `Known alias from prior review: ${alias}`;
        memoryGlyph.setAttribute("aria-label", "Known alias from prior review");
        merchantLine.appendChild(memoryGlyph);
      }

      const amountCell = document.createElement("td");
      amountCell.textContent = formatCurrency(item.amount);

      const diagnosisCell = document.createElement("td");
      const diagnosisWrap = document.createElement("div");
      diagnosisWrap.className = "queue-diagnosis-wrap";
      const diagnosisText = document.createElement("span");
      diagnosisText.className = "queue-diagnosis-text";
      diagnosisText.textContent = item.diagnosis || "--";
      if (getPatternCountForDiagnosis(item.diagnosis || "") >= 1) {
        diagnosisText.classList.add("seen-before-dotted");
        diagnosisText.title = "Based on prior review";
      }
      diagnosisWrap.appendChild(diagnosisText);
      diagnosisCell.appendChild(diagnosisWrap);

      const confidenceCell = document.createElement("td");
      const confidencePill = document.createElement("span");
      confidencePill.className = `queue-confidence-pill ${queueConfidenceTone(item.confidence_pct)}`;
      confidencePill.textContent = formatPercent(Number(item.confidence_pct || 0), 0);
      confidenceCell.appendChild(confidencePill);

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

  async function addWorkbenchItem(payload) {
    const response = await fetch(`${apiBase()}/workbench/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      let detail = `Failed to add item to workbench (${response.status})`;
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

  async function runSingleDiagnosis(event) {
    event.preventDefault();
    const receiptFile = singleReceiptFileEl && singleReceiptFileEl.files ? singleReceiptFileEl.files[0] : null;
    const csvFile = singleCsvFileEl && singleCsvFileEl.files ? singleCsvFileEl.files[0] : null;
    if (!receiptFile || !csvFile) {
      setSingleDiagnosisStatus("Select both a receipt file and a transactions CSV file.", true);
      return;
    }

    singleDiagnosisSubmitEl.disabled = true;
    setSingleDiagnosisStatus("Running single diagnosis...", false);
    setQueueAlert("");
    showThinkingCue();

    const formData = new FormData();
    formData.append("receipt", receiptFile);
    formData.append("csv", csvFile);
    if (singleManualVendorEl && String(singleManualVendorEl.value || "").trim()) {
      formData.append("manual_vendor", String(singleManualVendorEl.value).trim());
    }
    if (singleManualDateEl && String(singleManualDateEl.value || "").trim()) {
      formData.append("manual_date", String(singleManualDateEl.value).trim());
    }
    if (singleManualTotalEl && String(singleManualTotalEl.value || "").trim()) {
      formData.append("manual_total", String(singleManualTotalEl.value).trim());
    }

    try {
      const response = await fetch(`${apiBase()}/diagnose`, { method: "POST", body: formData });
      if (!response.ok) {
        let detail = `Diagnosis request failed (${response.status})`;
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

      const payload = await response.json();
      const queued = await addWorkbenchItem(payload);
      const queuedId = queued && queued.id ? String(queued.id) : "";
      setSingleDiagnosisStatus(
        queuedId
          ? `Diagnosis complete. Added to workbench (${queuedId}).`
          : "Diagnosis complete. Added to workbench.",
        false
      );
      await refreshQueue();
      if (queuedId) {
        await openDetail(queuedId, true);
      } else {
        await applyRoute();
      }
      setSingleModeOpen(false);
    } catch (error) {
      const message = error && error.message ? error.message : "Failed to run single diagnosis.";
      setSingleDiagnosisStatus(message, true);
      setQueueAlert(compactQueueErrorMessage(message));
    } finally {
      singleDiagnosisSubmitEl.disabled = false;
    }
  }

  function extractCandidate(payload) {
    const uiCandidate = payload && payload.ui ? payload.ui.top_candidate : null;
    if (uiCandidate) {
      return {
        merchant: uiCandidate.merchant || "--",
        amount: Number(uiCandidate.amount),
        date: uiCandidate.date || "--",
        transactionId: uiCandidate.transaction_id || "--",
        description: uiCandidate.description || "--",
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
      description: topMatch ? topMatch.description || "--" : "--",
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

  function renderDiagnosisSummary(payload) {
    const ui = payload && payload.ui ? payload.ui : {};
    const fallbackSummary = payload && payload.diagnosis && payload.diagnosis.label_summary
      ? `${payload.diagnosis.label_summary} (${Number(payload.confidence || 0).toFixed(1)}%)`
      : "Unclassified";
    detailSummaryEl.textContent = ui.diagnosis_summary || fallbackSummary;

    const nextChecks = Array.isArray(ui.next_checks) ? ui.next_checks : [];
    if (!nextChecks.length) {
      detailNextChecksEl.textContent = "Next checks: --";
    } else {
      detailNextChecksEl.textContent = `Next checks: ${nextChecks.join(" | ")}`;
    }
  }

  function setBridgeRowDiscrepancy(rows, enabled) {
    rows.forEach(function (rowEl) {
      if (!rowEl) {
        return;
      }
      rowEl.classList.toggle("bridge-row-discrepancy", !!enabled);
    });
  }

  function normalizedText(value) {
    return String(value || "").trim().toLowerCase();
  }

  function renderEvidenceBridge(payload, candidate) {
    const receipt = payload && payload.receipt ? payload.receipt : {};

    if (detailBridgeReceiptMerchantEl) {
      detailBridgeReceiptMerchantEl.textContent = receipt.vendor || "--";
    }
    if (detailBridgeReceiptAmountEl) {
      detailBridgeReceiptAmountEl.textContent = formatCurrency(receipt.total);
    }
    if (detailBridgeReceiptDateEl) {
      detailBridgeReceiptDateEl.textContent = receipt.date || "--";
    }
    if (detailBridgeBankMerchantEl) {
      detailBridgeBankMerchantEl.textContent = candidate.merchant || "--";
    }
    if (detailBridgeBankAmountEl) {
      detailBridgeBankAmountEl.textContent = formatCurrency(candidate.amount);
    }
    if (detailBridgeBankDateEl) {
      detailBridgeBankDateEl.textContent = candidate.date || "--";
    }

    const merchantMismatch = (
      normalizedText(receipt.vendor)
      && normalizedText(candidate.merchant)
      && normalizedText(receipt.vendor) !== normalizedText(candidate.merchant)
    );
    const amountMismatch = Number.isFinite(candidate.amountPct)
      ? Math.abs(candidate.amountPct) >= 0.1
      : (
        Number.isFinite(Number(receipt.total))
        && Number.isFinite(Number(candidate.amount))
        && Math.abs(Number(receipt.total) - Number(candidate.amount)) >= 0.01
      );
    const dateMismatch = typeof candidate.dateDays === "number"
      ? Math.abs(candidate.dateDays) >= 1
      : (
        normalizedText(receipt.date)
        && normalizedText(candidate.date)
        && normalizedText(receipt.date) !== normalizedText(candidate.date)
      );

    setBridgeRowDiscrepancy(
      [detailBridgeRowMerchantEl, detailBridgeRowMerchantBankEl],
      merchantMismatch
    );
    setBridgeRowDiscrepancy(
      [detailBridgeRowAmountEl, detailBridgeRowAmountBankEl],
      amountMismatch
    );
    setBridgeRowDiscrepancy(
      [detailBridgeRowDateEl, detailBridgeRowDateBankEl],
      dateMismatch
    );
  }

  function applyConfidenceTone(confidenceValue) {
    if (!detailSummarySectionEl) {
      return;
    }
    const confidence = Number(confidenceValue);
    detailSummarySectionEl.classList.remove("conf-high", "conf-medium", "conf-low");
    if (!Number.isFinite(confidence)) {
      return;
    }
    if (confidence >= 80) {
      detailSummarySectionEl.classList.add("conf-high");
      return;
    }
    if (confidence >= 50) {
      detailSummarySectionEl.classList.add("conf-medium");
      return;
    }
    detailSummarySectionEl.classList.add("conf-low");
  }

  function renderOtherCandidates(payload) {
    if (!detailOtherCandidateListEl) {
      return;
    }
    detailOtherCandidateListEl.innerHTML = "";
    const candidates = payload && payload.ui && Array.isArray(payload.ui.other_candidates)
      ? payload.ui.other_candidates
      : [];
    if (!candidates.length) {
      const empty = document.createElement("div");
      empty.className = "candidate-card empty-card";
      empty.textContent = "No additional candidates above threshold.";
      detailOtherCandidateListEl.appendChild(empty);
      return;
    }
    candidates.forEach(function (candidate) {
      const card = document.createElement("div");
      card.className = "candidate-card";
      const title = document.createElement("div");
      title.className = "candidate-title";
      title.textContent = candidate.merchant || "--";
      const meta = document.createElement("div");
      meta.className = "candidate-meta";
      meta.textContent = `${formatCurrency(candidate.amount)} | ${candidate.date || "--"}`;
      const scores = document.createElement("div");
      scores.className = "candidate-meta";
      scores.textContent =
        `Score ${formatPercent(candidate.overall_confidence, 1)} | ` +
        `Vendor ${Number.isFinite(Number(candidate.vendor_similarity_score)) ? Number(candidate.vendor_similarity_score).toFixed(1) : "--"} | ` +
        `Delta ${formatPercent(candidate.amount_delta_pct, 1)} | ` +
        `Date ${candidate.date_delta_days}d`;
      card.appendChild(title);
      card.appendChild(meta);
      card.appendChild(scores);
      detailOtherCandidateListEl.appendChild(card);
    });
  }

  function chooseDefaultGroundingField(fieldMap) {
    const order = ["vendor", "date", "total"];
    for (let i = 0; i < order.length; i += 1) {
      const fieldName = order[i];
      const fieldData = fieldMap ? fieldMap[fieldName] : null;
      if (fieldData && Array.isArray(fieldData.bounding_boxes) && fieldData.bounding_boxes.length > 0) {
        return fieldName;
      }
    }
    return null;
  }

  function scaleBoundingBox(box, imageEl) {
    const displayWidth = imageEl.clientWidth;
    const displayHeight = imageEl.clientHeight;
    const naturalWidth = imageEl.naturalWidth || displayWidth;
    const naturalHeight = imageEl.naturalHeight || displayHeight;
    if (!displayWidth || !displayHeight) {
      return null;
    }

    let x = Number(box.x);
    let y = Number(box.y);
    let width = Number(box.width);
    let height = Number(box.height);
    if ([x, y, width, height].some(Number.isNaN)) {
      return null;
    }

    if (box.normalized) {
      x *= displayWidth;
      y *= displayHeight;
      width *= displayWidth;
      height *= displayHeight;
    } else {
      const xScale = displayWidth / Math.max(naturalWidth, 1);
      const yScale = displayHeight / Math.max(naturalHeight, 1);
      x *= xScale;
      y *= yScale;
      width *= xScale;
      height *= yScale;
    }
    return { x: x, y: y, width: width, height: height };
  }

  function updateGroundingPills() {
    if (!detailGroundingFieldsEl) {
      return;
    }
    const buttons = detailGroundingFieldsEl.querySelectorAll(".field-pill");
    buttons.forEach(function (button) {
      const fieldName = button.getAttribute("data-field");
      const fieldData = state.detailGrounding.fieldMap ? state.detailGrounding.fieldMap[fieldName] : null;
      const available = !!(fieldData && fieldData.available);
      button.disabled = !available;
      button.classList.toggle("active", state.detailGrounding.activeField === fieldName);
    });
  }

  function renderGroundingOverlay() {
    if (!detailOverlayLayerEl) {
      return;
    }
    detailOverlayLayerEl.innerHTML = "";
    const fieldMap = state.detailGrounding.fieldMap;
    if (!state.detailGrounding.showGrounding || !fieldMap || !detailReceiptPreviewImageEl.complete) {
      return;
    }

    let hasAnyBoxes = false;
    Object.keys(fieldMap).forEach(function (fieldName) {
      const fieldData = fieldMap[fieldName];
      const boxes = fieldData && Array.isArray(fieldData.bounding_boxes) ? fieldData.bounding_boxes : [];
      boxes.forEach(function (box) {
        const scaled = scaleBoundingBox(box, detailReceiptPreviewImageEl);
        if (!scaled) {
          return;
        }
        hasAnyBoxes = true;
        const overlay = document.createElement("div");
        overlay.className = "overlay-box";
        overlay.dataset.field = fieldName;
        overlay.style.left = `${scaled.x}px`;
        overlay.style.top = `${scaled.y}px`;
        overlay.style.width = `${scaled.width}px`;
        overlay.style.height = `${scaled.height}px`;
        if (state.detailGrounding.activeField) {
          if (state.detailGrounding.activeField === fieldName) {
            overlay.classList.add("active");
          } else {
            overlay.classList.add("dimmed");
          }
        }
        detailOverlayLayerEl.appendChild(overlay);
      });
    });

    if (!hasAnyBoxes && detailGroundingMessageEl) {
      detailGroundingMessageEl.textContent = "Grounding not available for this extraction.";
      detailGroundingMessageEl.hidden = false;
    }
  }

  function renderGrounding(payload) {
    const ui = payload && payload.ui ? payload.ui : {};
    const groundingView = ui.grounding_view || {};
    const receiptPreview = ui.receipt_preview || {};
    state.detailGrounding.fieldMap = groundingView.fields || null;
    state.detailGrounding.activeField = chooseDefaultGroundingField(state.detailGrounding.fieldMap);
    state.detailGrounding.showGrounding = !!(detailGroundingToggleEl ? detailGroundingToggleEl.checked : true);
    updateGroundingPills();

    const previewDataUrl = receiptPreview.image_data_url || null;
    if (previewDataUrl && detailReceiptPreviewImageEl && detailReceiptViewerContainerEl) {
      detailReceiptPreviewImageEl.src = previewDataUrl;
      detailReceiptPreviewImageEl.hidden = false;
      detailReceiptViewerContainerEl.classList.remove("no-image");
    } else if (detailReceiptPreviewImageEl && detailReceiptViewerContainerEl) {
      detailReceiptPreviewImageEl.removeAttribute("src");
      detailReceiptPreviewImageEl.hidden = true;
      detailReceiptViewerContainerEl.classList.add("no-image");
    }

    const hasBoxes = !!(
      state.detailGrounding.fieldMap
      && Object.values(state.detailGrounding.fieldMap).some(function (fieldData) {
        return Array.isArray(fieldData.bounding_boxes) && fieldData.bounding_boxes.length > 0;
      })
    );

    if (detailGroundingMessageEl) {
      if (!hasBoxes) {
        detailGroundingMessageEl.hidden = false;
        detailGroundingMessageEl.textContent =
          groundingView.message
          || receiptPreview.message
          || "Grounding not available for this extraction.";
      } else if (!state.detailGrounding.showGrounding) {
        detailGroundingMessageEl.hidden = false;
        detailGroundingMessageEl.textContent = "Grounding hidden. Toggle on to view source regions.";
      } else {
        detailGroundingMessageEl.hidden = false;
        detailGroundingMessageEl.textContent = "Click Vendor, Date, or Total to highlight source regions.";
      }
    }

    if (detailReceiptViewerContainerEl) {
      detailReceiptViewerContainerEl.classList.toggle(
        "viewer-focus",
        !!(hasBoxes && state.detailGrounding.showGrounding)
      );
    }

    renderGroundingOverlay();
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
    applyConfidenceTone(Number(payload.confidence || 0));

    renderDiagnosisSummary(payload);
    renderEvidence(payload.evidence || []);
    renderGrounding(payload);
    renderOtherCandidates(payload);
    const candidate = extractCandidate(payload);
    renderEvidenceBridge(payload, candidate);

    detailMerchantEl.textContent = candidate.merchant;
    detailAmountEl.textContent = formatCurrency(candidate.amount);
    detailDateEl.textContent = candidate.date;
    detailTransactionIdEl.textContent = candidate.transactionId;
    detailDescriptionEl.textContent = candidate.description;
    detailVendorScoreEl.textContent = Number.isFinite(candidate.vendorScore) ? candidate.vendorScore.toFixed(1) : "--";
    detailAmountPctEl.textContent = Number.isFinite(candidate.amountPct) ? `${candidate.amountPct.toFixed(1)}%` : "--";
    detailDateDaysEl.textContent = typeof candidate.dateDays === "number" ? String(candidate.dateDays) : "--";
    if (detailOtherCandidatesEl) {
      detailOtherCandidatesEl.open = false;
    }

    detailAuditNoteEl.value = WorkbenchLogic.buildAuditMemo(payload);
    updateResolutionControls();
    updateDecisionNoteInput();
    renderMemoryHints(payload, currentItem);
  }

  function hideDetail() {
    state.currentId = null;
    state.currentPayload = null;
    state.currentViewMode = "queue";
    detailViewEl.hidden = true;
    detailEmptyEl.hidden = false;
    detailAuditNoteEl.value = "";
    detailSummaryEl.textContent = "Summary will appear here.";
    detailNextChecksEl.textContent = "Next checks: --";
    detailDescriptionEl.textContent = "--";
    if (detailBridgeReceiptMerchantEl) {
      detailBridgeReceiptMerchantEl.textContent = "--";
    }
    if (detailBridgeReceiptAmountEl) {
      detailBridgeReceiptAmountEl.textContent = "--";
    }
    if (detailBridgeReceiptDateEl) {
      detailBridgeReceiptDateEl.textContent = "--";
    }
    if (detailBridgeBankMerchantEl) {
      detailBridgeBankMerchantEl.textContent = "--";
    }
    if (detailBridgeBankAmountEl) {
      detailBridgeBankAmountEl.textContent = "--";
    }
    if (detailBridgeBankDateEl) {
      detailBridgeBankDateEl.textContent = "--";
    }
    [
      detailBridgeRowMerchantEl,
      detailBridgeRowMerchantBankEl,
      detailBridgeRowAmountEl,
      detailBridgeRowAmountBankEl,
      detailBridgeRowDateEl,
      detailBridgeRowDateBankEl,
    ].forEach(function (rowEl) {
      if (rowEl) {
        rowEl.classList.remove("bridge-row-discrepancy");
      }
    });
    if (detailSummarySectionEl) {
      detailSummarySectionEl.classList.remove("conf-high", "conf-medium", "conf-low");
    }
    if (detailDiagnosisEl) {
      detailDiagnosisEl.classList.remove("seen-before-dotted");
      detailDiagnosisEl.removeAttribute("title");
    }
    if (detailOtherCandidateListEl) {
      detailOtherCandidateListEl.innerHTML = '<div class="candidate-card empty-card">No additional candidates above threshold.</div>';
    }
    if (detailOtherCandidatesEl) {
      detailOtherCandidatesEl.open = false;
    }
    if (detailGroundingMessageEl) {
      detailGroundingMessageEl.textContent = "Grounding not available for this extraction.";
      detailGroundingMessageEl.hidden = false;
    }
    if (detailReceiptPreviewImageEl) {
      detailReceiptPreviewImageEl.hidden = true;
      detailReceiptPreviewImageEl.removeAttribute("src");
    }
    if (detailReceiptViewerContainerEl) {
      detailReceiptViewerContainerEl.classList.add("no-image");
      detailReceiptViewerContainerEl.classList.remove("viewer-focus");
    }
    if (detailOverlayLayerEl) {
      detailOverlayLayerEl.innerHTML = "";
    }
    state.detailGrounding.fieldMap = null;
    state.detailGrounding.activeField = null;
    if (detailGroundingToggleEl) {
      detailGroundingToggleEl.checked = true;
    }
    if (detailGroundingFieldsEl) {
      const pills = detailGroundingFieldsEl.querySelectorAll(".field-pill");
      pills.forEach(function (pill) {
        pill.disabled = true;
        pill.classList.remove("active");
      });
    }
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
    syncDetailEmptyState();
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
    const transitionId = ++state.detailTransitionId;
    try {
      showThinkingCue();
      const payload = await fetchDetail(itemId);
      if (transitionId !== state.detailTransitionId) {
        return;
      }

      const wasVisible = !detailViewEl.hidden;
      if (wasVisible) {
        detailViewEl.classList.remove("detail-fade-in");
        detailViewEl.classList.add("detail-fade-out");
        await delay(PANEL_FADE_OUT_MS);
        if (transitionId !== state.detailTransitionId) {
          return;
        }
      }

      state.currentId = itemId;
      state.selectedId = itemId;
      state.currentViewMode = "queue";
      const selectedItem = state.queueItems.find(function (item) {
        return item.id === itemId;
      });
      if (selectedItem && selectedItem.session_id) {
        state.currentSessionId = selectedItem.session_id;
        updateSessionLabel();
      }
      renderDetail(payload);
      detailViewEl.classList.remove("detail-fade-out");
      detailViewEl.classList.add("detail-fade-in");
      applyControlsAndRenderQueue();
      updateNavButtons();
      if (pushRoute) {
        history.pushState({ id: itemId }, "", detailUrl(itemId));
      }
      await delay(PANEL_FADE_IN_MS);
      if (transitionId === state.detailTransitionId) {
        detailViewEl.classList.remove("detail-fade-in");
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
      flashAuditCopyMoment();
      if (goNext) {
        const nextId = WorkbenchLogic.getNextQueueId(queueOrderIds(), state.currentId);
        if (nextId) {
          await openDetail(nextId, true);
        }
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
      state.lastSessionCount = Array.isArray(sessions) ? sessions.length : 0;
      state.lastQueueUpdatedAt = new Date();
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
      syncDetailEmptyState();
      updateMorningSurface();
    } catch (error) {
      setQueueStatus(error.message || "Failed to load queue.", true);
      state.queueItems = [];
      state.lastSessionCount = 0;
      state.lastQueueUpdatedAt = new Date();
      applyControlsAndRenderQueue();
      state.currentSessionId = null;
      updateSessionLabel();
      syncDetailEmptyState();
      updateMorningSurface();
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
      state.recentSessionId = result.session_id || null;
      state.recentSessionUntil = Date.now() + NEW_INTELLIGENCE_MS;
      if (state.recentSessionTimer) {
        clearTimeout(state.recentSessionTimer);
      }
      state.recentSessionTimer = setTimeout(function () {
        state.recentSessionId = null;
        state.recentSessionUntil = 0;
        state.recentSessionTimer = null;
        applyControlsAndRenderQueue();
      }, NEW_INTELLIGENCE_MS + 30);
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

  function bindSingleDiagnosisEvents() {
    if (singleDiagnosisToggleEl) {
      singleDiagnosisToggleEl.addEventListener("click", function () {
        setSingleModeOpen(!state.singleModeOpen);
      });
    }
    if (singleAdvancedToggleEl) {
      singleAdvancedToggleEl.addEventListener("click", function () {
        setSingleAdvancedVisible(singleAdvancedFieldsEl ? singleAdvancedFieldsEl.hidden : true);
      });
    }
    if (singleDiagnosisFormEl) {
      singleDiagnosisFormEl.addEventListener("submit", runSingleDiagnosis);
    }
  }

  function bindGroundingEvents() {
    if (detailGroundingFieldsEl) {
      detailGroundingFieldsEl.addEventListener("click", function (event) {
        const target = event.target;
        if (!(target instanceof HTMLElement) || !target.classList.contains("field-pill")) {
          return;
        }
        const fieldName = target.getAttribute("data-field");
        if (!fieldName || !state.detailGrounding.fieldMap || !state.detailGrounding.fieldMap[fieldName]) {
          return;
        }
        state.detailGrounding.activeField = fieldName;
        updateGroundingPills();
        renderGroundingOverlay();
      });
    }

    if (detailGroundingToggleEl) {
      detailGroundingToggleEl.addEventListener("change", function () {
        state.detailGrounding.showGrounding = !!detailGroundingToggleEl.checked;
        if (state.currentPayload) {
          renderGrounding(state.currentPayload);
        } else {
          if (!state.detailGrounding.showGrounding && detailGroundingMessageEl) {
            detailGroundingMessageEl.hidden = false;
            detailGroundingMessageEl.textContent = "Grounding hidden. Toggle on to view source regions.";
          } else if (detailGroundingMessageEl && state.detailGrounding.fieldMap) {
            detailGroundingMessageEl.hidden = false;
            detailGroundingMessageEl.textContent = "Click Vendor, Date, or Total to highlight source regions.";
          }
          if (detailReceiptViewerContainerEl) {
            detailReceiptViewerContainerEl.classList.remove("viewer-focus");
          }
          renderGroundingOverlay();
        }
      });
    }

    if (detailReceiptPreviewImageEl) {
      detailReceiptPreviewImageEl.addEventListener("load", function () {
        if (detailViewerStageEl) {
          detailViewerStageEl.classList.toggle("ready", !!detailReceiptPreviewImageEl.getAttribute("src"));
        }
        renderGroundingOverlay();
      });
    }

    window.addEventListener("resize", function () {
      renderGroundingOverlay();
    });
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
    if (copySummaryBottomBtn) {
      copySummaryBottomBtn.addEventListener("click", function () {
        copyMemo(false);
      });
    }
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
        applyResolutionSelection(target.value);
      });
    }

    if (detailResolveIgnoreBtn) {
      detailResolveIgnoreBtn.addEventListener("click", function () {
        applyResolutionSelection("ignored");
      });
    }
    if (detailResolveFlagBtn) {
      detailResolveFlagBtn.addEventListener("click", function () {
        applyResolutionSelection("follow_up");
      });
    }
    if (detailResolveAcceptBtn) {
      detailResolveAcceptBtn.addEventListener("click", function () {
        applyResolutionSelection("accepted");
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
    setSingleDiagnosisStatus("", false);
    setSingleModeOpen(false);
    setSingleAdvancedVisible(false);
    setWorkspaceSaveStatus("Saved", false);
    updateSessionLabel();
    updateResolutionControls();
    syncDetailEmptyState();
    updateMorningSurface();
  }

  async function init() {
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
    bindSingleDiagnosisEvents();
    bindGroundingEvents();
    bindActions();

    await refreshQueue();
    await applyRoute();
  }

  init();
})();

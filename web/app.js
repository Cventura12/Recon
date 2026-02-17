(function () {
  const form = document.getElementById("diagnose-form");
  const receiptInput = document.getElementById("receipt-file");
  const csvInput = document.getElementById("csv-file");
  const statusText = document.getElementById("status-text");
  const submitBtn = document.getElementById("submit-btn");
  const openWorkbenchLink = document.getElementById("open-workbench-link");
  const openInWorkbenchBtn = document.getElementById("open-in-workbench");

  const aiWordingToggle = document.getElementById("ai-wording");
  const advancedToggle = document.getElementById("advanced-toggle");
  const advancedFields = document.getElementById("advanced-fields");
  const manualVendor = document.getElementById("manual-vendor");
  const manualDate = document.getElementById("manual-date");
  const manualTotal = document.getElementById("manual-total");

  const matchStateBadgeEl = document.getElementById("match-state-badge");
  const confidenceEl = document.getElementById("confidence");
  const diagnosisSummaryEl = document.getElementById("diagnosis-summary");
  const nextChecksEl = document.getElementById("next-checks");
  const evidenceListEl = document.getElementById("evidence-list");

  const topCandidateCardEl = document.getElementById("top-candidate-card");
  const topMerchantEl = document.getElementById("top-merchant");
  const topAmountEl = document.getElementById("top-amount");
  const topDateEl = document.getElementById("top-date");
  const topIdEl = document.getElementById("top-id");
  const topDescriptionEl = document.getElementById("top-description");
  const overallScoreEl = document.getElementById("overall-score");
  const vendorScoreEl = document.getElementById("vendor-score");
  const amountDeltaEl = document.getElementById("amount-delta");
  const amountPctEl = document.getElementById("amount-pct");
  const dateDaysEl = document.getElementById("date-days");

  const otherCandidatesDetailsEl = document.getElementById("other-candidates");
  const otherCandidateListEl = document.getElementById("other-candidate-list");

  const groundingToggle = document.getElementById("grounding-toggle");
  const groundingFieldsEl = document.getElementById("grounding-fields");
  const groundingMessageEl = document.getElementById("grounding-message");
  const receiptViewerContainerEl = document.getElementById("receipt-viewer-container");
  const viewerStageEl = document.getElementById("viewer-stage");
  const receiptPreviewImageEl = document.getElementById("receipt-preview-image");
  const overlayLayerEl = document.getElementById("overlay-layer");

  const auditNoteEl = document.getElementById("audit-note");
  const copySummaryBtn = document.getElementById("copy-summary");
  const downloadJsonBtn = document.getElementById("download-json");

  const debugTraceSectionEl = document.getElementById("debug-trace-section");
  const debugTraceContentEl = document.getElementById("debug-trace-content");

  const BADGE_CLASS = {
    PROBABLE: "badge-probable",
    POSSIBLE: "badge-possible",
    "NO CONFIDENT": "badge-no-confident",
  };
  const DEFAULT_API_BASE = "http://127.0.0.1:8000";
  const API_BASE_STORAGE_KEY = "diagnosticApiBase";

  let lastPayload = null;
  let lastWorkbenchId = null;
  const groundingState = {
    fieldMap: null,
    activeField: null,
    showGrounding: true,
  };

  function apiBase() {
    const params = new URLSearchParams(window.location.search);
    const paramApi = params.get("api");
    if (paramApi && paramApi.trim()) {
      const trimmed = paramApi.trim().replace(/\/+$/, "");
      localStorage.setItem(API_BASE_STORAGE_KEY, trimmed);
      return trimmed;
    }

    const savedApi = localStorage.getItem(API_BASE_STORAGE_KEY);
    if (savedApi && savedApi.trim()) {
      return savedApi.trim().replace(/\/+$/, "");
    }

    return DEFAULT_API_BASE;
  }

  function workbenchHref() {
    return `./workbench/?api=${encodeURIComponent(apiBase())}`;
  }

  function workbenchDetailHref(itemId) {
    if (!itemId) {
      return workbenchHref();
    }
    return `./workbench/?api=${encodeURIComponent(apiBase())}&id=${encodeURIComponent(itemId)}`;
  }

  function setStatus(message, isError) {
    statusText.textContent = message || "";
    statusText.classList.toggle("error", !!isError);
  }

  function setAdvancedVisible(visible) {
    advancedFields.hidden = !visible;
    advancedToggle.setAttribute("aria-expanded", String(visible));
    advancedToggle.textContent = visible ? "Hide Advanced" : "Advanced";
  }

  function formatCurrency(value) {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return "--";
    }
    return `$${value.toFixed(2)}`;
  }

  function formatPercent(value, digits) {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return "--";
    }
    return `${value.toFixed(digits)}%`;
  }

  function formatNumber(value, digits) {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return "--";
    }
    return value.toFixed(digits);
  }

  function applyBadge(matchState) {
    const state = String(matchState || "NO CONFIDENT").toUpperCase();
    matchStateBadgeEl.textContent = state;
    matchStateBadgeEl.className = "badge";
    const className = BADGE_CLASS[state] || "badge-neutral";
    matchStateBadgeEl.classList.add(className);
  }

  function resetTopCandidate() {
    topCandidateCardEl.classList.add("placeholder-card");
    topMerchantEl.textContent = "--";
    topAmountEl.textContent = "--";
    topDateEl.textContent = "--";
    topIdEl.textContent = "--";
    topDescriptionEl.textContent = "--";
    overallScoreEl.textContent = "--";
    vendorScoreEl.textContent = "--";
    amountDeltaEl.textContent = "--";
    amountPctEl.textContent = "--";
    dateDaysEl.textContent = "--";
  }

  function renderTopCandidate(candidate) {
    if (!candidate) {
      resetTopCandidate();
      return;
    }

    topCandidateCardEl.classList.remove("placeholder-card");
    topMerchantEl.textContent = candidate.merchant || "--";
    topAmountEl.textContent = formatCurrency(candidate.amount);
    topDateEl.textContent = candidate.date || "--";
    topIdEl.textContent = candidate.transaction_id || "--";
    topDescriptionEl.textContent = candidate.description || "--";
    overallScoreEl.textContent = formatPercent(candidate.overall_confidence, 1);
    vendorScoreEl.textContent = formatNumber(candidate.vendor_similarity_score, 1);
    amountDeltaEl.textContent = formatCurrency(candidate.amount_delta);
    amountPctEl.textContent = formatPercent(candidate.amount_delta_pct, 1);
    dateDaysEl.textContent = typeof candidate.date_delta_days === "number"
      ? String(candidate.date_delta_days)
      : "--";
  }

  function renderOtherCandidates(candidates) {
    otherCandidateListEl.innerHTML = "";
    const list = Array.isArray(candidates) ? candidates : [];
    if (!list.length) {
      const empty = document.createElement("div");
      empty.className = "candidate-card empty-card";
      empty.textContent = "No additional candidates above threshold.";
      otherCandidateListEl.appendChild(empty);
      return;
    }

    list.forEach(function (candidate) {
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
      scores.textContent = `Score ${formatPercent(candidate.overall_confidence, 1)} | Vendor ${formatNumber(candidate.vendor_similarity_score, 1)} | Delta ${formatPercent(candidate.amount_delta_pct, 1)} | Date ${candidate.date_delta_days}d`;

      card.appendChild(title);
      card.appendChild(meta);
      card.appendChild(scores);
      otherCandidateListEl.appendChild(card);
    });
  }

  function renderEvidence(evidence) {
    evidenceListEl.innerHTML = "";
    if (!Array.isArray(evidence) || !evidence.length) {
      const li = document.createElement("li");
      li.className = "placeholder-line";
      li.textContent = "No evidence recorded.";
      evidenceListEl.appendChild(li);
      return;
    }

    evidence.forEach(function (item) {
      const li = document.createElement("li");
      li.textContent = item;
      evidenceListEl.appendChild(li);
    });
  }

  function renderNextChecks(nextChecks) {
    const list = Array.isArray(nextChecks) ? nextChecks : [];
    if (!list.length) {
      nextChecksEl.textContent = "Next checks: --";
      return;
    }
    nextChecksEl.textContent = `Next checks: ${list.join(" | ")}`;
  }

  function updateGroundingPills(fieldMap) {
    const buttons = groundingFieldsEl.querySelectorAll(".field-pill");
    buttons.forEach(function (button) {
      const fieldName = button.getAttribute("data-field");
      const fieldData = fieldMap ? fieldMap[fieldName] : null;
      const available = !!(fieldData && fieldData.available);
      button.disabled = !available;
      button.classList.toggle("active", groundingState.activeField === fieldName);
    });
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
      x = x * displayWidth;
      y = y * displayHeight;
      width = width * displayWidth;
      height = height * displayHeight;
    } else {
      const xScale = displayWidth / Math.max(naturalWidth, 1);
      const yScale = displayHeight / Math.max(naturalHeight, 1);
      x = x * xScale;
      y = y * yScale;
      width = width * xScale;
      height = height * yScale;
    }

    return { x, y, width, height };
  }

  function renderOverlay() {
    overlayLayerEl.innerHTML = "";
    const fieldMap = groundingState.fieldMap;
    if (!groundingState.showGrounding || !fieldMap || !receiptPreviewImageEl.complete) {
      return;
    }

    const entries = Object.entries(fieldMap);
    let hasAnyBoxes = false;
    entries.forEach(function ([fieldName, fieldData]) {
      const boxes = Array.isArray(fieldData.bounding_boxes) ? fieldData.bounding_boxes : [];
      boxes.forEach(function (box) {
        const scaled = scaleBoundingBox(box, receiptPreviewImageEl);
        if (!scaled) {
          return;
        }
        hasAnyBoxes = true;

        const overlayBox = document.createElement("div");
        overlayBox.className = "overlay-box";
        overlayBox.dataset.field = fieldName;
        overlayBox.style.left = `${scaled.x}px`;
        overlayBox.style.top = `${scaled.y}px`;
        overlayBox.style.width = `${scaled.width}px`;
        overlayBox.style.height = `${scaled.height}px`;

        if (groundingState.activeField) {
          if (groundingState.activeField === fieldName) {
            overlayBox.classList.add("active");
          } else {
            overlayBox.classList.add("dimmed");
          }
        }

        overlayLayerEl.appendChild(overlayBox);
      });
    });

    if (!hasAnyBoxes) {
      groundingMessageEl.textContent = "Grounding not available for this extraction.";
      groundingMessageEl.hidden = false;
    }
  }

  function chooseDefaultActiveField(fieldMap) {
    const order = ["vendor", "date", "total"];
    for (let i = 0; i < order.length; i += 1) {
      const fieldName = order[i];
      const fieldData = fieldMap[fieldName];
      if (fieldData && Array.isArray(fieldData.bounding_boxes) && fieldData.bounding_boxes.length) {
        return fieldName;
      }
    }
    return null;
  }

  function renderGrounding(payload) {
    const ui = payload && payload.ui ? payload.ui : {};
    const groundingView = ui.grounding_view || {};
    const fieldMap = groundingView.fields || null;
    const receiptPreview = ui.receipt_preview || {};
    const previewDataUrl = receiptPreview.image_data_url || null;

    groundingState.fieldMap = fieldMap;
    groundingState.activeField = chooseDefaultActiveField(fieldMap);
    groundingState.showGrounding = groundingToggle.checked;
    updateGroundingPills(fieldMap);

    if (previewDataUrl) {
      receiptPreviewImageEl.src = previewDataUrl;
      receiptPreviewImageEl.hidden = false;
      receiptViewerContainerEl.classList.remove("no-image");
    } else {
      receiptPreviewImageEl.removeAttribute("src");
      receiptPreviewImageEl.hidden = true;
      overlayLayerEl.innerHTML = "";
      receiptViewerContainerEl.classList.add("no-image");
    }

    const hasBoxes = !!(fieldMap && Object.values(fieldMap).some(function (fieldData) {
      return Array.isArray(fieldData.bounding_boxes) && fieldData.bounding_boxes.length > 0;
    }));

    if (!hasBoxes) {
      const previewMessage = receiptPreview.message || null;
      groundingMessageEl.textContent = groundingView.message || previewMessage || "Grounding not available for this extraction.";
      groundingMessageEl.hidden = false;
    } else {
      groundingMessageEl.hidden = false;
      groundingMessageEl.textContent = groundingToggle.checked
        ? "Click Vendor, Date, or Total to highlight source regions."
        : "Grounding hidden. Toggle on to view source regions.";
    }

    renderOverlay();
  }

  function renderDebugTrace(payload) {
    const trace = payload && payload.ui ? payload.ui.debug_trace : null;
    if (!trace) {
      debugTraceSectionEl.hidden = true;
      debugTraceContentEl.textContent = "";
      return;
    }

    debugTraceSectionEl.hidden = false;
    debugTraceContentEl.textContent = JSON.stringify(trace, null, 2);
  }

  function needsManualOverrideHint(payload) {
    const receipt = payload && payload.receipt ? payload.receipt : null;
    if (!receipt) {
      return true;
    }

    const vendor = String(receipt.vendor || "").toUpperCase();
    return receipt.is_low_confidence === true || vendor === "EXTRACTION_ERROR" || vendor === "EXTRACTION_FAILED";
  }

  function summaryLine(payload) {
    const uiSummary = payload && payload.ui ? payload.ui.diagnosis_summary : null;
    const labelSummary = payload && payload.diagnosis ? payload.diagnosis.label_summary : "Unclassified";
    const confidence = typeof payload.confidence === "number" ? payload.confidence.toFixed(1) : "--";
    if (aiWordingToggle.checked) {
      return `Assessment: ${labelSummary}. Confidence ${confidence}%.`;
    }
    return uiSummary || `${labelSummary} (${confidence}%)`;
  }

  function buildAuditNote(payload) {
    const ui = payload.ui || {};
    const topCandidate = ui.top_candidate || payload.top_match || null;
    const label = payload.diagnosis ? payload.diagnosis.label_summary : "Unclassified";
    const confidence = typeof payload.confidence === "number" ? `${payload.confidence.toFixed(1)}%` : "--";
    const badge = ui.match_state_badge || "NO CONFIDENT";
    const timestamp = ui.analysis_timestamp_utc || new Date().toISOString();
    const evidence = Array.isArray(payload.evidence) ? payload.evidence.slice(0, 4) : [];

    const lines = [];
    lines.push(`${badge} Match - ${confidence}`);
    lines.push(`Diagnosis: ${label}`);
    if (topCandidate) {
      lines.push(
        `Candidate: ${topCandidate.merchant || "--"} | ${formatCurrency(topCandidate.amount)} | ${topCandidate.date || "--"}`
      );
      lines.push(
        `Scores: overall ${formatPercent(topCandidate.overall_confidence, 1)}, vendor ${formatNumber(topCandidate.vendor_similarity_score, 1)}, amount_delta ${formatPercent(topCandidate.amount_delta_pct, 1)}, date_delta ${topCandidate.date_delta_days} day(s)`
      );
    }
    if (evidence.length) {
      lines.push("Evidence:");
      evidence.forEach(function (item) {
        lines.push(`- ${item}`);
      });
    }
    lines.push(`Analysis timestamp (UTC): ${timestamp}`);
    return lines.join("\n");
  }

  function renderResults(payload) {
    lastPayload = payload;
    downloadJsonBtn.disabled = false;

    const ui = payload && payload.ui ? payload.ui : {};
    applyBadge(ui.match_state_badge || payload.status || "NO CONFIDENT");
    confidenceEl.textContent = typeof payload.confidence === "number"
      ? `${payload.confidence.toFixed(1)}%`
      : "--%";

    diagnosisSummaryEl.textContent = summaryLine(payload);
    renderNextChecks(ui.next_checks || []);
    renderEvidence(payload.evidence || []);
    renderTopCandidate(ui.top_candidate || null);
    renderOtherCandidates(ui.other_candidates || []);
    renderGrounding(payload);
    renderDebugTrace(payload);

    if (payload.status === "no_match") {
      otherCandidatesDetailsEl.open = false;
    }

    auditNoteEl.value = buildAuditNote(payload);

    if (needsManualOverrideHint(payload)) {
      setAdvancedVisible(true);
      setStatus("Extraction quality appears low. Advanced manual override fields have been expanded.", false);
    }
  }

  function updateOpenWorkbenchButton() {
    if (!openInWorkbenchBtn) {
      return;
    }
    openInWorkbenchBtn.disabled = !lastPayload;
    if (lastWorkbenchId) {
      openInWorkbenchBtn.textContent = `Open in Workbench (${lastWorkbenchId})`;
    } else {
      openInWorkbenchBtn.textContent = "Open in Workbench";
    }
  }

  async function addToWorkbench(payload) {
    const response = await fetch(`${apiBase()}/workbench/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let detail = `Queue insert failed (${response.status})`;
      try {
        const body = await response.json();
        if (body && body.detail) {
          detail = String(body.detail);
        }
      } catch (_unused) {
        // Keep default message.
      }
      throw new Error(detail);
    }

    return response.json();
  }

  async function runDiagnosis(event) {
    event.preventDefault();
    if (!receiptInput.files.length || !csvInput.files.length) {
      setStatus("Select both a receipt file and a transactions CSV file.", true);
      return;
    }

    submitBtn.disabled = true;
    downloadJsonBtn.disabled = true;
    setStatus(`Submitting to ${apiBase()} ...`, false);

    const formData = new FormData();
    formData.append("receipt", receiptInput.files[0]);
    formData.append("csv", csvInput.files[0]);

    if (manualVendor.value.trim()) {
      formData.append("manual_vendor", manualVendor.value.trim());
    }
    if (manualDate.value.trim()) {
      formData.append("manual_date", manualDate.value.trim());
    }
    if (manualTotal.value.trim()) {
      formData.append("manual_total", manualTotal.value.trim());
    }

    try {
      const response = await fetch(`${apiBase()}/diagnose`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let detail = `Request failed with status ${response.status}`;
        try {
          const body = await response.json();
          if (body && body.detail) {
            detail = String(body.detail);
          }
        } catch (_unused) {
          // Keep default error detail.
        }
        throw new Error(detail);
      }

      const payload = await response.json();
      renderResults(payload);
      lastWorkbenchId = null;
      updateOpenWorkbenchButton();

      try {
        const queued = await addToWorkbench(payload);
        lastWorkbenchId = queued && queued.id ? String(queued.id) : null;
        updateOpenWorkbenchButton();
        setStatus(`Analysis complete. Added to Workbench (${queued.id}).`, false);
      } catch (queueError) {
        const queueMessage = queueError && queueError.message
          ? queueError.message
          : "Analysis complete, but queue insert failed.";
        setStatus(queueMessage, true);
      }
    } catch (error) {
      const message = error && error.message ? error.message : "Unexpected error while contacting backend.";
      setStatus(message, true);
    } finally {
      submitBtn.disabled = false;
    }
  }

  function downloadJson() {
    if (!lastPayload) {
      return;
    }
    const blob = new Blob([JSON.stringify(lastPayload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "diagnosis.json";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  async function copyAuditSummary() {
    const text = auditNoteEl.value || "";
    if (!text) {
      setStatus("No summary available to copy.", true);
      return;
    }

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        auditNoteEl.focus();
        auditNoteEl.select();
        document.execCommand("copy");
      }
      setStatus("Audit note copied to clipboard.", false);
    } catch (_unused) {
      setStatus("Copy failed. Select the audit note and copy manually.", true);
    }
  }

  function bindGroundingInteractions() {
    groundingFieldsEl.addEventListener("click", function (event) {
      const target = event.target;
      if (!(target instanceof HTMLElement) || !target.classList.contains("field-pill")) {
        return;
      }
      const fieldName = target.getAttribute("data-field");
      if (!fieldName || !groundingState.fieldMap || !groundingState.fieldMap[fieldName]) {
        return;
      }
      groundingState.activeField = fieldName;
      updateGroundingPills(groundingState.fieldMap);
      renderOverlay();
    });

    groundingToggle.addEventListener("change", function () {
      groundingState.showGrounding = groundingToggle.checked;
      if (groundingToggle.checked) {
        groundingMessageEl.hidden = false;
        if (groundingState.fieldMap) {
          groundingMessageEl.textContent = "Click Vendor, Date, or Total to highlight source regions.";
        }
      } else {
        groundingMessageEl.hidden = false;
        groundingMessageEl.textContent = "Grounding hidden. Toggle on to view source regions.";
      }
      renderOverlay();
    });
  }

  function initializePlaceholders() {
    applyBadge("NO CONFIDENT");
    confidenceEl.textContent = "--%";
    diagnosisSummaryEl.textContent = "Diagnosis will appear here";
    nextChecksEl.textContent = "Next checks: --";
    renderEvidence([]);
    resetTopCandidate();
    renderOtherCandidates([]);
    groundingMessageEl.textContent = "Grounding not available for this extraction.";
    groundingMessageEl.hidden = false;
    auditNoteEl.value = "Diagnosis summary will be generated after analysis.";
    debugTraceSectionEl.hidden = true;
  }

  async function checkBackendHealth() {
    try {
      const response = await fetch(`${apiBase()}/health`, { method: "GET" });
      if (response.ok) {
        setStatus(`Connected to backend: ${apiBase()}`, false);
        return;
      }
    } catch (_unused) {
      // ignore; message below
    }
    setStatus(`Backend not reachable at ${apiBase()}. Start uvicorn and retry.`, true);
  }

  function refreshSummaryWording() {
    if (lastPayload) {
      diagnosisSummaryEl.textContent = summaryLine(lastPayload);
      auditNoteEl.value = buildAuditNote(lastPayload);
    }
  }

  function handleImageLoad() {
    viewerStageEl.classList.toggle("ready", !!receiptPreviewImageEl.getAttribute("src"));
    renderOverlay();
  }

  function openWorkbenchFromResult() {
    window.location.href = workbenchDetailHref(lastWorkbenchId);
  }

  function init() {
    setAdvancedVisible(false);
    initializePlaceholders();
    bindGroundingInteractions();
    checkBackendHealth();
    if (openWorkbenchLink) {
      openWorkbenchLink.href = workbenchHref();
    }
    if (openInWorkbenchBtn) {
      openInWorkbenchBtn.addEventListener("click", openWorkbenchFromResult);
      updateOpenWorkbenchButton();
    }

    advancedToggle.addEventListener("click", function () {
      setAdvancedVisible(advancedFields.hidden);
    });
    form.addEventListener("submit", runDiagnosis);
    downloadJsonBtn.addEventListener("click", downloadJson);
    copySummaryBtn.addEventListener("click", copyAuditSummary);
    aiWordingToggle.addEventListener("change", refreshSummaryWording);
    receiptPreviewImageEl.addEventListener("load", handleImageLoad);
    window.addEventListener("resize", function () {
      renderOverlay();
    });
  }

  init();
})();

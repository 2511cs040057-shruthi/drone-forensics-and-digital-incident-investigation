"use strict";

const API = "";
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const state = { cases: [], evidence: [], reports: [], tab: "integrity", toastTimer: null };
const analysisTabs = {
  integrity: { kicker: "EVIDENCE INTEGRITY", title: "Verify the original file", description: "Compare the stored SHA-256 reference with the current evidence file.", button: "Run verification", endpoint: (id) => `/api/evidence/${id}/verify` },
  timeline: { kicker: "FLIGHT RECONSTRUCTION", title: "Review the flight timeline", description: "Inspect reconstructed events in recorded order.", button: "Load timeline", endpoint: (id) => `/api/timeline/${id}` },
  gps: { kicker: "LOCATION DATA", title: "Inspect GPS records", description: "Review coordinates, altitude, and speed associated with this evidence.", button: "Load GPS route", endpoint: (id) => `/api/gps-route/${id}` },
  anomalies: { kicker: "FLIGHT INTELLIGENCE", title: "Review potential anomalies", description: "Find unusual flight speed, altitude changes, invalid coordinates, and time gaps.", button: "Run anomaly review", endpoint: (id) => `/api/accident-analysis/${id}` },
  custody: { kicker: "EVIDENCE HANDLING", title: "Review chain of custody", description: "Track evidence transfers and handling events recorded for this item.", button: "Load custody history", endpoint: (id) => `/api/evidence/${id}/chain-of-custody` }
};

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const type = response.headers.get("content-type") || "";
  const data = type.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof data === "string" ? data : (data.error || data.message || JSON.stringify(data));
    throw new Error(message || `Request failed (${response.status})`);
  }
  return data;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function dateText(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? escapeHTML(value) : date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => element.classList.remove("show"), 2800);
}

function setHealth(apiOnline, databaseOnline, database) {
  const pulse = $("#side-pulse");
  pulse.className = `pulse ${apiOnline && databaseOnline ? "online" : apiOnline ? "" : "offline"}`;
  $("#side-health").textContent = apiOnline ? "API connected" : "API unavailable";
  $("#side-db").textContent = databaseOnline ? `Database · ${database || "connected"}` : apiOnline ? "Database unavailable" : "Waiting for server";
  $("#footer-api").textContent = apiOnline ? "CONNECTED" : "OFFLINE";
  $("#footer-api").style.color = apiOnline ? "var(--green)" : "var(--red)";
}

async function loadHealth() {
  try {
    await api("/api/test");
    try {
      const result = await api("/api/health");
      setHealth(true, result.status === "healthy", result.database);
    } catch (_) { setHealth(true, false); }
  } catch (_) { setHealth(false, false); }
}

function renderCases() {
  const body = $("#cases-table");
  const cases = state.cases.slice(0, 8);
  $("#case-count").textContent = `${state.cases.length} ${state.cases.length === 1 ? "case" : "cases"}`;
  $("#stat-cases").textContent = state.cases.filter((item) => String(item.status || "Open").toLowerCase() !== "closed").length;
  if (!cases.length) {
    body.innerHTML = '<tr><td colspan="5" class="empty-cell">No cases yet. Create a case to begin an investigation.</td></tr>';
    return;
  }
  body.innerHTML = cases.map((item) => {
    const id = Number(item.case_id);
    const status = String(item.status || "Open");
    return `<tr><td><div class="case-key">${escapeHTML(item.case_number || `CASE-${id}`)}</div><div class="secondary-cell">${escapeHTML(item.case_title || "Untitled case")}</div></td><td>${escapeHTML(item.examiner_name || "Unassigned")}</td><td><span class="status-badge ${status.toLowerCase() === "closed" ? "closed" : "open"}">${escapeHTML(status)}</span></td><td>${dateText(item.created_at)}</td><td><button class="row-action" data-case-evidence="${id}">View evidence</button></td></tr>`;
  }).join("");
  body.querySelectorAll("[data-case-evidence]").forEach((button) => button.addEventListener("click", () => {
    $("#evidence-case-filter").value = button.dataset.caseEvidence;
    loadEvidence();
    location.hash = "evidence";
  }));
}

function fillCaseSelects() {
  const options = state.cases.map((item) => `<option value="${Number(item.case_id)}">${escapeHTML(item.case_number || `CASE-${item.case_id}`)} · ${escapeHTML(item.case_title || "Untitled")}</option>`).join("");
  const selectedUpload = $("#upload-case").value;
  const selectedFilter = $("#evidence-case-filter").value;
  $("#upload-case").innerHTML = `<option value="">Select a case</option>${options}`;
  $("#evidence-case-filter").innerHTML = `<option value="">All cases</option>${options}`;
  if ([...$("#upload-case").options].some((option) => option.value === selectedUpload)) $("#upload-case").value = selectedUpload;
  if ([...$("#evidence-case-filter").options].some((option) => option.value === selectedFilter)) $("#evidence-case-filter").value = selectedFilter;
}

async function loadCases() {
  try {
    const data = await api("/api/cases");
    state.cases = data.cases || [];
    renderCases();
    fillCaseSelects();
  } catch (error) {
    $("#cases-table").innerHTML = `<tr><td colspan="5" class="empty-cell error-cell">${escapeHTML(error.message)}</td></tr>`;
    $("#stat-cases").textContent = "—";
  }
}

function statusClass(value) {
  const status = String(value || "Unknown").toLowerCase();
  if (["verified", "match", "open"].includes(status)) return status === "open" ? "open" : "verified";
  if (["mismatch", "unverifiable"].includes(status)) return status;
  return "closed";
}

function renderEvidence() {
  const body = $("#evidence-table");
  $("#evidence-count").textContent = `${state.evidence.length} ${state.evidence.length === 1 ? "record" : "records"}`;
  $("#stat-evidence").textContent = state.evidence.length;
  $("#stat-verified").textContent = state.evidence.filter((item) => String(item.verification_status || "").toLowerCase() === "verified").length;
  const selected = $("#analysis-evidence").value;
  $("#analysis-evidence").innerHTML = `<option value="">Select evidence</option>${state.evidence.map((item) => `<option value="${Number(item.evidence_id)}">${escapeHTML(item.evidence_code || `EVD-${item.evidence_id}`)} · ${escapeHTML(item.file_name || "Evidence")}</option>`).join("")}`;
  if (state.evidence.some((item) => String(item.evidence_id) === selected)) $("#analysis-evidence").value = selected;
  if (!state.evidence.length) {
    body.innerHTML = '<tr><td colspan="6" class="empty-cell">No evidence records found for this selection.</td></tr>';
    return;
  }
  body.innerHTML = state.evidence.slice(0, 50).map((item) => {
    const id = Number(item.evidence_id);
    const status = item.verification_status || "Pending";
    return `<tr><td><span class="evidence-key">${escapeHTML(item.evidence_code || `EVD-${id}`)}</span><div class="secondary-cell">ID ${id}</div></td><td><div class="primary-cell">${escapeHTML(item.file_name || "Unnamed file")}</div><div class="secondary-cell">${escapeHTML(item.evidence_type || "Digital file")}</div></td><td>${escapeHTML(caseName(item.case_id))}</td><td>${dateText(item.acquired_at || item.created_at)}</td><td><span class="status-badge ${statusClass(status)}">${escapeHTML(status)}</span></td><td><button class="row-action" data-analyze="${id}">Analyze</button></td></tr>`;
  }).join("");
  body.querySelectorAll("[data-analyze]").forEach((button) => button.addEventListener("click", () => {
    $("#analysis-evidence").value = button.dataset.analyze;
    location.hash = "analysis";
    runAnalysis();
  }));
}

function caseName(id) {
  const item = state.cases.find((entry) => Number(entry.case_id) === Number(id));
  return item ? (item.case_number || `CASE-${id}`) : `Case ${id ?? "—"}`;
}

async function loadEvidence() {
  try {
    const caseId = $("#evidence-case-filter").value;
    const data = await api(`/api/evidence${caseId ? `?case_id=${encodeURIComponent(caseId)}` : ""}`);
    state.evidence = data.evidence || [];
    renderEvidence();
  } catch (error) {
    state.evidence = [];
    $("#evidence-table").innerHTML = `<tr><td colspan="6" class="empty-cell error-cell">${escapeHTML(error.message)}</td></tr>`;
    $("#stat-evidence").textContent = "—";
    $("#stat-verified").textContent = "—";
  }
}

async function loadReports() {
  try {
    const data = await api("/api/reports");
    state.reports = data.reports || [];
    $("#stat-reports").textContent = state.reports.length;
    const body = $("#reports-table");
    if (!state.reports.length) {
      body.innerHTML = '<tr><td colspan="5" class="empty-cell">No reports have been generated yet.</td></tr>';
      return;
    }
    body.innerHTML = state.reports.slice(0, 10).map((item) => `<tr><td><span class="case-key">${escapeHTML(item.report_number || `REPORT-${item.report_id}`)}</span><div class="secondary-cell">${escapeHTML(item.report_type || "Forensic report")}</div></td><td>${escapeHTML(caseName(item.case_id))}</td><td>${dateText(item.generated_at)}</td><td><span class="status-badge verified">${escapeHTML(item.status || "Generated")}</span></td><td><a class="row-action" href="/api/reports/${Number(item.report_id)}/download">Download PDF</a></td></tr>`).join("");
  } catch (error) {
    $("#reports-table").innerHTML = `<tr><td colspan="5" class="empty-cell error-cell">${escapeHTML(error.message)}</td></tr>`;
    $("#stat-reports").textContent = "—";
  }
}

function updateAnalysisTab(tab) {
  state.tab = tab;
  $$(".analysis-tab").forEach((button) => {
    const selected = button.dataset.tab === tab;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-selected", String(selected));
  });
  const config = analysisTabs[tab];
  $("#analysis-kicker").textContent = config.kicker;
  $("#analysis-title").textContent = config.title;
  $("#analysis-description").textContent = config.description;
  $("#analysis-run").textContent = config.button;
  $("#analysis-result").innerHTML = '<div class="result-placeholder"><span>⌁</span><p>Select evidence, then run an analysis to see results.</p></div>';
}

function chip(label, value) {
  return `<div class="data-chip"><small>${escapeHTML(label)}</small><b>${escapeHTML(value ?? "—")}</b></div>`;
}

function renderAnalysis(tab, data) {
  const target = $("#analysis-result");
  if (tab === "integrity") {
    const status = data.status || data.integrity_status || "UNVERIFIABLE";
    const cls = statusClass(status);
    target.innerHTML = `<div class="data-grid">${chip("RESULT", status)}${chip("ALGORITHM", data.algorithm || "SHA-256")}${chip("EVIDENCE ID", data.evidence_id)}${chip("VERIFIED", data.integrity_verified ? "Yes" : "No")}</div><div class="result-row" style="margin-top:8px"><small>REFERENCE HASH</small><div class="result-hash">${escapeHTML(data.reference_hash || "No reference hash available")}</div><small style="display:block;margin-top:8px">CURRENT HASH</small><div class="result-hash">${escapeHTML(data.current_hash || data.message || "Not calculated")}</div><span class="status-badge ${cls}" style="margin-top:9px">${escapeHTML(data.message || status)}</span></div>`;
    return;
  }
  if (tab === "timeline") {
    const rows = data.timeline || [];
    target.innerHTML = rows.length ? `<div class="result-list">${rows.map((row) => `<div class="result-row"><small>${dateText(row.event_time || row.timestamp)}</small><b style="display:block;margin-top:3px">${escapeHTML(row.event_type || row.event_name || row.description || "Flight event")}</b>${row.description && row.event_type ? `<p>${escapeHTML(row.description)}</p>` : ""}</div>`).join("")}</div>` : `<div class="result-empty">${escapeHTML(data.message || "No reconstructed timeline records are available for this evidence.")}</div>`;
    return;
  }
  if (tab === "gps") {
    const rows = data.route || data.records || [];
    target.innerHTML = rows.length ? `<div class="data-grid">${chip("FLIGHT ID", data.flight_id)}${chip("GPS POINTS", rows.length)}</div><div class="table-wrap route-list" style="margin-top:9px"><table><thead><tr><th>TIME</th><th>LATITUDE</th><th>LONGITUDE</th><th>ALTITUDE</th><th>SPEED</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${dateText(row.timestamp)}</td><td>${escapeHTML(row.latitude)}</td><td>${escapeHTML(row.longitude)}</td><td>${escapeHTML(row.altitude ?? "—")}</td><td>${escapeHTML(row.speed ?? "—")}</td></tr>`).join("")}</tbody></table></div>` : '<div class="result-empty">No GPS route records are available for this evidence.</div>';
    return;
  }
  if (tab === "anomalies") {
    const rows = data.anomalies || [];
    target.innerHTML = `<div class="data-grid">${chip("RECORDS ANALYZED", data.records_analyzed ?? "—")}${chip("ANOMALIES FOUND", data.anomaly_count ?? rows.length)}</div>${rows.length ? `<div class="result-list" style="margin-top:9px">${rows.map((row) => `<div class="result-row"><small>${dateText(row.timestamp)} · ${escapeHTML(row.severity || "Review")}</small><b style="display:block;margin-top:3px">${escapeHTML(row.type || "Potential anomaly")}</b><p>${escapeHTML(row.description || "")}</p></div>`).join("")}</div>` : `<div class="result-empty">${escapeHTML(data.message || "No potential anomalies were reported.")}</div>`}`;
    return;
  }
  if (tab === "custody") {
    const rows = data.chain_of_custody || [];
    target.innerHTML = rows.length ? `<div class="result-list">${rows.map((row) => `<div class="result-row"><small>${dateText(row.transferred_at)}</small><b style="display:block;margin-top:3px">${escapeHTML(row.action || "Evidence handling")}</b><p>${escapeHTML(row.released_by || "—")} → ${escapeHTML(row.received_by || "—")}${row.location ? ` · ${escapeHTML(row.location)}` : ""}</p>${row.remarks ? `<p>${escapeHTML(row.remarks)}</p>` : ""}</div>`).join("")}</div>` : '<div class="result-empty">No chain-of-custody events are recorded for this evidence.</div>';
  }
}

async function runAnalysis() {
  const id = Number($("#analysis-evidence").value);
  const target = $("#analysis-result");
  if (!Number.isInteger(id) || id < 1) {
    target.innerHTML = '<div class="result-error">Select an evidence item first.</div>';
    return;
  }
  const button = $("#analysis-run");
  button.disabled = true;
  button.textContent = "Loading…";
  target.innerHTML = '<div class="result-placeholder"><span>⌁</span><p>Requesting analysis from the Flask API…</p></div>';
  try {
    const result = await api(analysisTabs[state.tab].endpoint(id));
    renderAnalysis(state.tab, result);
  } catch (error) {
    target.innerHTML = `<div class="result-error">${escapeHTML(error.message)}</div>`;
  } finally {
    button.disabled = false;
    button.textContent = analysisTabs[state.tab].button;
  }
}

function openCaseDialog() {
  $("#case-message").textContent = "";
  $("#case-form").reset();
  $("#case-dialog").showModal();
}

async function createCase(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const message = $("#case-message");
  const button = form.querySelector('[type="submit"]');
  const data = Object.fromEntries(new FormData(form).entries());
  for (const key of Object.keys(data)) data[key] = data[key].trim();
  button.disabled = true;
  message.textContent = "Creating case…";
  try {
    const result = await api("/api/cases", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    $("#case-dialog").close();
    toast(`Case ${result.case_number} created`);
    await Promise.all([loadCases(), loadEvidence()]);
    $("#upload-case").value = result.case_id;
  } catch (error) {
    message.textContent = error.message;
    message.className = "form-message error";
  } finally { button.disabled = false; }
}

async function uploadEvidence(event) {
  event.preventDefault();
  const file = $("#evidence-file").files[0];
  const caseId = $("#upload-case").value;
  const message = $("#upload-message");
  const button = $("#upload-submit");
  if (!file || !caseId) return;
  const form = new FormData();
  form.append("case_id", caseId);
  form.append("file", file);
  const processFlightLog = $("#process-flight-log")?.checked;
  button.disabled = true;
  message.className = "form-message";
  message.textContent = processFlightLog ? "Processing flight log and registering evidence…" : "Uploading file and registering evidence…";
  try {
    const result = await api(processFlightLog ? "/api/flight-log/process" : "/api/evidence/upload", { method: "POST", body: form });
    message.className = "form-message success";
    message.textContent = `Evidence ${result.evidence_code || `#${result.evidence_id}`} registered successfully.`;
    toast("Evidence registered");
    $("#evidence-file").value = "";
    $("#file-label").textContent = "Choose a file to upload";
    await Promise.all([loadEvidence(), loadReports()]);
    if (result.evidence_id) $("#analysis-evidence").value = result.evidence_id;
  } catch (error) {
    message.className = "form-message error";
    message.textContent = error.message;
  } finally { button.disabled = false; }
}

async function downloadGeneratedReport() {
  const id = Number($("#analysis-evidence").value);
  if (!Number.isInteger(id) || id < 1) { toast("Select evidence before generating a report"); return; }
  const button = $("#analysis-run");
  try {
    const response = await fetch(`/api/reports/${id}`);
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Could not generate report (${response.status})`);
    }
    const blob = await response.blob();
    const disposition = response.headers.get("content-disposition") || "";
    const filename = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
    const name = filename ? decodeURIComponent(filename[1] || filename[2]) : `forensic-report-${id}.pdf`;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    link.click();
    URL.revokeObjectURL(url);
    toast("Forensic report downloaded");
    await loadReports();
  } catch (error) { toast(error.message); }
  finally { if (button) button.disabled = false; }
}

async function refreshAll() {
  await Promise.all([loadHealth(), loadCases()]);
  await Promise.all([loadEvidence(), loadReports()]);
}

document.addEventListener("DOMContentLoaded", () => {
  $("#case-form").addEventListener("submit", createCase);
  $("#upload-form").addEventListener("submit", uploadEvidence);
  $("#evidence-file").addEventListener("change", (event) => {
    $("#file-label").textContent = event.target.files[0]?.name || "Choose a file to upload";
  });
  $$("[data-open-case]").forEach((button) => button.addEventListener("click", openCaseDialog));
  $$(".close-modal").forEach((button) => button.addEventListener("click", () => $("#case-dialog").close()));
  $$(".analysis-tab").forEach((button) => button.addEventListener("click", () => updateAnalysisTab(button.dataset.tab)));
  $("#analysis-run").addEventListener("click", runAnalysis);
  $("#analysis-evidence").addEventListener("change", () => { $("#analysis-result").innerHTML = '<div class="result-placeholder"><span>⌁</span><p>Evidence selected. Run an analysis to see results.</p></div>'; });
  $("#evidence-case-filter").addEventListener("change", loadEvidence);
  $("#reload-cases").addEventListener("click", loadCases);
  $("#reload-evidence").addEventListener("click", loadEvidence);
  $("#reload-reports").addEventListener("click", loadReports);
  $("#refresh-button").addEventListener("click", refreshAll);
  $("#report-generate")?.addEventListener("click", downloadGeneratedReport);
  $(".side-nav").addEventListener("click", (event) => {
    const link = event.target.closest(".nav-link");
    if (!link) return;
    $$(".nav-link").forEach((item) => item.classList.toggle("active", item === link));
  });
  refreshAll();
});

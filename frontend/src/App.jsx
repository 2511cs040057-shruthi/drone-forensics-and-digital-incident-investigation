import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, AlertTriangle, ArrowUpRight, Bookmark,
  CalendarDays, Check, CheckCircle2, ChevronDown, ChevronRight, Clock3,
  Database, FileBarChart, FileCheck2, FileClock, Files, Flag, FolderKanban,
  Gauge, Image, Link2, ListFilter, LogOut, MapPinned, Menu, Plane, Plus,
  Search, Settings, ShieldCheck, Upload, Waypoints,
  X,
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip as MapTooltip } from "react-leaflet";
import {
  demoActivity, demoCases, demoEvidence, demoEvents, demoRoute, demoSummary,
  demoSensor, demoTelemetry,
} from "./data/demo.js";
import { authApi, caseApi } from "./services/caseApi.js";
import LoginPage from "./LoginPage.jsx";
import EvidenceAcquisition from "./pages/EvidenceAcquisition.jsx";

const navigation = [
  { id: "dashboard", label: "Dashboard", icon: Activity, group: "WORKSPACE" },
  { id: "cases", label: "Case Management", icon: FolderKanban },
  { id: "acquisition", label: "Evidence Acquisition", icon: Upload },
  { id: "explorer", label: "Evidence Explorer", icon: Files },
  { id: "flight", label: "Flight Log Analysis", icon: Plane, group: "ANALYSIS" },
  { id: "gps", label: "GPS Flight Map", icon: MapPinned },
  { id: "image", label: "Image & EXIF Analysis", icon: Image },
  { id: "sensors", label: "Sensor Data Analysis", icon: Gauge },
  { id: "timeline", label: "Incident Timeline", icon: Clock3 },
  { id: "integrity", label: "Integrity Verification", icon: ShieldCheck, group: "EVIDENCE" },
  { id: "bookmarks", label: "Bookmarks & Findings", icon: Bookmark },
  { id: "custody", label: "Chain of Custody", icon: Link2 },
  { id: "reports", label: "Forensic Reports", icon: FileBarChart, group: "OUTPUT" },
  { id: "settings", label: "Settings", icon: Settings },
];

const phaseInfo = {
  acquisition: ["Evidence Acquisition", "Phase 3", "Evidence uploads, immutable originals, hash registration, and AutopsyBridge package import."],
  explorer: ["Evidence Explorer", "Phase 6", "Folder navigation, metadata, file previews, byte-level inspection, and authorized working-copy downloads."],
  flight: ["Flight Log Analysis", "Phase 4", "CSV parser adapters, telemetry charts, event filtering, time windows, and filtered exports."],
  gps: ["GPS Flight Map", "Phase 5", "Leaflet flight paths, timestamped points, event markers, and synchronized selection."],
  image: ["Image & EXIF Analysis", "Phase 5", "Image previews, ExifTool metadata, GPS fields, and nearby flight-event correlation."],
  sensors: ["Sensor Data Analysis", "Phase 5", "Verified BARO, IMU, and VIBE sensor telemetry analysis."],
  timeline: ["Incident Timeline", "Phase 6", "Chronological view across flight, GPS, image, sensor, acquisition, and verification records."],
  integrity: ["Integrity Verification", "Phase 3", "SHA-256 recalculation, immutable source handling, comparison, and verification history."],
  bookmarks: ["Bookmarks & Findings", "Phase 6", "Investigator notes, categories, saved evidence, and report-ready findings."],
  custody: ["Chain of Custody", "Phase 7", "Append-only transfer history with examiner, action, time, source, and evidence hash."],
  reports: ["Forensic Reports", "Phase 7", "Case-aware PDF reports with evidence inventory, integrity, timeline, findings, and custody."],
  settings: ["Settings", "Phase 1 setup", "Local service configuration, evidence storage preferences, and demonstration mode."],
};

function Sidebar({ page, setPage, mobileOpen, setMobileOpen, demoMode, apiStatus, user, onLogout }) {
  return <>
    {mobileOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
      <div className="brand-row">
        <div className="brand-symbol"><Waypoints size={21} strokeWidth={1.8} /></div>
        <div className="brand-copy"><b>DRONE FORENSICS</b><span>INVESTIGATION SYSTEM</span></div>
        <button className="sidebar-close" aria-label="Close navigation" onClick={() => setMobileOpen(false)}><X size={18} /></button>
      </div>
      <div className="workspace-switch"><span className="workspace-avatar">DF</span><span className="workspace-copy"><b>Forensic Lab</b><small>Local workspace</small></span><ChevronDown size={14} /></div>
      <nav className="sidebar-nav" aria-label="Application sections">
        {navigation.map((item) => {
          const Icon = item.icon;
          return <div key={item.id}>
            {item.group && <div className="nav-group-label">{item.group}</div>}
            <button className={`nav-item ${page === item.id ? "active" : ""}`} onClick={() => { setPage(item.id); setMobileOpen(false); }} aria-current={page === item.id ? "page" : undefined}>
              <Icon size={16} strokeWidth={1.8} /><span>{item.label}</span>
            </button>
          </div>;
        })}
      </nav>
      <div className="sidebar-bottom">
        <div className="storage-card"><div className="storage-head"><Database size={14} /><span>{demoMode ? "DEMO DATA STORE" : "MYSQL CASE STORE"}</span><span className={`storage-dot ${!demoMode && apiStatus === "healthy" ? "connected" : ""}`} /></div><b>{demoMode ? "Isolated sample records" : apiStatus === "healthy" ? "Connected" : "API connection pending"}</b><small>{demoMode ? "Training data is not saved to the case database." : "Case records are stored in the configured MySQL database."}</small></div>
        <div className="profile-row"><div className="profile-avatar">{user.username.slice(0, 2).toUpperCase()}</div><div><b>{user.username}</b><small>Investigator workspace</small></div><button type="button" onClick={onLogout} title="Sign out" aria-label="Sign out"><LogOut size={15} /></button></div>
      </div>
    </aside>
  </>;
}

function Header({ activeCase, setActiveCase, cases, demoMode, setDemoMode, setMobileOpen, search, setSearch, page, user }) {
  return <header className="topbar">
    <div className="topbar-left"><button className="mobile-menu" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={19} /></button><div className="breadcrumb">Workspace <ChevronRight size={13} /> <b>{navigation.find((item) => item.id === page)?.label || "Dashboard"}</b></div></div>
    <div className="topbar-right">
      <label className="global-search"><Search size={15} /><input id="global-search-input" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search cases and evidence" /><kbd>Ctrl K</kbd></label>
      <div className="top-divider" />
      <div className="case-select-wrap"><span>{demoMode ? "ACTIVE DEMO CASE" : "ACTIVE CASE"}</span>{cases.length ? <><select value={activeCase ? (demoMode ? activeCase.id : String(activeCase.case_id)) : ""} onChange={(event) => setActiveCase(event.target.value)} aria-label="Select active case">{cases.map((item) => <option key={demoMode ? item.id : item.case_id} value={demoMode ? item.id : item.case_id}>{demoMode ? item.id : item.case_number} · {demoMode ? item.title : item.case_title}</option>)}</select><ChevronDown size={13} /></> : <div className="no-live-case">{demoMode ? "No demo cases" : "No live cases"}</div>}</div>
      <button className={`mode-pill ${demoMode ? "demo" : "real"}`} onClick={() => setDemoMode(!demoMode)} title="Switch between isolated demo data and real evidence mode"><span className="mode-dot" />{demoMode ? "DEMO MODE" : "REAL DATA"}<ChevronDown size={12} /></button>
      <div className="top-avatar">{user.username.slice(0, 2).toUpperCase()}</div>
    </div>
  </header>;
}

function StatCard({ icon: Icon, label, value, detail, tone, trend }) {
  return <article className="stat-card"><div className="stat-card-top"><span>{label}</span><span className={`stat-icon ${tone}`}><Icon size={16} /></span></div><div className="stat-value-row"><strong>{value}</strong>{trend && <span className="stat-trend"><ArrowUpRight size={12} />{trend}</span>}</div><small>{detail}</small></article>;
}

function SectionTitle({ eyebrow, title, action, onAction }) {
  return <div className="section-title"><div><span className="section-eyebrow">{eyebrow}</span><h2>{title}</h2></div>{action && <button className="link-button" onClick={onAction}>{action}<ArrowUpRight size={14} /></button>}</div>;
}

function TelemetryPanel({ series, setSeries }) {
  const isAltitude = series === "altitude";
  return <section className="surface telemetry-panel">
    <SectionTitle eyebrow="FLIGHT TELEMETRY · DEMO DATA" title="Flight profile" action="Open flight analysis" onAction={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "flight" }))} />
    <div className="chart-toolbar"><div className="chart-legend"><i className={isAltitude ? "legend-line altitude-line" : "legend-line speed-line"} /><span>{isAltitude ? "Altitude (m)" : "Ground speed (m/s)"}</span><span className="chart-period"><CalendarDays size={13} /> 21 Oct · 09:14–09:36</span></div><div className="segmented-control"><button className={isAltitude ? "selected" : ""} onClick={() => setSeries("altitude")}>Altitude</button><button className={!isAltitude ? "selected" : ""} onClick={() => setSeries("speed")}>Speed</button></div></div>
    <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%">
      {isAltitude ? <AreaChart data={demoTelemetry} margin={{ top: 6, right: 10, left: -17, bottom: 0 }}><defs><linearGradient id="altitudeGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#087f83" stopOpacity={0.18} /><stop offset="96%" stopColor="#087f83" stopOpacity={0} /></linearGradient></defs><CartesianGrid vertical={false} stroke="#e8edf0" strokeDasharray="3 4" /><XAxis dataKey="time" tickLine={false} axisLine={false} tick={{ fill: "#89969b", fontSize: 10 }} interval={1} /><YAxis tickLine={false} axisLine={false} tick={{ fill: "#89969b", fontSize: 10 }} domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} /><Tooltip contentStyle={{ border: "1px solid #e1e9e8", borderRadius: 8, fontSize: 12 }} formatter={(value) => [`${value} m`, "Altitude"]} /><Area type="monotone" dataKey="altitude" stroke="#087f83" strokeWidth={2.2} fill="url(#altitudeGradient)" activeDot={{ r: 4, fill: "#087f83", stroke: "white", strokeWidth: 2 }} /></AreaChart>
        : <LineChart data={demoTelemetry} margin={{ top: 6, right: 10, left: -17, bottom: 0 }}><CartesianGrid vertical={false} stroke="#e8edf0" strokeDasharray="3 4" /><XAxis dataKey="time" tickLine={false} axisLine={false} tick={{ fill: "#89969b", fontSize: 10 }} interval={1} /><YAxis tickLine={false} axisLine={false} tick={{ fill: "#89969b", fontSize: 10 }} domain={[0, 25]} ticks={[0, 5, 10, 15, 20, 25]} /><Tooltip contentStyle={{ border: "1px solid #e1e9e8", borderRadius: 8, fontSize: 12 }} formatter={(value) => [`${value} m/s`, "Speed"]} /><Line type="monotone" dataKey="speed" stroke="#d19342" strokeWidth={2.2} dot={false} activeDot={{ r: 4, fill: "#d19342", stroke: "white", strokeWidth: 2 }} /></LineChart>}
    </ResponsiveContainer></div>
    <div className="chart-foot"><span><i className="chart-foot-dot" />Synthetic training telemetry</span><span>Values shown are simulated · DEMO DATA</span></div>
  </section>;
}

function RouteMap() {
  return <div className="map-frame"><MapContainer center={demoRoute[4]} zoom={15} scrollWheelZoom={false} zoomControl={false} attributionControl={false}>
    <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <Polyline positions={demoRoute} pathOptions={{ color: "#087f83", weight: 4, opacity: 0.88 }} />
    <CircleMarker center={demoRoute[0]} radius={6} pathOptions={{ color: "#fff", weight: 2, fillColor: "#1a9b72", fillOpacity: 1 }}><MapTooltip direction="top">DEMO start</MapTooltip></CircleMarker>
    <CircleMarker center={demoRoute[demoRoute.length - 1]} radius={6} pathOptions={{ color: "#fff", weight: 2, fillColor: "#c67835", fillOpacity: 1 }}><MapTooltip direction="top">DEMO end</MapTooltip></CircleMarker>
  </MapContainer><div className="map-demo-chip"><span /> DEMO ROUTE</div></div>;
}

function MapPanel() {
  return <section className="surface map-panel"><SectionTitle eyebrow="GPS FLIGHT MAP" title="Route overview" action="View map" onAction={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "gps" }))} /><RouteMap /><div className="map-meta"><span><i className="map-point start" />Launch</span><span><i className="map-point end" />Landing</span><span className="map-coords">12 points · simulated route</span></div></section>;
}

function EvidencePanel({ query }) {
  const rows = demoEvidence.filter((item) => `${item.name} ${item.type}`.toLowerCase().includes(query.toLowerCase())).slice(0, 4);
  return <section className="surface evidence-panel"><SectionTitle eyebrow="EVIDENCE REGISTER · DEMO DATA" title="Recent evidence" action="Open explorer" onAction={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "explorer" }))} />
    <div className="data-table-wrap"><table className="data-table"><thead><tr><th>FILE</th><th>TYPE</th><th>SIZE</th><th>SHA-256</th><th>ACQUIRED</th></tr></thead><tbody>{rows.map((item) => <tr key={item.name}><td><span className="file-kind"><Files size={14} /></span><b>{item.name}</b></td><td>{item.type}</td><td>{item.size}</td><td><span className="hash-match"><Check size={12} />{item.hash}</span></td><td>{item.time}</td></tr>)}{!rows.length && <tr><td colSpan="5" className="no-results">No matching demo evidence.</td></tr>}</tbody></table></div>
    <div className="table-foot"><span>All listed items are synthetic samples</span><button className="small-action" onClick={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "explorer" }))}>Browse evidence <ChevronRight size={13} /></button></div>
  </section>;
}

function ActivityPanel() {
  const iconMap = { file: FileCheck2, shield: ShieldCheck, image: Image, flag: Flag };
  return <section className="surface activity-panel"><SectionTitle eyebrow="AUDIT PREVIEW · DEMO DATA" title="Recent activity" action="View timeline" onAction={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "timeline" }))} />
    <div className="activity-list">{demoActivity.map((item, index) => { const Icon = iconMap[item.icon]; return <div className="activity-row" key={item.title}><span className={`activity-icon ${item.tint}`}><Icon size={14} /></span><div className="activity-copy"><b>{item.title}</b><small>{item.meta}</small></div>{index === 0 && <span className="activity-new">NEW</span>}</div>; })}</div>
    <div className="activity-footer"><span><span className="live-dot" />Demo event stream</span><button className="small-action" onClick={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "timeline" }))}>Open audit log <ChevronRight size={13} /></button></div>
  </section>;
}

function EventsPanel() {
  return <section className="surface events-panel"><SectionTitle eyebrow="INVESTIGATION REVIEW · DEMO DATA" title="Alerts & key events" action="Review events" onAction={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "flight" }))} />
    <div className="alert-summary"><span><AlertTriangle size={13} /></span><div><b>{demoSummary.reviewCount} evidence items need review</b><small>Simulated integrity review queue</small></div><ChevronRight size={13} /></div>
    <div className="event-list">{demoEvents.map((event) => <div className="event-row" key={event.time}><span className={`event-marker ${event.level}`} /><span className="event-time">{event.time}</span><div><b>{event.label}</b><small>{event.detail}</small></div><ChevronRight size={14} /></div>)}</div>
  </section>;
}

function EvidenceTypePanel() {
  return <section className="surface type-panel"><SectionTitle eyebrow="EVIDENCE INVENTORY · DEMO DATA" title="Evidence by type" action="Open explorer" onAction={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "explorer" }))} />
    <div className="type-chart-row"><div className="type-chart"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={demoSummary.evidenceTypes} dataKey="count" nameKey="type" innerRadius={30} outerRadius={43} paddingAngle={3} stroke="none">{demoSummary.evidenceTypes.map((entry) => <Cell key={entry.type} fill={entry.color} />)}</Pie><Tooltip contentStyle={{ border: "1px solid #e1e9e8", borderRadius: 7, fontSize: 10 }} /></PieChart></ResponsiveContainer><span>{demoSummary.evidenceCount}<small>FILES</small></span></div>
    <div className="type-legend">{demoSummary.evidenceTypes.map((item) => <div key={item.type}><i style={{ background: item.color }} /><span>{item.type}</span><b>{item.count}</b></div>)}</div></div>
    <div className="type-foot"><AlertTriangle size={12} /> Counts are synthetic demo records</div>
  </section>;
}

function SensorPanel() {
  return <section className="surface sensor-panel"><SectionTitle eyebrow="BMP280 · DEMO DATA" title="Sensor conditions" action="Open sensor analysis" onAction={() => window.dispatchEvent(new CustomEvent("navigate", { detail: "sensors" }))} />
    <div className="sensor-values"><div><span>TEMPERATURE</span><b>24.8 <small>°C</small></b><em>+0.8° over flight</em></div><div><span>PRESSURE</span><b>1007.6 <small>hPa</small></b><em>−1.2 hPa over flight</em></div></div>
    <div className="sensor-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={demoSensor} margin={{ top: 3, right: 4, bottom: 0, left: -28 }}><CartesianGrid vertical={false} stroke="#edf1f2" strokeDasharray="3 4" /><XAxis dataKey="time" tickLine={false} axisLine={false} tick={{ fill: "#99a5aa", fontSize: 9 }} interval={1} /><YAxis yAxisId="temp" domain={[23, 26]} hide /><YAxis yAxisId="pressure" domain={[1006, 1010]} orientation="right" hide /><Tooltip contentStyle={{ border: "1px solid #e1e9e8", borderRadius: 8, fontSize: 11 }} /><Line yAxisId="temp" type="monotone" dataKey="temp" name="Temperature °C" stroke="#d19342" dot={false} strokeWidth={1.8} /><Line yAxisId="pressure" type="monotone" dataKey="pressure" name="Pressure hPa" stroke="#527caa" dot={false} strokeWidth={1.8} /></LineChart></ResponsiveContainer></div>
    <div className="sensor-note"><AlertTriangle size={13} /> Synthetic BMP280 sample · humidity not included</div>
  </section>;
}

function Dashboard({ demoMode, activeCase, setPage, query, series, setSeries, setDemoMode, realCases, realCase, loading, apiError, apiStatus }) {
  if (!demoMode) return <LiveDashboard cases={realCases} activeCase={realCase} setPage={setPage} loading={loading} apiError={apiError} apiStatus={apiStatus} query={query} />;
  return <>
    <div className="demo-banner"><div className="demo-banner-icon"><AlertTriangle size={16} /></div><div><b>DEMONSTRATION MODE</b><span>Every case, record, coordinate, and chart on this screen is synthetic demo data. Nothing is stored as real evidence.</span></div><span className="demo-banner-tag">ISOLATED DATASET</span></div>
    <div className="page-title-row"><div><div className="page-kicker"><span>INVESTIGATION WORKSPACE</span><span className="kicker-divider">/</span><span>CASE OVERVIEW</span></div><h1>Forensic dashboard</h1><p>Review case activity, evidence integrity, and flight telemetry in one workspace.</p></div><div className="page-title-actions"><span className="case-status-chip"><i />{activeCase.status.toUpperCase()}</span><button className="outline-button" onClick={() => setPage("cases")}><FolderKanban size={15} /> Case overview</button></div></div>
    <div className="active-case-strip"><div className="case-badge">{activeCase.id.slice(-4)}</div><div className="active-case-main"><span>ACTIVE INVESTIGATION</span><b>{activeCase.title}</b></div><div className="active-case-detail"><span>CASE REFERENCE</span><b>{activeCase.id}</b></div><div className="active-case-detail"><span>EXAMINER</span><b>{activeCase.examiner}</b></div><div className="active-case-detail"><span>OPENED</span><b>{new Date(activeCase.date).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}</b></div><button className="case-chevron" aria-label="Open case management" onClick={() => setPage("cases")}><ChevronRight size={18} /></button></div>
    <div className="stats-grid">
      <StatCard icon={FolderKanban} label="FORENSIC CASES" value={String(demoCases.length).padStart(2, "0")} detail={`${demoCases.filter((item) => item.status !== "Closed").length} active · ${demoCases.filter((item) => item.status === "Closed").length} closed`} tone="teal" />
      <StatCard icon={Files} label="EVIDENCE FILES" value={demoSummary.evidenceCount} detail="Synthetic records across demo cases" tone="blue" />
      <StatCard icon={Plane} label="FLIGHT LOGS" value={demoCases.reduce((sum, item) => sum + item.flightLogs, 0)} detail="Synthetic logs in demo cases" tone="amber" />
      <StatCard icon={ShieldCheck} label="HASH VERIFIED" value={`${demoSummary.verifiedCount} / ${demoSummary.evidenceCount}`} detail={`${demoSummary.reviewCount} simulated items need review`} tone="green" />
    </div>
    <div className="dashboard-grid primary-grid"><TelemetryPanel series={series} setSeries={setSeries} /><MapPanel /></div>
    <div className="dashboard-grid secondary-grid"><EvidencePanel query={query} /><div className="stacked-panels"><ActivityPanel /><EventsPanel /></div><div className="stacked-panels"><EvidenceTypePanel /><SensorPanel /></div></div>
    <div className="dashboard-bottom-note"><ShieldCheck size={14} /><span>SHA-256 is used for integrity verification. It does not encrypt evidence.</span><span className="bottom-spacer" /><span>DEMO CASE · {activeCase.id}</span></div>
  </>;
}

function useCaseTelemetry(caseId) {
  const [state, setState] = useState({ loading: false, data: null, error: "" });
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!caseId) { setState({ loading: false, data: null, error: "" }); return; }
    const controller = new AbortController();
    setState({ loading: true, data: null, error: "" });
    (async () => {
      try {
        const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/telemetry`, { credentials: "same-origin", cache: "no-store", signal: controller.signal });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Telemetry request failed (HTTP ${response.status})`);
        if (!data.series || typeof data.series !== "object") throw new Error("Unexpected telemetry API response.");
        if (!controller.signal.aborted) setState({ loading: false, data, error: "" });
      } catch (error) {
        if (!controller.signal.aborted) setState({ loading: false, data: null, error: error.message || "Unable to load telemetry." });
      }
    })();
    return () => controller.abort();
  }, [caseId, retry]);
  return { ...state, retry: () => setRetry((n) => n + 1) };
}

const FLIGHT_METRICS = [
  { key: "altitude_m", label: "Altitude", unit: "m", group: "ctun" },
  { key: "throttle_output", label: "Throttle output", unit: "raw log value", group: "ctun" },
  { key: "climb_rate_m_s", label: "Climb rate", unit: "m/s", group: "ctun" },
  { key: "roll", label: "Roll", unit: "°", group: "att" },
  { key: "pitch", label: "Pitch", unit: "°", group: "att" },
  { key: "yaw", label: "Yaw", unit: "°", group: "att" },
];
const CHANNEL_NAMES = Array.from({ length: 14 }, (_, index) => `C${index + 1}`);
const TRACE_COLORS = ["#087f83", "#d19342", "#527caa", "#a15f8b", "#667b43", "#bf5a4c"];

function sampledRows(records, maxPoints = 550) {
  if (!Array.isArray(records)) return [];
  const step = Math.max(1, Math.ceil(records.length / maxPoints));
  return records.filter((row, index) => Number.isFinite(row.time_s) && (index % step === 0 || index === records.length - 1));
}

function TelemetryChart({ records, lines, height = 310, stepAfter = false }) {
  const chartRows = useMemo(() => sampledRows(records), [records]);
  const hasValues = chartRows.some((row) => lines.some((line) => Number.isFinite(line.read ? line.read(row) : row[line.key])));
  const normalized = useMemo(() => chartRows.map((row) => {
    const point = { time_s: row.time_s };
    for (const line of lines) point[line.key] = line.read ? line.read(row) : row[line.key];
    return point;
  }), [chartRows, lines]);
  if (!hasValues) return <p style={{ padding: "18px 0", fontSize: 13 }}>No usable measurements are available for this selection.</p>;
  return <div style={{ width: "100%", height }}><ResponsiveContainer width="100%" height="100%"><LineChart data={normalized} margin={{ top: 14, right: 22, left: 0, bottom: 20 }}>
    <CartesianGrid vertical={false} stroke="#e8edf0" strokeDasharray="3 4" />
    <XAxis dataKey="time_s" type="number" domain={["dataMin", "dataMax"]} tickFormatter={(value) => Number(value).toFixed(0)} tick={{ fontSize: 11 }} label={{ value: "Seconds since boot", position: "insideBottom", offset: -10, fontSize: 11 }} />
    <YAxis tick={{ fontSize: 11 }} width={65} domain={["auto", "auto"]} />
    <Tooltip labelFormatter={(value) => `Boot time: ${Number(value).toFixed(3)} s`} formatter={(value, name) => [Number.isFinite(value) ? Number(value).toFixed(4) : "—", name]} />
    {lines.map((line, index) => <Line key={line.key} type={stepAfter ? "stepAfter" : "linear"} dataKey={line.key} name={line.label} stroke={TRACE_COLORS[index % TRACE_COLORS.length]} strokeWidth={1.8} dot={false} connectNulls={false} isAnimationActive={false} />)}
  </LineChart></ResponsiveContainer></div>;
}

function SourceLabel({ source }) {
  return <p style={{ fontSize: 12, marginTop: 10, overflowWrap: "anywhere" }}>Verified source: <b>{source?.filename || "Unavailable"}</b> · Evidence ID <b>{source?.evidence_id ?? "—"}</b> · {source?.count ?? 0} records</p>;
}

function RealTelemetryView({ activeCase, compact = false }) {
  const caseId = activeCase?.case_id;
  const { data, loading, error, retry } = useCaseTelemetry(caseId);
  const [metric, setMetric] = useState("altitude_m");
  const [channelGroup, setChannelGroup] = useState("rcou");
  const [channels, setChannels] = useState(["C1", "C2", "C3", "C4"]);
  const current = FLIGHT_METRICS.find((item) => item.key === metric) || FLIGHT_METRICS[0];
  const source = data?.series?.[current.group];
  const rows = source?.records || [];
  const values = rows.map((row) => row[metric]).filter(Number.isFinite);
  const minimum = values.length ? Math.min(...values).toFixed(3) : "—";
  const maximum = values.length ? Math.max(...values).toFixed(3) : "—";
  const channelsSource = data?.series?.[channelGroup];
  const channelLines = useMemo(() => channels.map((channel) => ({ key: channel, label: channel, read: (row) => row.channels?.[channel] ?? null })), [channels]);
  const vibeLines = useMemo(() => [
    { key: "vibration_x", label: "X" }, { key: "vibration_y", label: "Y" }, { key: "vibration_z", label: "Z" },
  ], []);
  const flightLine = useMemo(() => [{ key: metric, label: `${current.label} (${current.unit})` }], [metric, current]);
  const modeRows = data?.series?.mode?.records || [];
  const modeLines = useMemo(() => [{ key: "mode_num", label: "ModeNum" }], []);
  const modeEvents = modeRows.filter((row, index) => index === 0 || row.mode_num !== modeRows[index - 1].mode_num);
  const vibeRows = data?.series?.vibe?.records || [];
  const clips = vibeRows.map((row) => row.clip).filter(Number.isFinite);
  const maxClip = clips.length ? Math.max(...clips) : null;
  const hasExtended = ["rcou", "vibe", "mode", "rcin"].some((key) => Boolean(data?.series?.[key]));
  return <div style={{ display: "grid", gap: 18 }}>
    <section className="surface" style={{ padding: 20, minWidth: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div><span className="section-eyebrow">VERIFIED AUTOPSY EVIDENCE · REAL TELEMETRY</span><h2 style={{ marginTop: 6 }}>Recorded flight measurements</h2><p style={{ fontSize: 12, marginTop: 7 }}>TimeUS is microseconds since boot, not UTC. Source files are SHA-256 checked by the backend.</p></div>
        <button className="outline-button" type="button" onClick={retry} disabled={!caseId || loading}>Refresh</button>
      </div>
      {!caseId && <p style={{ marginTop: 18 }}>Select an active investigation to load telemetry.</p>}
      {loading && <p style={{ marginTop: 18 }}>Loading and verifying flight telemetry…</p>}
      {error && <div className="api-error-card" style={{ marginTop: 16 }}><AlertTriangle size={17} /><div><b>Telemetry unavailable</b><span>{error}</span></div></div>}
      {data && <>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 16, marginBottom: 18 }}>
          <span className="case-status-chip">Duration: {data.duration_s ?? "—"} s</span>
          <span className="case-status-chip">ATT: {data.series.att?.count ?? 0}</span>
          <span className="case-status-chip">CTUN: {data.series.ctun?.count ?? 0}</span>
          <span className="case-status-chip">GPS: {data.gps_fix_available ? "Fix available" : "NO VALID FIX"}</span>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
          {FLIGHT_METRICS.map((option) => <button key={option.key} type="button" className={metric === option.key ? "primary-button" : "outline-button"} onClick={() => setMetric(option.key)}>{option.label}</button>)}
        </div>
        <div style={{ display: "flex", gap: 18, flexWrap: "wrap", marginBottom: 10, fontSize: 12 }}><span><b>{current.label}</b> ({current.unit})</span><span>Minimum: <b>{minimum}</b></span><span>Maximum: <b>{maximum}</b></span></div>
        <TelemetryChart records={rows} lines={flightLine} height={compact ? 260 : 350} />
        <SourceLabel source={source} />
        {!data.gps_fix_available && <div className="api-error-card" style={{ marginTop: 16 }}><AlertTriangle size={17} /><div><b>GPS route unavailable</b><span>No valid GPS fix was recorded. Zero coordinates will not be plotted as a route.</span></div></div>}
        {Array.isArray(data.warnings) && data.warnings.map((warning, index) => <div key={index} className="inline-error" style={{ marginTop: 10 }}><AlertTriangle size={14} />{warning.filename}: {warning.reason}</div>)}
        <p style={{ fontSize: 11, marginTop: 14 }}>Charts may be downsampled for display. Min/max use all returned samples. No evidence is modified.</p>
      </>}
    </section>
    {data && <>
      <section className="surface" style={{ padding: 20, minWidth: 0 }}>
        <SectionTitle eyebrow="OUTPUTS & PILOT INPUT · VERIFIED CSV" title="Channel comparison" />
        <p style={{ fontSize: 12, margin: "10px 0 14px" }}>Raw recorded channel values. Output channel numbers are not confirmed physical motor identities; input channel numbers are not confirmed stick functions.</p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
          <button type="button" className={channelGroup === "rcou" ? "primary-button" : "outline-button"} onClick={() => setChannelGroup("rcou")}>RCOU · Outputs</button>
          <button type="button" className={channelGroup === "rcin" ? "primary-button" : "outline-button"} onClick={() => setChannelGroup("rcin")}>RCIN · Pilot inputs</button>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          {CHANNEL_NAMES.map((channel) => <button key={channel} type="button" className={channels.includes(channel) ? "primary-button" : "outline-button"} style={{ padding: "6px 10px", fontSize: 12 }} aria-pressed={channels.includes(channel)} onClick={() => setChannels((previous) => previous.includes(channel) ? previous.filter((item) => item !== channel) : [...previous, channel].sort((a, b) => Number(a.slice(1)) - Number(b.slice(1))))}>{channel}</button>)}
        </div>
        {channelsSource ? <TelemetryChart records={channelsSource.records} lines={channelLines} height={compact ? 260 : 330} /> : <p style={{ padding: 12 }}>No verified {channelGroup.toUpperCase()} evidence available for this case.</p>}
        <SourceLabel source={channelsSource} />
      </section>
      <section className="surface" style={{ padding: 20, minWidth: 0 }}>
        <SectionTitle eyebrow="VIBRATION · VERIFIED CSV" title="IMU vibration axes" />
        <p style={{ fontSize: 12, margin: "10px 0 14px" }}>VibeX, VibeY and VibeZ are raw logged vibration measurements. A peak does not by itself establish a collision or fault.</p>
        {data.series.vibe ? <TelemetryChart records={vibeRows} lines={vibeLines} height={compact ? 250 : 320} /> : <p>No verified VIBE evidence available for this case.</p>}
        <p style={{ fontSize: 12, marginTop: 10 }}>Maximum recorded Clip counter: <b>{maxClip ?? "—"}</b> (counter value, not a calculated number of clipping events).</p>
        <SourceLabel source={data.series.vibe} />
      </section>
      <section className="surface" style={{ padding: 20, minWidth: 0 }}>
        <SectionTitle eyebrow="FLIGHT MODE EVENTS · VERIFIED CSV" title="Recorded flight modes" />
        <p style={{ fontSize: 12, margin: "10px 0 14px" }}>Mode numbers and reason codes are shown without guessed flight-mode names. Confirm vehicle firmware before interpreting codes.</p>
        {data.series.mode ? <>
          <TelemetryChart records={modeRows} lines={modeLines} height={compact ? 220 : 260} stepAfter />
          <div className="data-table-wrap" style={{ marginTop: 16 }}><table className="data-table"><thead><tr><th>BOOT TIME (s)</th><th>MODE NUMBER</th><th>REASON CODE</th></tr></thead><tbody>{modeEvents.map((row, index) => <tr key={`${row.time_us}-${index}`}><td>{Number(row.time_s).toFixed(3)}</td><td>{row.mode_num ?? "—"}</td><td>{row.reason_code ?? "—"}</td></tr>)}{!modeEvents.length && <tr><td colSpan="3">No mode events found.</td></tr>}</tbody></table></div>
        </> : <p>No verified MODE evidence available for this case.</p>}
        <SourceLabel source={data.series.mode} />
      </section>
      {!hasExtended && <div className="api-error-card"><AlertTriangle size={16} />Extended telemetry was not returned. Confirm the expanded backend is running and that the CSV files are registered in the case.</div>}
    </>}
  </div>;
}


// Step 71: read-only GPS diagnostics derived solely from hash-verified API records.
function GPSAnalysisPage({ demoMode, activeCase }) {
  const caseId = demoMode ? null : activeCase?.case_id;
  const { data, loading, error, retry } = useCaseTelemetry(caseId);
  const [diagnostic, setDiagnostic] = useState("satellites");
  const gpsSource = data?.series?.gps;
  const records = gpsSource?.records || [];
  const valid = useMemo(() => records.filter((row) =>
    row.gps_valid === true && Number.isFinite(row.latitude) && Number.isFinite(row.longitude) &&
    Math.abs(row.latitude) <= 90 && Math.abs(row.longitude) <= 180 &&
    !(row.latitude === 0 && row.longitude === 0)
  ), [records]);
  const route = useMemo(() => valid.map((row) => [row.latitude, row.longitude]), [valid]);
  const firstFix = valid[0];
  const lastFix = valid[valid.length - 1];
  const statuses = useMemo(() => [...new Set(records.map((row) => row.status).filter(Number.isFinite))].sort((a, b) => a - b), [records]);
  const satelliteValues = records.map((row) => row.satellites).filter(Number.isFinite);
  const hdopValues = records.map((row) => row.hdop).filter(Number.isFinite);
  const diagnostics = [
    { key: "satellites", label: "Satellite count", unit: "satellites" },
    { key: "hdop", label: "HDOP (logged)", unit: "raw logged value" },
    { key: "status", label: "GPS status code", unit: "raw status code" },
  ];
  const selected = diagnostics.find((item) => item.key === diagnostic) || diagnostics[0];
  const diagnosticLines = useMemo(() => [{ key: diagnostic, label: selected.label }], [diagnostic, selected.label]);
  if (demoMode) return <>
    <PageHeading kicker="GPS FORENSICS" title="GPS Flight Map" detail="Select REAL DATA to inspect verified GPS evidence. Demo coordinates are never used for forensic reconstruction." badge="DEMO MODE" context="ISOLATED WORKSPACE" />
    <section className="surface module-preview"><MapPinned size={28} /><h2>GPS evidence requires REAL DATA mode</h2><p>Switch to REAL DATA and select the investigation.</p></section>
  </>;
  return <>
    <PageHeading kicker="GPS FORENSICS" title="GPS Flight Map" detail={`GPS position validity and receiver diagnostics for ${activeCase?.case_number || "the selected case"}.`} badge="MYSQL · LIVE" context="VERIFIED EVIDENCE" />
    <section className="surface" style={{ padding: 20, marginBottom: 18, minWidth: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div><span className="section-eyebrow">GPS.CSV · EVIDENCE-BASED RECONSTRUCTION</span><h2 style={{ marginTop: 6 }}>GPS evidence assessment</h2><p style={{ marginTop: 8, fontSize: 12 }}>TimeUS is seconds since vehicle boot, not UTC. The backend verifies source SHA-256 before returning records.</p></div>
        <button type="button" className="outline-button" onClick={retry} disabled={!caseId || loading}>Refresh GPS evidence</button>
      </div>
      {!caseId && <p style={{ marginTop: 16 }}>Select a real investigation to view GPS evidence.</p>}
      {loading && <p style={{ marginTop: 16 }}>Loading and verifying GPS evidence…</p>}
      {error && <div className="api-error-card" role="alert" style={{ marginTop: 16 }}><AlertTriangle size={17} /><div><b>GPS evidence unavailable</b><span>{error}</span></div></div>}
      {data && <>
        <div className="stats-grid" style={{ marginTop: 18 }}>
          <StatCard icon={MapPinned} label="VALID POSITION FIXES" value={valid.length} detail={`Of ${records.length} GPS samples`} tone="teal" />
          <StatCard icon={Activity} label="GPS STATUS CODES" value={statuses.length ? statuses.join(", ") : "—"} detail="Raw recorded status values" tone="blue" />
          <StatCard icon={Gauge} label="MAX SATELLITES" value={satelliteValues.length ? Math.max(...satelliteValues) : "—"} detail="Maximum recorded NSats" tone="amber" />
          <StatCard icon={Clock3} label="GPS RECORDS" value={gpsSource?.count ?? 0} detail="Parsed from verified source" tone="green" />
        </div>
        <SourceLabel source={gpsSource} />
        {valid.length === 0 ? <div className="api-error-card" style={{ marginTop: 18 }}><AlertTriangle size={19} /><div><b>NO VALID GPS ROUTE</b><span>No valid latitude/longitude fix was recorded in the verified GPS evidence. A route, launch location, landing location, distance, and geographic incident position cannot be reconstructed from this file. No demo or zero coordinates are plotted.</span></div></div> : <div style={{ marginTop: 18 }}>
          <h3 style={{ marginBottom: 10 }}>Recorded GPS positions</h3>
          <div className="map-frame" style={{ height: 390 }}><MapContainer key={`${caseId}-${firstFix.latitude}-${firstFix.longitude}`} center={[firstFix.latitude, firstFix.longitude]} zoom={15} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
            <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {route.length > 1 && <Polyline positions={route} pathOptions={{ color: "#087f83", weight: 3 }} />}
            <CircleMarker center={[firstFix.latitude, firstFix.longitude]} radius={6} pathOptions={{ color: "#fff", weight: 2, fillColor: "#1a9b72", fillOpacity: 1 }}><MapTooltip>First valid GPS point · boot {firstFix.time_s} s</MapTooltip></CircleMarker>
            {route.length > 1 && <CircleMarker center={[lastFix.latitude, lastFix.longitude]} radius={6} pathOptions={{ color: "#fff", weight: 2, fillColor: "#c67835", fillOpacity: 1 }}><MapTooltip>Last valid GPS point · boot {lastFix.time_s} s</MapTooltip></CircleMarker>}
          </MapContainer></div>
          <p style={{ marginTop: 10, fontSize: 12 }}>Map shows only recorded valid coordinates, connected in log order. First and last valid points are not necessarily launch and landing. A line between samples does not prove the exact intervening path.</p>
        </div>}
      </>}
    </section>
    {data && <>
      <section className="surface" style={{ padding: 20, marginBottom: 18, minWidth: 0 }}>
        <SectionTitle eyebrow="RECEIVER DIAGNOSTICS · GPS.CSV" title="GPS signal and fix timeline" />
        <p style={{ margin: "10px 0 14px", fontSize: 12 }}>These plots show logged receiver measurements even when GPS positioning was invalid. HDOP is displayed as recorded, not treated as a verified position accuracy estimate.</p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
          {diagnostics.map((item) => <button type="button" key={item.key} className={diagnostic === item.key ? "primary-button" : "outline-button"} onClick={() => setDiagnostic(item.key)}>{item.label}</button>)}
        </div>
        {records.length ? <TelemetryChart records={records} lines={diagnosticLines} height={320} stepAfter={diagnostic === "status"} /> : <p>No verified GPS records are available to chart.</p>}
        <p style={{ marginTop: 12, fontSize: 12 }}>Diagnostic: <b>{selected.label}</b> ({selected.unit}) · Satellite observations: <b>{satelliteValues.length}</b> · HDOP observations: <b>{hdopValues.length}</b></p>
        <SourceLabel source={gpsSource} />
      </section>
      <section className="surface" style={{ padding: 20, minWidth: 0 }}>
        <SectionTitle eyebrow="GPS FORENSIC FINDINGS" title="Evidence limitations and observations" />
        <div className="data-table-wrap" style={{ marginTop: 14 }}><table className="data-table"><thead><tr><th>CHECK</th><th>RECORDED RESULT</th><th>INTERPRETATION</th></tr></thead><tbody>
          <tr><td>Position validity</td><td>{valid.length} valid / {records.length} total</td><td>{valid.length ? "Valid recorded positions available" : "No defensible geographic route from this evidence"}</td></tr>
          <tr><td>Satellite count</td><td>{satelliteValues.length ? `${Math.min(...satelliteValues)}–${Math.max(...satelliteValues)}` : "Unavailable"}</td><td>Receiver-reported satellite observations</td></tr>
          <tr><td>GPS status</td><td>{statuses.length ? statuses.join(", ") : "Unavailable"}</td><td>Raw status codes; interpretation depends on firmware</td></tr>
          <tr><td>HDOP</td><td>{hdopValues.length ? `${Math.min(...hdopValues).toFixed(2)}–${Math.max(...hdopValues).toFixed(2)}` : "Unavailable"}</td><td>Raw HDOP values; invalid fixes remain invalid</td></tr>
          <tr><td>Time reference</td><td>ArduPilot TimeUS</td><td>Boot-relative, not an absolute date/time</td></tr>
        </tbody></table></div>
        {Array.isArray(data.warnings) && data.warnings.map((warning, index) => <div className="inline-error" key={index} style={{ marginTop: 10 }}><AlertTriangle size={14} />{warning.filename}: {warning.reason}</div>)}
        <p style={{ fontSize: 12, marginTop: 16 }}>Source files remain read-only. The map and charts are investigative visualizations, not proof of unrecorded movement or a collision.</p>
      </section>
    </>}
  </>;
}

function FlightAnalysisPage({ demoMode, activeCase }) {
  if (demoMode) return <><PageHeading kicker="FLIGHT ANALYSIS" title="Flight Log Analysis" detail="Switch to REAL DATA to analyze registered drone telemetry." badge="DEMO MODE" context="ISOLATED WORKSPACE" /><section className="surface module-preview"><Plane size={28} /><h2>Real telemetry is available in REAL DATA mode</h2></section></>;
  return <><PageHeading kicker="FLIGHT ANALYSIS" title="Flight Log Analysis" detail={`Recorded telemetry for ${activeCase?.case_number || "the selected case"}, with traceable evidence sources.`} badge="MYSQL · LIVE" context="REAL CASE DATA" /><RealTelemetryView activeCase={activeCase} /></>;
}

function LiveDashboard({ cases, activeCase, setPage, loading, apiError, apiStatus, query }) {
  const activeCount = cases.filter((item) => item.status !== "Closed").length;
  const reviewCount = cases.filter((item) => item.status === "Review").length;
  const closedCount = cases.filter((item) => item.status === "Closed").length;
  const visibleCases = cases.filter((item) => `${item.case_number} ${item.case_title} ${item.examiner_name || ""}`.toLowerCase().includes(query.toLowerCase()));
  return <>
    <div className="live-banner"><Database size={15} /><div><b>REAL CASE DATA · MYSQL</b><span>{apiError || (apiStatus === "healthy" ? "Connected to the configured MySQL case database." : "Connecting to the MySQL case API…")}</span></div><span className={`api-state ${apiError ? "error" : apiStatus === "healthy" ? "ok" : "pending"}`}><i />{apiError ? "OFFLINE" : apiStatus === "healthy" ? "CONNECTED" : "CONNECTING"}</span></div>
    <div className="page-title-row"><div><div className="page-kicker"><span>INVESTIGATION WORKSPACE</span><span className="kicker-divider">/</span><span>LIVE CASE OVERVIEW</span></div><h1>Forensic dashboard</h1><p>Case totals and verified flight telemetry are loaded from the investigation database and evidence files.</p></div><div className="page-title-actions"><span className="case-status-chip"><i />REAL CASE DATA</span><button className="outline-button" onClick={() => setPage("cases")}><FolderKanban size={15} /> Manage cases</button></div></div>
    {activeCase && <div className="active-case-strip"><div className="case-badge">{String(activeCase.case_id).padStart(2, "0")}</div><div className="active-case-main"><span>ACTIVE INVESTIGATION</span><b>{activeCase.case_title}</b></div><div className="active-case-detail"><span>CASE REFERENCE</span><b>{activeCase.case_number}</b></div><div className="active-case-detail"><span>EXAMINER</span><b>{activeCase.examiner_name || "Unassigned"}</b></div><div className="active-case-detail"><span>OPENED</span><b>{activeCase.investigation_date || "—"}</b></div><button className="case-chevron" aria-label="Open case management" onClick={() => setPage("cases")}><ChevronRight size={18} /></button></div>}
    <div className="stats-grid"><StatCard icon={FolderKanban} label="FORENSIC CASES" value={apiError ? "—" : loading ? "…" : cases.length} detail="Persisted in MySQL" tone="teal" /><StatCard icon={Activity} label="ACTIVE CASES" value={apiError ? "—" : loading ? "…" : activeCount} detail="Open and in progress" tone="blue" /><StatCard icon={FileClock} label="IN REVIEW" value={apiError ? "—" : loading ? "…" : reviewCount} detail="Cases awaiting review" tone="amber" /><StatCard icon={CheckCircle2} label="CLOSED CASES" value={apiError ? "—" : loading ? "…" : closedCount} detail="Completed investigations" tone="green" /></div>
    {apiError && <div className="api-error-card"><AlertTriangle size={17} /><div><b>MySQL API unavailable</b><span>{apiError}</span></div><button className="outline-button" onClick={() => window.dispatchEvent(new CustomEvent("refresh-cases"))}>Retry</button></div>}
    <div style={{ marginTop: 20, marginBottom: 20 }}><RealTelemetryView activeCase={activeCase} compact /></div>
    <div className="live-content-grid"><section className="surface live-case-list"><SectionTitle eyebrow="PERSISTED CASES" title="Recent casework" action="View all cases" onAction={() => setPage("cases")} /><div className="data-table-wrap"><table className="data-table"><thead><tr><th>CASE REFERENCE</th><th>INVESTIGATION</th><th>EXAMINER</th><th>STATUS</th><th>UPDATED</th></tr></thead><tbody>{visibleCases.slice(0, 6).map((item) => <tr key={item.case_id}><td><b className="case-ref">{item.case_number}</b></td><td><b className="case-title-cell">{item.case_title}</b></td><td>{item.examiner_name || "Unassigned"}</td><td><span className={`case-state ${item.status === "Closed" ? "closed" : item.status === "Review" ? "review" : "progress"}`}><i />{item.status}</span></td><td>{new Date(item.updated_at || item.investigation_date).toLocaleDateString()}</td></tr>)}{!loading && !visibleCases.length && <tr><td colSpan="5" className="no-results">{cases.length ? "No cases match this search." : "No cases in the database yet. Create a case to get started."}</td></tr>}</tbody></table></div></section>
      <section className="surface phase-availability"><SectionTitle eyebrow="PHASE 2 · CASEWORK" title="MySQL case store" /><div className="phase-ready"><CheckCircle2 size={16} /><b>Case persistence is available</b></div><p>Cases are saved in your configured MySQL database and are also manageable from the MySQL command line.</p><div className="phase-divider" /><div className="future-items"><span><Clock3 size={14} /> Evidence import <small>Phase 3</small></span><span><Clock3 size={14} /> Flight telemetry <small>Phase 4</small></span><span><Clock3 size={14} /> Maps and metadata <small>Phase 5</small></span></div><button className="primary-button" onClick={() => setPage("cases")}>Open case management <ArrowUpRight size={14} /></button></section>
    </div>
  </>;
}

function CasesPage({ demoMode, query, setActiveCase, setPage, cases, loading, apiError, refreshCases }) {
  return demoMode ? <DemoCasesPage query={query} setActiveCase={setActiveCase} setPage={setPage} /> : <CaseManagementPage query={query} cases={cases} loading={loading} apiError={apiError} refreshCases={refreshCases} setActiveCase={setActiveCase} setPage={setPage} />;
}

function DemoCasesPage({ query, setActiveCase, setPage }) {
  const [filter, setFilter] = useState("All cases");
  const rows = useMemo(() => demoCases.filter((item) => `${item.id} ${item.title} ${item.examiner}`.toLowerCase().includes(query.toLowerCase()) && (filter === "All cases" || item.status === filter)), [query, filter]);
  return <><PageHeading kicker="CASEWORK" title="Case management" detail="Browse isolated training cases. These records are not saved to the live database." badge="DEMO RECORDS" />
    <div className="case-page-toolbar"><label className="field-search"><Search size={15} /><input value={query} readOnly placeholder="Search cases" /></label><label className="filter-select"><ListFilter size={14} /><select value={filter} onChange={(event) => setFilter(event.target.value)}><option>All cases</option><option>In progress</option><option>Review</option><option>Closed</option></select></label><span className="sample-note">Synthetic records · read only</span></div>
    <div className="surface case-table-card"><div className="data-table-wrap"><table className="data-table case-data-table"><thead><tr><th>CASE REFERENCE</th><th>INVESTIGATION</th><th>EXAMINER</th><th>OPENED</th><th>EVIDENCE</th><th>STATUS</th><th></th></tr></thead><tbody>{rows.map((item) => <tr key={item.id}><td><b className="case-ref">{item.id}</b></td><td><b className="case-title-cell">{item.title}</b><small>{item.description}</small></td><td>{item.examiner}</td><td>{new Date(item.date).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}</td><td>{item.evidence} files</td><td><span className={`case-state ${item.status === "Closed" ? "closed" : item.status === "Review" ? "review" : "progress"}`}><i />{item.status}</span></td><td><button className="text-action" onClick={() => { setActiveCase(item); setPage("dashboard"); }}>Open case <ArrowUpRight size={13} /></button></td></tr>)}{!rows.length && <tr><td colSpan="7" className="no-results">No demo cases match these filters.</td></tr>}</tbody></table></div></div>
  </>;
}

function CaseManagementPage({ query, cases, loading, apiError, refreshCases, setActiveCase, setPage }) {
  const dialogRef = useRef(null);
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState({ case_number: "", case_title: "", examiner_name: "", investigation_date: new Date().toISOString().slice(0, 10), status: "Open", description: "" });
  const [filter, setFilter] = useState("All cases");
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState("");
  const rows = useMemo(() => cases.filter((item) => `${item.case_number} ${item.case_title} ${item.examiner_name || ""}`.toLowerCase().includes(query.toLowerCase()) && (filter === "All cases" || item.status === filter)), [cases, query, filter]);

  function beginCreate() {
    setEditingId(null);
    setActionError("");
    setDraft({ case_number: "", case_title: "", examiner_name: "", investigation_date: new Date().toISOString().slice(0, 10), status: "Open", description: "" });
    dialogRef.current?.showModal();
  }

  function beginEdit(item) {
    setEditingId(item.case_id);
    setActionError("");
    setDraft({ case_number: item.case_number, case_title: item.case_title, examiner_name: item.examiner_name || "", investigation_date: item.investigation_date || "", status: item.status, description: item.description || "" });
    dialogRef.current?.showModal();
  }

  async function saveCase(event) {
    event.preventDefault();
    setSaving(true);
    setActionError("");
    try {
      const result = editingId ? await caseApi.update(editingId, draft) : await caseApi.create(draft);
      dialogRef.current?.close();
      await refreshCases();
      setActiveCase(result.case);
    } catch (error) {
      setActionError(error.message);
    } finally {
      setSaving(false);
    }
  }

  async function deleteCase(item) {
    if (!window.confirm(`Delete case ${item.case_number}? This removes its case record from the MySQL database.`)) return;
    setActionError("");
    try {
      await caseApi.remove(item.case_id);
      await refreshCases();
    } catch (error) { setActionError(error.message); }
  }

  return <>
    <PageHeading kicker="CASEWORK" title="Case management" detail="Create and maintain investigation records stored in the configured MySQL database." badge="MYSQL · LIVE" context="LIVE CASE DATA" />
    <div className="case-page-toolbar"><label className="field-search"><Search size={15} /><input value={query} readOnly placeholder="Search cases" /></label><label className="filter-select"><ListFilter size={14} /><select value={filter} onChange={(event) => setFilter(event.target.value)}><option>All cases</option><option>Open</option><option>In Progress</option><option>Review</option><option>Closed</option></select></label><span className="sample-note">{cases.length} persisted cases</span><button className="primary-button new-case-button" onClick={beginCreate}><Plus size={13} /> New case</button></div>
    {apiError && <div className="api-error-card"><AlertTriangle size={16} /><div><b>Could not load cases</b><span>{apiError}</span></div><button className="outline-button" onClick={refreshCases}>Retry</button></div>}
    {actionError && <div className="inline-error"><AlertTriangle size={14} />{actionError}</div>}
    <div className="surface case-table-card"><div className="data-table-wrap"><table className="data-table case-data-table"><thead><tr><th>CASE REFERENCE</th><th>INVESTIGATION</th><th>EXAMINER</th><th>INVESTIGATION DATE</th><th>EVIDENCE</th><th>STATUS</th><th>ACTIONS</th></tr></thead><tbody>{rows.map((item) => <tr key={item.case_id}><td><b className="case-ref">{item.case_number}</b></td><td><b className="case-title-cell">{item.case_title}</b><small>{item.description || "No description"}</small></td><td>{item.examiner_name || "Unassigned"}</td><td>{item.investigation_date || "—"}</td><td>{item.evidence_count ?? 0}</td><td><span className={`case-state ${item.status === "Closed" ? "closed" : item.status === "Review" ? "review" : "progress"}`}><i />{item.status}</span></td><td><div className="case-actions"><button className="text-action" onClick={() => { setActiveCase(item); setPage("dashboard"); }}>Open</button><button className="text-action" onClick={() => beginEdit(item)}>Edit</button><button className="delete-action" onClick={() => deleteCase(item)} aria-label={`Delete ${item.case_number}`}>Delete</button></div></td></tr>)}{loading && <tr><td colSpan="7" className="no-results">Loading cases from MySQL…</td></tr>}{!loading && !apiError && !rows.length && <tr><td colSpan="7" className="no-results">No cases match this search. Create a case to get started.</td></tr>}</tbody></table></div></div>
    <dialog ref={dialogRef} className="case-modal"><form onSubmit={saveCase}>
      <div className="case-modal-heading"><div><span className="phase-label">MYSQL CASE RECORD</span><h2>{editingId ? "Edit investigation" : "Create investigation"}</h2></div><button type="button" className="modal-x" aria-label="Close dialog" onClick={() => dialogRef.current?.close()}>×</button></div>
      <div className="case-form-grid"><label>Case ID / reference<input required maxLength="64" value={draft.case_number} onChange={(event) => setDraft({ ...draft, case_number: event.target.value })} placeholder="e.g. DF-2026-014" /></label><label>Investigation title<input required maxLength="200" value={draft.case_title} onChange={(event) => setDraft({ ...draft, case_title: event.target.value })} placeholder="Case title" /></label><label>Examiner name<input maxLength="150" value={draft.examiner_name} onChange={(event) => setDraft({ ...draft, examiner_name: event.target.value })} placeholder="Assigned examiner" /></label><label>Investigation date<input required type="date" value={draft.investigation_date} onChange={(event) => setDraft({ ...draft, investigation_date: event.target.value })} /></label><label>Case status<select value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}><option>Open</option><option>In Progress</option><option>Review</option><option>Closed</option></select></label><label className="description-field">Incident description<textarea rows="4" value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} placeholder="Describe the reported incident and investigation scope" /></label></div>
      {actionError && <div className="inline-error"><AlertTriangle size={14} />{actionError}</div>}
      <div className="case-modal-footer"><span>Case data is stored in MySQL.</span><div><button type="button" className="outline-button" onClick={() => dialogRef.current?.close()}>Cancel</button><button type="submit" className="primary-button" disabled={saving}>{saving ? "Saving…" : editingId ? "Save changes" : "Create case"}</button></div></div>
    </form></dialog>
  </>;
}

function PageHeading({ kicker, title, detail, badge, context = "DEMONSTRATION WORKSPACE" }) {
  return <div className="page-title-row module-heading"><div><div className="page-kicker"><span>{kicker}</span><span className="kicker-divider">/</span><span>{context}</span></div><h1>{title}</h1><p>{detail}</p></div><span className="demo-readonly-badge"><span />{badge}</span></div>;
}


function formatEvidenceSize(bytes) {
  const value = Number(bytes);
  if (!Number.isFinite(value) || value < 0) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}

function EvidenceExplorerPage({ demoMode, activeCase, query }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("All files");
  const [selected, setSelected] = useState(null);
  const detailsDialogRef = useRef(null);
  const [verification, setVerification] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const verificationRequestRef = useRef(0);

  function selectEvidence(item) {
    verificationRequestRef.current += 1;
    setVerification(null);
    setVerifying(false);
    setSelected(item);
  }

  function closeEvidenceDetails() {
    verificationRequestRef.current += 1;
    setVerification(null);
    setVerifying(false);
    setSelected(null);
  }

  async function verifySelectedEvidence() {
    if (!caseId || !selected || verifying) return;
    const requestId = ++verificationRequestRef.current;
    setVerification(null);
    setVerifying(true);
    try {
      const response = await fetch(
        `/api/cases/${encodeURIComponent(caseId)}/evidence/${encodeURIComponent(selected.evidence_id)}/verify`,
        { credentials: "same-origin", cache: "no-store" }
      );
      const result = await response.json();
      if (requestId !== verificationRequestRef.current) return;
      if (!response.ok) throw new Error(result.error || `Verification failed (HTTP ${response.status}).`);
      if (!["MATCH", "MISMATCH", "FILE MISSING"].includes(result.result)) {
        throw new Error("Unexpected verification response from the server.");
      }
      setVerification({ data: result });
    } catch (verificationError) {
      if (requestId === verificationRequestRef.current) {
        setVerification({ error: verificationError.message || "Unable to verify evidence." });
      }
    } finally {
      if (requestId === verificationRequestRef.current) setVerifying(false);
    }
  }

  useEffect(() => {
    const dialog = detailsDialogRef.current;
    if (!dialog) return;
    if (selected && !dialog.open) dialog.showModal();
    if (!selected && dialog.open) dialog.close();
  }, [selected]);
  const [reloadKey, setReloadKey] = useState(0);
  const caseId = demoMode ? null : activeCase?.case_id;

  useEffect(() => {
    if (demoMode || !caseId) {
      setRecords([]);
      setSelected(null);
      setError("");
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setRecords([]);
    setSelected(null);
    async function loadEvidence() {
      try {
        const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/evidence`, {
          credentials: "same-origin",
          signal: controller.signal,
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || `Evidence request failed (HTTP ${response.status}).`);
        if (!Array.isArray(result.evidence)) throw new Error("Unexpected evidence API response.");
        if (!controller.signal.aborted) setRecords(result.evidence);
      } catch (fetchError) {
        if (!controller.signal.aborted) setError(fetchError.message || "Unable to retrieve evidence.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    loadEvidence();
    return () => controller.abort();
  }, [demoMode, caseId, reloadKey]);

  const types = useMemo(() => [...new Set(records.map((item) => {
    const name = item.filename || "";
    return name.includes(".") ? name.split(".").pop().toUpperCase() : "OTHER";
  }))].sort(), [records]);

  const visible = useMemo(() => records.filter((item) => {
    const filename = item.filename || "";
    const type = filename.includes(".") ? filename.split(".").pop().toUpperCase() : "OTHER";
    const matchesFilter = filter === "All files" || type === filter;
    const searchable = `${filename} ${item.sha256 || ""} ${item.source_path || ""} ${item.verification_status || ""}`.toLowerCase();
    return matchesFilter && searchable.includes(query.toLowerCase());
  }), [records, filter, query]);

  if (demoMode) return <>
    <PageHeading kicker="EVIDENCE" title="Evidence Explorer" detail="Switch to REAL DATA to browse evidence registered in MySQL. Demo records are kept separate from forensic evidence." badge="DEMO MODE" context="ISOLATED WORKSPACE" />
    <section className="surface module-preview"><Files size={28} /><h2>Real evidence is not shown in demo mode</h2><p>Use the DEMO MODE switch in the top bar to access the active investigation's evidence.</p></section>
  </>;

  return <>
    <PageHeading kicker="EVIDENCE REGISTER" title="Evidence Explorer" detail={`Read-only evidence metadata for ${activeCase?.case_number || "the selected case"}. Source files are not modified.`} badge="MYSQL · LIVE" context="REAL CASE DATA" />
    <div className="stats-grid" style={{ marginBottom: 20 }}>
      <StatCard icon={Files} label="REGISTERED FILES" value={loading ? "…" : records.length} detail="Records linked to this case" tone="teal" />
      <StatCard icon={ShieldCheck} label="VERIFIED AT IMPORT" value={loading ? "…" : records.filter((item) => /verified/i.test(item.verification_status || "") && !/unverified|not verified/i.test(item.verification_status || "")).length} detail="Stored verification status" tone="green" />
      <StatCard icon={FileCheck2} label="VISIBLE RESULTS" value={loading ? "…" : visible.length} detail="After search and type filter" tone="blue" />
      <StatCard icon={Database} label="TOTAL FILE SIZE" value={loading ? "…" : formatEvidenceSize(records.reduce((sum, item) => sum + Number(item.file_size || 0), 0))} detail="Sum of registered file sizes" tone="amber" />
    </div>
    {!activeCase && <div className="api-error-card"><AlertTriangle size={17} /><span>Select an investigation from the ACTIVE CASE menu to browse its evidence.</span></div>}
    {error && <div className="api-error-card"><AlertTriangle size={17} /><div><b>Unable to load evidence</b><span>{error}</span></div><button className="outline-button" onClick={() => setReloadKey((key) => key + 1)}>Retry</button></div>}
    <section className="surface" style={{ padding: 20 }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", marginBottom: 18 }}>
        <label className="field-search" style={{ flex: "1 1 260px", maxWidth: 520 }}><Search size={15} /><input value={query} readOnly placeholder="Use global search to find evidence" /></label>
        <label className="filter-select"><ListFilter size={14} /><select value={filter} onChange={(event) => setFilter(event.target.value)}><option>All files</option>{types.map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
        <button className="outline-button" type="button" onClick={() => setReloadKey((key) => key + 1)} disabled={loading || !caseId}>Refresh</button>
      </div>
      <div className="data-table-wrap"><table className="data-table"><thead><tr><th>FILE NAME</th><th>SIZE</th><th>SHA-256</th><th>VERIFICATION</th><th>ACTION</th></tr></thead><tbody>
        {visible.map((item) => <tr key={item.evidence_id}><td><span className="file-kind"><Files size={14} /></span><b style={{ overflowWrap: "anywhere" }}>{item.filename}</b></td><td>{formatEvidenceSize(item.file_size)}</td><td><code style={{ fontSize: 11, overflowWrap: "anywhere" }} title={item.sha256}>{item.sha256 ? `${item.sha256.slice(0, 16)}…` : "—"}</code></td><td><span className="hash-match"><ShieldCheck size={12} />{item.verification_status || "Unknown"}</span></td><td><button type="button" className="text-action" onClick={() => selectEvidence(item)}>Details</button></td></tr>)}
        {loading && <tr><td colSpan="5" className="no-results">Loading evidence from MySQL…</td></tr>}
        {!loading && !error && !visible.length && <tr><td colSpan="5" className="no-results">{records.length ? "No files match the search or filter." : "No evidence registered for this case."}</td></tr>}
      </tbody></table></div>
      <div className="table-foot"><span>{visible.length} of {records.length} evidence records shown · read-only metadata</span></div>
    </section>
    <dialog
      ref={detailsDialogRef}
      onClose={closeEvidenceDetails}
      aria-label="Evidence file details"
      style={{ width: "min(680px, calc(100vw - 32px))", maxHeight: "85vh", overflowY: "auto", border: "1px solid #dbe5e4", borderRadius: 14, padding: 24, boxShadow: "0 20px 70px rgba(0,0,0,.28)" }}
    >
      {selected && <>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
          <div style={{ minWidth: 0 }}>
            <span className="section-eyebrow">EVIDENCE METADATA</span>
            <h2 style={{ marginTop: 8, overflowWrap: "anywhere" }}>{selected.filename}</h2>
          </div>
          <button type="button" className="outline-button" onClick={closeEvidenceDetails}><X size={14} /> Close</button>
        </div>
        <dl style={{ display: "grid", gridTemplateColumns: "minmax(120px, 160px) minmax(0, 1fr)", gap: "12px 18px", marginTop: 18, overflowWrap: "anywhere" }}>
          <dt>Evidence ID</dt><dd>{selected.evidence_id}</dd>
          <dt>Case reference</dt><dd>{activeCase?.case_number}</dd>
          <dt>File size</dt><dd>{formatEvidenceSize(selected.file_size)} ({selected.file_size} bytes)</dd>
          <dt>SHA-256</dt><dd><code style={{ userSelect: "all", overflowWrap: "anywhere" }}>{selected.sha256}</code> <button className="text-action" type="button" onClick={() => navigator.clipboard?.writeText(selected.sha256 || "")}>Copy</button></dd>
          <dt>Verification</dt><dd>{selected.verification_status || "Unknown"}</dd>
          <dt>Autopsy export ID</dt><dd>{selected.autopsy_export_id || "—"}</dd>
          <dt>Autopsy object ID</dt><dd>{selected.autopsy_object_id || "—"}</dd>
          <dt>Original source path</dt><dd>{selected.source_path || "—"}</dd>
          <dt>Imported at</dt><dd>{selected.imported_at || "—"}</dd>
        </dl>
        <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid #e1e9e8" }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <button type="button" className="primary-button" disabled={verifying} onClick={verifySelectedEvidence}>
              <ShieldCheck size={15} /> {verifying ? "Calculating SHA-256…" : "Verify Integrity"}
            </button>
            <span style={{ fontSize: 12 }}>Read-only check against the hash recorded at import.</span>
          </div>
          {verification?.error && <div className="inline-error" role="alert" style={{ marginTop: 14 }}><AlertTriangle size={15} />{verification.error}</div>}
          {verification?.data && <div role="status" style={{ marginTop: 14, padding: 14, border: "1px solid #dbe5e4", borderRadius: 9, overflowWrap: "anywhere" }}>
            <strong style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {verification.data.result === "MATCH" ? <CheckCircle2 size={17} /> : <AlertTriangle size={17} />}
              {verification.data.result === "MATCH" ? "MATCH — Integrity verified" : verification.data.result === "MISMATCH" ? "MISMATCH — Hashes differ" : "FILE MISSING — Source unavailable"}
            </strong>
            <p style={{ marginTop: 9, fontSize: 12 }}>Expected SHA-256 (recorded at import)</p>
            <code style={{ fontSize: 12, overflowWrap: "anywhere" }}>{verification.data.expected_sha256 || "—"}</code>
            <p style={{ marginTop: 9, fontSize: 12 }}>Actual SHA-256 (calculated now)</p>
            <code style={{ fontSize: 12, overflowWrap: "anywhere" }}>{verification.data.actual_sha256 || "Not available"}</code>
            <p style={{ marginTop: 10, fontSize: 12 }}>This result is from the current check only. The stored import hash and evidence file have not been changed.</p>
          </div>}
        </div>
        <p style={{ marginTop: 16, fontSize: 12 }}>The verification status above the button was recorded during import; it is not automatically updated by a new check.</p>
      </>}
    </dialog>
  </>;
}

function IntegrityDashboardPage({ demoMode, activeCase, query }) {
  const caseId = demoMode ? null : activeCase?.case_id;
  const [records, setRecords] = useState([]);
  const [results, setResults] = useState({});
  const [busyId, setBusyId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const requestRef = useRef(0);

  useEffect(() => {
    const generation = ++requestRef.current;
    setRecords([]);
    setResults({});
    setBusyId(null);
    setError("");
    if (!caseId) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true);
    (async () => {
      try {
        const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/evidence`, {
          credentials: "same-origin", cache: "no-store", signal: controller.signal,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
        if (!Array.isArray(data.evidence)) throw new Error("Unexpected evidence API response.");
        if (generation === requestRef.current) setRecords(data.evidence);
      } catch (err) {
        if (!controller.signal.aborted && generation === requestRef.current) setError(err.message || "Unable to load evidence.");
      } finally {
        if (generation === requestRef.current) setLoading(false);
      }
    })();
    return () => { controller.abort(); requestRef.current += 1; };
  }, [caseId, reload]);

  async function verify(item) {
    if (!caseId || busyId !== null) return;
    const generation = requestRef.current;
    setBusyId(item.evidence_id);
    setResults((previous) => ({ ...previous, [item.evidence_id]: { status: "CHECKING" } }));
    try {
      const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/evidence/${encodeURIComponent(item.evidence_id)}/verify`, {
        credentials: "same-origin", cache: "no-store",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      if (!["MATCH", "MISMATCH", "FILE MISSING"].includes(data.result)) throw new Error("Unexpected verification result.");
      if (generation === requestRef.current) setResults((previous) => ({ ...previous, [item.evidence_id]: { status: data.result, data, checkedAt: new Date().toLocaleString() } }));
    } catch (err) {
      if (generation === requestRef.current) setResults((previous) => ({ ...previous, [item.evidence_id]: { status: "ERROR", message: err.message || "Verification failed." } }));
    } finally {
      if (generation === requestRef.current) setBusyId(null);
    }
  }

  const visible = records.filter((item) => `${item.filename || ""} ${item.sha256 || ""}`.toLowerCase().includes(query.toLowerCase()));
  const values = Object.values(results);
  const matches = values.filter((entry) => entry.status === "MATCH").length;
  const problems = values.filter((entry) => ["MISMATCH", "FILE MISSING", "ERROR"].includes(entry.status)).length;
  const checked = values.filter((entry) => ["MATCH", "MISMATCH", "FILE MISSING"].includes(entry.status)).length;

  if (demoMode) return <>
    <PageHeading kicker="EVIDENCE" title="Integrity Verification" detail="Switch to REAL DATA to verify registered forensic evidence." badge="DEMO MODE" context="ISOLATED WORKSPACE" />
    <section className="surface module-preview"><ShieldCheck size={28} /><h2>Real evidence verification is unavailable in demo mode</h2><p>Select REAL DATA to use the live SHA-256 verification API.</p></section>
  </>;

  return <>
    <PageHeading kicker="EVIDENCE INTEGRITY" title="Integrity Verification" detail={`On-demand SHA-256 checks for ${activeCase?.case_number || "the selected case"}. Verification reads the source file without changing its recorded hash.`} badge="MYSQL · LIVE" context="REAL CASE DATA" />
    <div className="stats-grid" style={{ marginBottom: 20 }}>
      <StatCard icon={Files} label="REGISTERED FILES" value={loading ? "…" : records.length} detail="From MySQL evidence register" tone="teal" />
      <StatCard icon={ShieldCheck} label="CHECKED THIS SESSION" value={checked} detail="Results are not saved to MySQL" tone="blue" />
      <StatCard icon={CheckCircle2} label="MATCH" value={matches} detail="Current SHA-256 matches import hash" tone="green" />
      <StatCard icon={AlertTriangle} label="ISSUES" value={problems} detail="Mismatch, missing file, or error" tone="amber" />
    </div>
    {!activeCase && <div className="api-error-card"><AlertTriangle size={16} />Select an active case to view its evidence.</div>}
    {error && <div className="api-error-card"><AlertTriangle size={16} /><span>{error}</span><button type="button" className="outline-button" onClick={() => setReload((n) => n + 1)}>Retry</button></div>}
    <section className="surface" style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
        <div><b>Evidence integrity checks</b><p style={{ fontSize: 12, marginTop: 6 }}>Use Verify to recalculate a file's hash. Unchecked files have not been verified during this page session.</p></div>
        <button type="button" className="outline-button" disabled={loading || busyId !== null || !caseId} onClick={() => setReload((n) => n + 1)}>Refresh evidence list</button>
      </div>
      <div className="data-table-wrap"><table className="data-table"><thead><tr><th>FILE</th><th>IMPORT STATUS</th><th>CURRENT CHECK</th><th>CHECKED AT</th><th>ACTION</th></tr></thead><tbody>
        {visible.map((item) => {
          const result = results[item.evidence_id];
          const status = result?.status || "NOT CHECKED";
          return <tr key={item.evidence_id}>
            <td><b style={{ overflowWrap: "anywhere" }}>{item.filename}</b><small style={{ display: "block", marginTop: 4 }}>ID {item.evidence_id} · {formatEvidenceSize(item.file_size)}</small></td>
            <td>{item.verification_status || "Unknown"}</td>
            <td><b style={{ color: status === "MATCH" ? "#087f83" : ["MISMATCH", "FILE MISSING", "ERROR"].includes(status) ? "#b45309" : "inherit" }}>{status}</b>{result?.message && <small style={{ display: "block", overflowWrap: "anywhere" }}>{result.message}</small>}{result?.data && <details style={{ marginTop: 6 }}><summary style={{ cursor: "pointer", fontSize: 12 }}>Compare hashes</summary><div style={{ fontSize: 11, marginTop: 8, overflowWrap: "anywhere" }}>Expected: <code>{result.data.expected_sha256}</code><div style={{ marginTop: 5 }}>Actual: <code>{result.data.actual_sha256 || "Unavailable"}</code></div></div></details>}</td>
            <td>{result?.checkedAt || "—"}</td>
            <td><button type="button" className="outline-button" disabled={busyId !== null || loading} onClick={() => verify(item)}><ShieldCheck size={14} /> {busyId === item.evidence_id ? "Checking…" : "Verify"}</button></td>
          </tr>;
        })}
        {loading && <tr><td colSpan="5" className="no-results">Loading evidence from MySQL…</td></tr>}
        {!loading && !error && !visible.length && <tr><td colSpan="5" className="no-results">{records.length ? "No evidence matches the search." : "No evidence registered for this case."}</td></tr>}
      </tbody></table></div>
      <div className="table-foot"><span>{visible.length} of {records.length} records · current verification results are temporary and are not an audit trail</span></div>
    </section>
  </>;
}

// Step 73C: verified sensor measurements from the existing read-only telemetry API.
const SENSOR_METRICS = [
  { id: "pressure", label: "Pressure", group: "baro", unit: "Pa (backend field)", lines: [{ key: "pressure_pa", label: "Pressure" }] },
  { id: "baro_altitude", label: "Barometric altitude", group: "baro", unit: "m", lines: [{ key: "altitude_m", label: "Altitude (m)" }] },
  { id: "baro_climb", label: "Barometric climb rate", group: "baro", unit: "m/s", lines: [{ key: "climb_rate_m_s", label: "Climb rate (m/s)" }] },
  { id: "baro_temperature", label: "Barometer temperature", group: "baro", unit: "°C", lines: [{ key: "temperature_c", label: "Temperature (°C)" }] },
  { id: "acceleration", label: "Accelerometer XYZ", group: "imu", unit: "m/s²", lines: [{ key: "accel_x_m_s2", label: "X" }, { key: "accel_y_m_s2", label: "Y" }, { key: "accel_z_m_s2", label: "Z" }] },
  { id: "gyroscope", label: "Gyroscope XYZ", group: "imu", unit: "rad/s", lines: [{ key: "gyro_x_rad_s", label: "X" }, { key: "gyro_y_rad_s", label: "Y" }, { key: "gyro_z_rad_s", label: "Z" }] },
  { id: "imu_temperature", label: "IMU temperature", group: "imu", unit: "°C", lines: [{ key: "temperature_c", label: "Temperature (°C)" }] },
  { id: "vibration", label: "Vibration XYZ", group: "vibe", unit: "raw logged values", lines: [{ key: "vibration_x", label: "X" }, { key: "vibration_y", label: "Y" }, { key: "vibration_z", label: "Z" }] },
  { id: "clipping", label: "Vibration clip counter", group: "vibe", unit: "counter", lines: [{ key: "clip", label: "Clip counter" }] },
];

function SensorAnalysisPage({ demoMode, activeCase }) {
  const caseId = demoMode ? null : activeCase?.case_id;
  const { data, loading, error, retry } = useCaseTelemetry(caseId);
  const [metricId, setMetricId] = useState("acceleration");
  const selected = SENSOR_METRICS.find((item) => item.id === metricId) || SENSOR_METRICS[0];
  const source = data?.series?.[selected.group];
  const records = source?.records || [];
  const lines = useMemo(() => selected.lines, [selected]);
  const summary = selected.lines.map((line) => {
    const values = records.map((row) => row[line.key]).filter(Number.isFinite);
    return { label: line.label, count: values.length, min: values.length ? Math.min(...values) : null, max: values.length ? Math.max(...values) : null };
  });
  const sensorWarnings = (data?.warnings || []).filter((item) => ["BARO.csv", "IMU.csv", "VIBE.csv"].includes(item.filename));
  if (demoMode) return <>
    <PageHeading kicker="SENSOR FORENSICS" title="Sensor Data Analysis" detail="Inspect recorded barometer, inertial, and vibration measurements from registered case evidence." badge="DEMO MODE" context="ISOLATED WORKSPACE" />
    <section className="surface module-preview"><Gauge size={28} /><h2>Sensor evidence requires REAL DATA mode</h2><p>Switch to REAL DATA and select your investigation. No simulated measurements are presented as forensic sensor evidence.</p></section>
  </>;
  return <>
    <PageHeading kicker="SENSOR FORENSICS" title="Sensor Data Analysis" detail={`Recorded sensor measurements for ${activeCase?.case_number || "the selected case"}.`} badge="MYSQL · LIVE" context="VERIFIED EVIDENCE" />
    <section className="surface" style={{ padding: 20, marginBottom: 18, minWidth: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div><span className="section-eyebrow">BARO · IMU · VIBE · READ-ONLY EVIDENCE</span><h2 style={{ marginTop: 6 }}>Sensor evidence overview</h2><p style={{ fontSize: 12, marginTop: 8 }}>Measurements are taken from registered Autopsy CSV evidence. The backend checks SHA-256 before returning each file. TimeUS is boot-relative, not UTC.</p></div>
        <button className="outline-button" type="button" disabled={!caseId || loading} onClick={retry}>Refresh sensors</button>
      </div>
      {!caseId && <p style={{ marginTop: 16 }}>Select an active case to inspect sensor measurements.</p>}
      {loading && <p style={{ marginTop: 16 }}>Loading and verifying sensor evidence…</p>}
      {error && <div className="api-error-card" role="alert" style={{ marginTop: 16 }}><AlertTriangle size={17} /><div><b>Sensor evidence unavailable</b><span>{error}</span></div></div>}
      {data && <>
        <div className="stats-grid" style={{ marginTop: 18 }}>
          <StatCard icon={Gauge} label="BAROMETER SAMPLES" value={data.series.baro?.count ?? 0} detail={data.series.baro ? "Verified BARO.csv" : "No verified BARO source"} tone="teal" />
          <StatCard icon={Activity} label="IMU SAMPLES" value={data.series.imu?.count ?? 0} detail={data.series.imu ? "Verified IMU.csv" : "No verified IMU source"} tone="blue" />
          <StatCard icon={Waypoints} label="VIBRATION SAMPLES" value={data.series.vibe?.count ?? 0} detail={data.series.vibe ? "Verified VIBE.csv" : "No verified VIBE source"} tone="amber" />
          <StatCard icon={Clock3} label="TIME REFERENCE" value="TimeUS" detail="Microseconds since boot" tone="green" />
        </div>
        {sensorWarnings.map((warning, index) => <div className="inline-error" key={`${warning.filename}-${index}`} style={{ marginTop: 12 }}><AlertTriangle size={14} />{warning.filename}: {warning.reason}</div>)}
        {!data.series.baro && !data.series.imu && !data.series.vibe && <div className="api-error-card" style={{ marginTop: 16 }}><AlertTriangle size={17} /><div><b>No verified sensor files available</b><span>Confirm that BARO.csv, IMU.csv and VIBE.csv are registered in the case and that the Step 73B backend is running.</span></div></div>}
      </>}
    </section>
    {data && <>
      <section className="surface" style={{ padding: 20, marginBottom: 18, minWidth: 0 }}>
        <SectionTitle eyebrow="SENSOR TRACES · RECORDED DATA" title="Sensor measurement timeline" />
        <p style={{ margin: "10px 0 14px", fontSize: 12 }}>Select a measurement. Multi-axis traces show X, Y and Z separately. Chart points may be downsampled for display; the range table uses every returned record.</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
          {SENSOR_METRICS.map((item) => <button type="button" key={item.id} className={metricId === item.id ? "primary-button" : "outline-button"} onClick={() => setMetricId(item.id)} aria-pressed={metricId === item.id}>{item.label}</button>)}
        </div>
        <h3 style={{ marginBottom: 8 }}>{selected.label} <span style={{ fontSize: 12, fontWeight: 400 }}>({selected.unit})</span></h3>
        {source ? <TelemetryChart records={records} lines={lines} height={350} /> : <div className="api-error-card"><AlertTriangle size={16} /><div><b>{selected.group.toUpperCase()} evidence unavailable</b><span>No verified records for this source. Check the backend warnings and evidence registration.</span></div></div>}
        <SourceLabel source={source} />
        {source && <div className="data-table-wrap" style={{ marginTop: 18 }}><table className="data-table"><thead><tr><th>MEASUREMENT</th><th>VALID SAMPLES</th><th>MINIMUM</th><th>MAXIMUM</th></tr></thead><tbody>{summary.map((item) => <tr key={item.label}><td>{item.label}</td><td>{item.count}</td><td>{item.min === null ? "—" : item.min.toFixed(4)}</td><td>{item.max === null ? "—" : item.max.toFixed(4)}</td></tr>)}</tbody></table></div>}
      </section>
      <section className="surface" style={{ padding: 20, minWidth: 0 }}>
        <SectionTitle eyebrow="FORENSIC INTERPRETATION" title="Evidence sources and limitations" />
        <div className="data-table-wrap" style={{ marginTop: 14 }}><table className="data-table"><thead><tr><th>FILE</th><th>EVIDENCE ID</th><th>RECORDS</th><th>STATUS</th></tr></thead><tbody>{["baro", "imu", "vibe"].map((key) => { const item = data.series[key]; return <tr key={key}><td>{key.toUpperCase()}.csv</td><td>{item?.evidence_id ?? "—"}</td><td>{item?.count ?? 0}</td><td>{item ? "Loaded after SHA-256 check" : "Not available"}</td></tr>; })}</tbody></table></div>
        <p style={{ fontSize: 12, marginTop: 16 }}>A sudden acceleration, rotation, or vibration change is an observation, not proof of a collision or mechanical failure. Sensor readings are not automatically synchronized to UTC or a geographic location. Sensor hardware models must be independently verified; a BARO log alone does not establish that a BMP280 was installed.</p>
      </section>
    </>}
  </>;
}


// Step 72: external image samples remain separate from registered drone evidence.
function ImageAnalysisPage({ demoMode, activeCase }) {
  const caseId = demoMode ? null : activeCase?.case_id;
  const [items, setItems] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [file, setFile] = useState(null);
  const [notes, setNotes] = useState("");
  const [observationTime, setObservationTime] = useState("");
  const [reload, setReload] = useState(0);
  const selected = items.find((item) => item.sample_id === selectedId) || null;
  useEffect(() => {
    setItems([]); setSelectedId(null); setError("");
    if (!caseId) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true);
    (async () => {
      try {
        const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/image-samples`, { credentials: "same-origin", cache: "no-store", signal: controller.signal });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
        if (!Array.isArray(payload.samples)) throw new Error("Unexpected image gallery response");
        if (!controller.signal.aborted) setItems(payload.samples);
      } catch (err) { if (!controller.signal.aborted) setError(err.message || "Unable to load image samples"); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    })();
    return () => controller.abort();
  }, [caseId, reload]);
  useEffect(() => {
    if (!caseId || !selectedId) { setPreviewUrl(""); return; }
    const controller = new AbortController();
    let objectUrl = "";
    (async () => {
      try {
        const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/image-samples/${encodeURIComponent(selectedId)}/file`, { credentials: "same-origin", cache: "no-store", signal: controller.signal });
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.error || `Image preview failed (HTTP ${response.status})`);
        }
        const blob = await response.blob();
        if (!controller.signal.aborted) { objectUrl = URL.createObjectURL(blob); setPreviewUrl(objectUrl); }
      } catch (err) { if (!controller.signal.aborted) { setPreviewUrl(""); setError(err.message || "Image preview unavailable"); } }
    })();
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [caseId, selectedId]);
  async function uploadImage(event) {
    event.preventDefault();
    if (!caseId || !file || saving) return;
    setSaving(true); setError("");
    try {
      const form = new FormData();
      form.append("image", file);
      form.append("notes", notes);
      if (observationTime) form.append("observation_time", observationTime);
      const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/image-samples`, { method: "POST", credentials: "same-origin", body: form });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || `Upload failed (HTTP ${response.status})`);
      setFile(null); setNotes(""); setObservationTime("");
      event.currentTarget.reset();
      setReload((value) => value + 1);
    } catch (err) { setError(err.message || "Upload failed"); }
    finally { setSaving(false); }
  }
  if (demoMode) return <><PageHeading kicker="IMAGE FORENSICS" title="Image & EXIF Analysis" detail="External image samples are managed only in REAL DATA mode and are not represented as drone camera evidence." badge="DEMO MODE" context="ISOLATED WORKSPACE" /><section className="surface module-preview"><Image size={28}/><h2>Switch to REAL DATA</h2><p>Select your investigation to manage external sample images.</p></section></>;
  return <>
    <PageHeading kicker="IMAGE FORENSICS · STEP 72" title="Image & EXIF Analysis" detail={`External sample image gallery for ${activeCase?.case_number || "the selected case"}. These are not verified drone-captured photographs.`} badge="MYSQL · LIVE" context="EXTERNAL SAMPLE IMAGES" />
    <div className="api-error-card" style={{ marginBottom: 18 }}><AlertTriangle size={18}/><div><b>External samples — not drone-captured evidence</b><span>Files are stored separately from the Autopsy evidence register. Original upload bytes are preserved and checked by SHA-256 when served. Observation time is investigator-assigned, not EXIF capture time.</span></div></div>
    <section className="surface" style={{ padding: 20, marginBottom: 18 }}>
      <SectionTitle eyebrow="SAMPLE IMAGE INTAKE" title="Add JPG or PNG sample" />
      <form onSubmit={uploadImage} style={{ display: "grid", gap: 12, marginTop: 16, maxWidth: 640 }}>
        <label style={{ display: "grid", gap: 6 }}>Image file (20 MB maximum)<input type="file" accept="image/jpeg,image/png,.jpg,.jpeg,.png" required onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
        <label style={{ display: "grid", gap: 6 }}>Investigator-assigned observation time (optional)<input type="datetime-local" value={observationTime} onChange={(event) => setObservationTime(event.target.value)} /></label>
        <label style={{ display: "grid", gap: 6 }}>Investigator notes (optional)<textarea rows={3} maxLength={2000} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Describe the image's source and why it was added; do not claim drone-camera provenance." /></label>
        <button type="submit" className="primary-button" disabled={!file || !caseId || saving}>{saving ? "Saving sample…" : "Add external sample"}</button>
      </form>
    </section>
    {error && <div className="api-error-card" role="alert" style={{ marginBottom: 18 }}><AlertTriangle size={16}/><div><b>Image gallery issue</b><span>{error}</span></div></div>}
    <section className="surface" style={{ padding: 20, marginBottom: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}><SectionTitle eyebrow="CASE-ASSOCIATED SAMPLES" title={`Image gallery (${items.length})`} /><button className="outline-button" disabled={loading || !caseId} onClick={() => setReload((n) => n + 1)}>Refresh</button></div>
      {loading && <p style={{ marginTop: 14 }}>Loading image samples…</p>}
      {!loading && !items.length && <p style={{ marginTop: 14 }}>No external sample images uploaded for this case yet.</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))", gap: 12, marginTop: 16 }}>
        {items.map((item) => <button key={item.sample_id} type="button" className={selectedId === item.sample_id ? "primary-button" : "outline-button"} onClick={() => setSelectedId(item.sample_id)} style={{ display: "grid", textAlign: "left", justifyItems: "start", gap: 8, overflowWrap: "anywhere", whiteSpace: "normal" }}><Image size={20}/><b>{item.filename}</b><small>{item.width} × {item.height} · {formatEvidenceSize(item.byte_size)}</small><small>External sample · View details</small></button>)}
      </div>
    </section>
    {selected && <section className="surface" style={{ padding: 20, minWidth: 0 }}>
      <SectionTitle eyebrow="IMAGE INSPECTION" title={selected.filename} />
      {previewUrl ? <img src={previewUrl} alt={`External sample: ${selected.filename}`} style={{ display: "block", width: "100%", maxWidth: 850, maxHeight: 520, objectFit: "contain", margin: "16px 0", borderRadius: 8, background: "#f1f4f5" }} /> : <p style={{ marginTop: 14 }}>Loading SHA-256-checked image preview…</p>}
      <div className="data-table-wrap"><table className="data-table"><tbody>
        <tr><th>Classification</th><td>{selected.classification}</td></tr>
        <tr><th>Dimensions</th><td>{selected.width} × {selected.height} px</td></tr>
        <tr><th>Format</th><td>{selected.format}</td></tr>
        <tr><th>SHA-256 (uploaded bytes)</th><td><code style={{ overflowWrap: "anywhere" }}>{selected.sha256}</code></td></tr>
        <tr><th>Investigator observation time</th><td>{selected.observation_time || "Not assigned"}</td></tr>
        <tr><th>Camera EXIF time</th><td>{selected.exif?.DateTimeOriginal || selected.exif?.DateTime || "Not present"}</td></tr>
        <tr><th>Camera model</th><td>{selected.exif?.Model || "Not present"}</td></tr>
        <tr><th>Available EXIF fields</th><td><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontSize: 12 }}>{Object.keys(selected.exif || {}).length ? JSON.stringify(selected.exif, null, 2) : "No supported EXIF fields present"}</pre></td></tr>
        <tr><th>Investigator notes</th><td style={{ whiteSpace: "pre-wrap" }}>{selected.notes || "None"}</td></tr>
      </tbody></table></div>
      <p style={{ marginTop: 12, fontSize: 12 }}>Metadata is reported only where present. Image appearance does not establish camera identity, geographic location, or capture time.</p>
    </section>}
  </>;
}


// Step 74A: two independent clock domains. Never infer UTC from ArduPilot TimeUS.
function IncidentTimelinePage({ demoMode, activeCase }) {
  const caseId = demoMode ? null : activeCase?.case_id;
  const { data, loading: telemetryLoading, error: telemetryError, retry } = useCaseTelemetry(caseId);
  const [images, setImages] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [auxErrors, setAuxErrors] = useState([]);
  const [auxLoading, setAuxLoading] = useState(false);
  const [reload, setReload] = useState(0);
  const [domain, setDomain] = useState("boot");
  const [category, setCategory] = useState("all");
  const [searchText, setSearchText] = useState("");
  const [expanded, setExpanded] = useState(null);
  useEffect(() => {
    setImages([]); setEvidence([]); setAuxErrors([]);
    if (!caseId) { setAuxLoading(false); return; }
    const controller = new AbortController();
    setAuxLoading(true);
    const get = async (path) => {
      const response = await fetch(path, { credentials: "same-origin", cache: "no-store", signal: controller.signal });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
      return body;
    };
    Promise.allSettled([
      get(`/api/cases/${encodeURIComponent(caseId)}/evidence`),
      get(`/api/cases/${encodeURIComponent(caseId)}/image-samples`),
    ]).then(([e, i]) => {
      if (controller.signal.aborted) return;
      const errors = [];
      if (e.status === "fulfilled" && Array.isArray(e.value.evidence)) setEvidence(e.value.evidence);
      else errors.push(`Evidence register: ${e.status === "rejected" ? e.reason.message : "Unexpected response"}`);
      if (i.status === "fulfilled" && Array.isArray(i.value.samples)) setImages(i.value.samples);
      else errors.push(`External images: ${i.status === "rejected" ? i.reason.message : "Unexpected response"}`);
      setAuxErrors(errors);
      setAuxLoading(false);
    });
    return () => controller.abort();
  }, [caseId, reload]);

  const bootEvents = useMemo(() => {
    if (!data?.series) return [];
    const events = [];
    const add = (source, row, kind, title, detail) => {
      if (!Number.isFinite(row?.time_s)) return;
      events.push({ id: `${source.evidence_id}-${kind}-${row.time_us ?? row.time_s}-${events.length}`, time: row.time_s,
        kind, title, detail, filename: source.filename, evidenceId: source.evidence_id, clock: "boot" });
    };
    const mode = data.series.mode;
    if (mode?.records) mode.records.forEach((row, index, records) => {
      if (index === 0 || row.mode_num !== records[index - 1].mode_num) {
        add(mode, row, "mode", index === 0 ? "First recorded flight mode" : "Flight mode changed",
          `Raw mode number: ${row.mode_num ?? "unknown"}; reason code: ${row.reason_code ?? "not recorded"}. Mode names are not inferred.`);
      }
    });
    const gps = data.series.gps;
    if (gps?.records?.length) {
      const rows = gps.records;
      add(gps, rows[0], "gps", "GPS recording begins", `Raw GPS status: ${rows[0].status ?? "unknown"}; valid fix: ${rows[0].gps_valid === true ? "yes" : "no"}.`);
      rows.forEach((row, index) => {
        if (index && (row.status !== rows[index - 1].status || row.gps_valid !== rows[index - 1].gps_valid)) {
          add(gps, row, "gps", "GPS receiver state changed", `Status: ${row.status ?? "unknown"}; valid fix: ${row.gps_valid === true ? "yes" : "no"}; satellites: ${row.satellites ?? "unknown"}.`);
        }
      });
      if (rows.length > 1) add(gps, rows[rows.length - 1], "gps", "GPS recording ends", `${rows.length} receiver records; this event does not establish a landing.`);
    }
    for (const key of ["att", "ctun", "baro", "imu", "vibe", "rcin", "rcou"]) {
      const source = data.series[key];
      const rows = source?.records;
      if (!rows?.length) continue;
      const label = key.toUpperCase();
      add(source, rows[0], "sensor", `${label} measurements begin`, `First of ${source.count ?? rows.length} recorded samples.`);
      if (rows.length > 1) add(source, rows[rows.length - 1], "sensor", `${label} measurements end`, `Last recorded sample; not proof of flight termination.`);
    }
    return events.sort((a, b) => a.time - b.time || a.title.localeCompare(b.title));
  }, [data]);

  const absoluteEvents = useMemo(() => {
    const events = [];
    const add = (id, raw, kind, title, detail, filename, evidenceId, basis) => {
      if (!raw) return;
      const ms = Date.parse(raw);
      if (!Number.isFinite(ms)) return;
      events.push({ id, time: ms, rawTime: raw, kind, title, detail, filename, evidenceId, basis, clock: "calendar" });
    };
    evidence.forEach((item) => add(`import-${item.evidence_id}`, item.imported_at, "evidence", "Evidence imported into case",
      `Stored verification status: ${item.verification_status || "unknown"}. Import time is not original capture time.`, item.filename, item.evidence_id, "Evidence register import timestamp"));
    images.forEach((item) => {
      add(`sample-${item.sample_id}`, item.observation_time, "image", "Investigator-assigned image observation",
        `External sample ID ${item.sample_id}. Time is investigator-assigned, not verified capture time.`, item.filename, null, "Investigator observation time (timezone may be unspecified)");
      const exif = item.exif?.DateTimeOriginal || item.exif?.DateTime;
      if (exif) {
        const normalized = String(exif).replace(/^(\d{4}):(\d{2}):(\d{2})/, "$1-$2-$3");
        add(`exif-${item.sample_id}`, normalized, "image", "Image EXIF timestamp (unverified)",
          `External sample ID ${item.sample_id}. EXIF can be edited; timezone and clock accuracy may be unknown.`, item.filename, null, "Embedded EXIF clock (unverified)");
      }
    });
    return events.sort((a, b) => a.time - b.time || a.title.localeCompare(b.title));
  }, [evidence, images]);
  const events = domain === "boot" ? bootEvents : absoluteEvents;
  const visible = events.filter((event) => (category === "all" || event.kind === category) &&
    `${event.title} ${event.detail} ${event.filename}`.toLowerCase().includes(searchText.toLowerCase()));
  const categories = [...new Set(events.map((event) => event.kind))].sort();
  const formatTime = (event) => domain === "boot" ? `${event.time.toFixed(3)} s since boot` : event.rawTime;
  if (demoMode) return <><PageHeading kicker="INCIDENT RECONSTRUCTION" title="Incident Timeline" detail="Real evidence timeline is available only in REAL DATA mode." badge="DEMO MODE" context="ISOLATED WORKSPACE" /><section className="surface module-preview"><Clock3 size={28}/><h2>Switch to REAL DATA</h2><p>Select your investigation to build a timeline from registered evidence and verified telemetry.</p></section></>;
  return <>
    <PageHeading kicker="INCIDENT RECONSTRUCTION · STEP 74A" title="Incident Timeline" detail={`Evidence-linked events for ${activeCase?.case_number || "the selected case"}, without invented dates or incident conclusions.`} badge="MYSQL · LIVE" context="EVIDENCE-BASED TIMELINE" />
    <div className="api-error-card" style={{ marginBottom: 18 }}><AlertTriangle size={17}/><div><b>Two separate time domains</b><span>Flight TimeUS is seconds since vehicle boot, NOT UTC. Evidence import and external image times use separate clocks. These timelines cannot be merged until a documented clock offset is established. An EXIF or investigator-assigned timestamp is not verified capture time.</span></div></div>
    <div className="stats-grid" style={{ marginBottom: 18 }}>
      <StatCard icon={Clock3} label="FLIGHT-LOG EVENTS" value={telemetryLoading ? "…" : bootEvents.length} detail="From SHA-256-checked telemetry" tone="teal" />
      <StatCard icon={Files} label="EVIDENCE IMPORTS" value={auxLoading ? "…" : absoluteEvents.filter(e => e.kind === "evidence").length} detail="Records with parseable import times" tone="blue" />
      <StatCard icon={Image} label="IMAGE TIME ENTRIES" value={auxLoading ? "…" : absoluteEvents.filter(e => e.kind === "image").length} detail="External samples; timestamps unverified" tone="amber" />
      <StatCard icon={MapPinned} label="GPS POSITION" value={data ? (data.gps_fix_available ? "Review fixes" : "NO VALID FIX") : "—"} detail="No invented route or location" tone="green" />
    </div>
    <section className="surface" style={{ padding: 20, marginBottom: 18 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <SectionTitle eyebrow="TIME REFERENCE" title="Timeline event explorer" />
        <button className="outline-button" type="button" disabled={!caseId || telemetryLoading || auxLoading} onClick={() => { retry(); setReload(n => n + 1); }}>Refresh sources</button>
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "16px 0" }}>
        <button type="button" className={domain === "boot" ? "primary-button" : "outline-button"} onClick={() => { setDomain("boot"); setCategory("all"); setExpanded(null); }}>Flight-log clock (boot-relative)</button>
        <button type="button" className={domain === "calendar" ? "primary-button" : "outline-button"} onClick={() => { setDomain("calendar"); setCategory("all"); setExpanded(null); }}>Evidence & image clocks</button>
      </div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
        <label className="field-search" style={{ flex: "1 1 250px" }}><Search size={15}/><input value={searchText} onChange={e => setSearchText(e.target.value)} placeholder="Search timeline events" /></label>
        <label className="filter-select"><ListFilter size={14}/><select value={category} onChange={e => setCategory(e.target.value)}><option value="all">All event types</option>{categories.map(kind => <option key={kind} value={kind}>{kind.toUpperCase()}</option>)}</select></label>
      </div>
      {telemetryLoading && domain === "boot" && <p>Loading and verifying telemetry…</p>}
      {auxLoading && domain === "calendar" && <p>Loading case evidence and external image metadata…</p>}
      {telemetryError && <div className="inline-error"><AlertTriangle size={14}/>Telemetry: {telemetryError}</div>}
      {auxErrors.map((message, index) => <div className="inline-error" key={index}><AlertTriangle size={14}/>{message}</div>)}
      {!data?.gps_fix_available && data && domain === "boot" && <p style={{ fontSize: 12, marginBottom: 12 }}>GPS has no valid position fix. Receiver-state events are not geographic positions.</p>}
      <div className="data-table-wrap"><table className="data-table"><thead><tr><th>RECORDED TIME</th><th>TYPE</th><th>EVENT</th><th>SOURCE</th><th>DETAILS</th></tr></thead><tbody>
        {visible.map(event => <tr key={event.id}><td style={{ whiteSpace: "nowrap" }}><b>{formatTime(event)}</b></td><td>{event.kind.toUpperCase()}</td><td><b>{event.title}</b></td><td><span style={{ overflowWrap: "anywhere" }}>{event.filename}</span>{event.evidenceId != null && <small style={{ display: "block" }}>Evidence ID {event.evidenceId}</small>}</td><td><button type="button" className="text-action" onClick={() => setExpanded(expanded === event.id ? null : event.id)}>{expanded === event.id ? "Hide" : "Inspect"}</button>{expanded === event.id && <div style={{ fontSize: 12, marginTop: 8, maxWidth: 420, whiteSpace: "normal" }}>{event.detail}<p style={{ marginTop: 6 }}>Time basis: {event.basis || "ArduPilot TimeUS (boot-relative)"}</p></div>}</td></tr>)}
        {!visible.length && !telemetryLoading && !auxLoading && <tr><td colSpan="5" className="no-results">No recorded events match the current clock and filters.</td></tr>}
      </tbody></table></div>
      <div className="table-foot"><span>{visible.length} of {events.length} events · ordered within the selected clock only · read-only</span></div>
    </section>
    <section className="surface" style={{ padding: 20 }}><SectionTitle eyebrow="FORENSIC LIMITATIONS" title="Timeline interpretation"/><p style={{ marginTop: 12, fontSize: 13 }}>Mode transitions and receiver-state changes are direct observations of logged values. Sensor start/end entries indicate the first and last available records, not takeoff, landing, impact, or fault. Import times reflect case handling rather than event occurrence. External image observations and EXIF clocks are separate, unverified time sources. No cross-clock correlation, geographic incident location, or collision finding is asserted.</p></section>
  </>;
}


// Step 75B — append-only, case-scoped investigator annotations.
function BookmarksFindingsPage({ demoMode, activeCase }) {
  const caseId = demoMode ? null : activeCase?.case_id;
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [searchText, setSearchText] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [draft, setDraft] = useState({
    category: "Observation", title: "", description: "",
    source_type: "evidence", source_reference: "",
    time_basis: "not_applicable", time_value: ""
  });
  useEffect(() => {
    setFindings([]); setError(""); setNotice("");
    if (!caseId) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true);
    (async () => {
      try {
        const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/findings`, {
          credentials: "same-origin", cache: "no-store", signal: controller.signal
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
        if (!Array.isArray(data.findings)) throw new Error("Unexpected findings response");
        if (!controller.signal.aborted) setFindings(data.findings);
      } catch (err) {
        if (!controller.signal.aborted) setError(err.message || "Unable to load findings");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [caseId, refresh]);

  async function saveFinding(event) {
    event.preventDefault();
    if (!caseId || saving) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/findings`, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...draft, time_value: draft.time_basis === "not_applicable" ? "" : draft.time_value
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      setNotice(`Finding #${data.finding?.finding_id ?? "new"} saved to MySQL.`);
      setDraft({
        category: "Observation", title: "", description: "",
        source_type: "evidence", source_reference: "",
        time_basis: "not_applicable", time_value: ""
      });
      setRefresh((n) => n + 1);
    } catch (err) {
      setError(err.message || "Unable to save finding");
    } finally {
      setSaving(false);
    }
  }

  const visible = findings.filter((item) =>
    (categoryFilter === "All" || item.category === categoryFilter) &&
    `${item.title} ${item.description} ${item.source_reference} ${item.source_type}`
      .toLowerCase().includes(searchText.toLowerCase())
  );
  if (demoMode) return <>
    <PageHeading kicker="INVESTIGATOR NOTES" title="Bookmarks & Findings"
      detail="Switch to REAL DATA to save case-associated findings. No demo findings are written to MySQL."
      badge="DEMO MODE" context="ISOLATED WORKSPACE" />
    <section className="surface module-preview"><Bookmark size={28} />
      <h2>Findings require REAL DATA mode</h2>
      <p>Choose the investigation and return to Bookmarks & Findings.</p>
    </section>
  </>;

  return <>
    <PageHeading kicker="INVESTIGATOR NOTES · STEP 75B" title="Bookmarks & Findings"
      detail={`Append-only investigator annotations for ${activeCase?.case_number || "the selected case"}.`}
      badge="MYSQL · LIVE" context="CASE-ASSOCIATED FINDINGS" />
    <div className="api-error-card" style={{ marginBottom: 18 }}>
      <AlertTriangle size={17} />
      <div><b>Investigator assertions — not automatically verified facts</b>
        <span>Source references are manually entered. Saving a finding does not validate the cited evidence, verify its SHA-256, or establish a timestamp conversion. Existing findings cannot be edited or deleted in this version.</span>
      </div>
    </div>
    <div className="stats-grid" style={{ marginBottom: 18 }}>
      <StatCard icon={Bookmark} label="SAVED ENTRIES" value={loading ? "…" : findings.length} detail="Persisted case annotations" tone="teal" />
      <StatCard icon={Flag} label="FINDINGS" value={findings.filter((x) => x.category === "Finding").length} detail="Investigator conclusions" tone="blue" />
      <StatCard icon={Search} label="QUESTIONS" value={findings.filter((x) => x.category === "Question").length} detail="Open investigative questions" tone="amber" />
      <StatCard icon={Clock3} label="FOLLOW-UPS" value={findings.filter((x) => x.category === "Follow-up").length} detail="Items requiring further work" tone="green" />
    </div>
    <section className="surface" style={{ padding: 20, marginBottom: 18 }}>
      <SectionTitle eyebrow="NEW CASE ANNOTATION" title="Save a bookmark or finding" />
      <form onSubmit={saveFinding} style={{ display: "grid", gap: 13, marginTop: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 12 }}>
          <label style={{ display: "grid", gap: 5 }}>Category
            <select value={draft.category} onChange={(e) => setDraft({ ...draft, category: e.target.value })}>
              {["Observation", "Finding", "Question", "Follow-up"].map((v) => <option key={v}>{v}</option>)}
            </select>
          </label>
          <label style={{ display: "grid", gap: 5 }}>Source type
            <select value={draft.source_type} onChange={(e) => setDraft({ ...draft, source_type: e.target.value })}>
              {["evidence", "telemetry", "image_sample", "timeline", "case"].map((v) => <option key={v} value={v}>{v.replace("_", " ")}</option>)}
            </select>
          </label>
        </div>
        <label style={{ display: "grid", gap: 5 }}>Title
          <input required maxLength={200} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} placeholder="e.g. No valid GPS fix in GPS.csv" />
        </label>
        <label style={{ display: "grid", gap: 5 }}>Source reference (manual; required)
          <input required maxLength={255} value={draft.source_reference} onChange={(e) => setDraft({ ...draft, source_reference: e.target.value })} placeholder="e.g. GPS.csv · Evidence ID 20" />
        </label>
        <label style={{ display: "grid", gap: 5 }}>Description / reasoning
          <textarea required rows={4} maxLength={10000} value={draft.description}
            onChange={(e) => setDraft({ ...draft, description: e.target.value })}
            placeholder="State what the records show, what they do not show, and any uncertainty." />
        </label>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 12 }}>
          <label style={{ display: "grid", gap: 5 }}>Event time basis
            <select value={draft.time_basis} onChange={(e) => setDraft({ ...draft, time_basis: e.target.value, time_value: "" })}>
              <option value="not_applicable">Not applicable / unknown</option>
              <option value="boot_relative">Flight controller boot-relative</option>
              <option value="utc">UTC (documented)</option>
              <option value="local_unspecified">Local time (offset unknown)</option>
            </select>
          </label>
          {draft.time_basis !== "not_applicable" && <label style={{ display: "grid", gap: 5 }}>Recorded time (as documented)
            <input required maxLength={80} value={draft.time_value} onChange={(e) => setDraft({ ...draft, time_value: e.target.value })}
              placeholder={draft.time_basis === "boot_relative" ? "e.g. 14.239 seconds since boot" : "Enter source timestamp with context"} />
          </label>}
        </div>
        <button type="submit" className="primary-button" disabled={!caseId || saving}>
          <Bookmark size={15} />{saving ? "Saving…" : "Save append-only entry"}
        </button>
      </form>
    </section>
    {error && <div className="api-error-card" role="alert" style={{ marginBottom: 16 }}>
      <AlertTriangle size={16} /><span>{error}</span>
    </div>}
    {notice && <p role="status" style={{ marginBottom: 14, fontSize: 12 }}>{notice}</p>}
    <section className="surface" style={{ padding: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <SectionTitle eyebrow="PERSISTED INVESTIGATOR RECORDS" title={`Saved entries (${findings.length})`} />
        <button type="button" className="outline-button" onClick={() => setRefresh((n) => n + 1)} disabled={loading || !caseId}>Refresh</button>
      </div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", margin: "16px 0" }}>
        <label className="field-search" style={{ flex: "1 1 250px" }}><Search size={15} />
          <input value={searchText} onChange={(e) => setSearchText(e.target.value)} placeholder="Search saved findings" />
        </label>
        <label className="filter-select"><ListFilter size={14} />
          <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
            {["All", "Observation", "Finding", "Question", "Follow-up"].map((v) => <option key={v}>{v}</option>)}
          </select>
        </label>
      </div>
      {loading && <p>Loading saved findings…</p>}
      <div className="data-table-wrap"><table className="data-table">
        <thead><tr><th>ID / CATEGORY</th><th>ANNOTATION</th><th>SOURCE REFERENCE</th><th>TIME BASIS</th><th>CREATED (UTC)</th></tr></thead>
        <tbody>
          {visible.map((item) => <tr key={item.finding_id}>
            <td><b>#{item.finding_id}</b><small style={{ display: "block" }}>{item.category}</small></td>
            <td style={{ maxWidth: 430 }}><b style={{ overflowWrap: "anywhere" }}>{item.title}</b>
              <p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", marginTop: 5, fontSize: 12 }}>{item.description}</p></td>
            <td style={{ overflowWrap: "anywhere" }}>{item.source_type}<small style={{ display: "block" }}>{item.source_reference}</small></td>
            <td>{item.time_basis === "boot_relative" ? "Boot-relative" : item.time_basis === "utc" ? "UTC" : item.time_basis === "local_unspecified" ? "Local, offset unknown" : "Not applicable"}
              {item.time_value && <small style={{ display: "block" }}>{item.time_value}</small>}</td>
            <td>{item.created_utc || "—"}</td>
          </tr>)}
          {!loading && !visible.length && <tr><td colSpan={5} className="no-results">{findings.length ? "No matching findings." : "No findings saved for this case."}</td></tr>}
        </tbody>
      </table></div>
      <p style={{ fontSize: 12, marginTop: 14 }}>Entries are case-scoped, append-only investigator notes. Their source references and interpretations require independent review.</p>
    </section>
  </>;
}


// Step 76B: investigator-declared append-only chain of custody.
function ChainOfCustodyPage({ demoMode, activeCase }) {
  const caseId = demoMode ? null : activeCase?.case_id;
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reload, setReload] = useState(0);
  const [filterId, setFilterId] = useState("");
  const [draft, setDraft] = useState({ evidence_id: "", action: "Examined", actor: "", counterparty: "", purpose: "", storage_location: "", event_time: "", integrity_sha256: "", integrity_note: "" });
  useEffect(() => {
    setEvents([]); setError(""); setNotice("");
    if (!caseId) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true);
    fetch(`/api/cases/${encodeURIComponent(caseId)}/custody`, { credentials: "same-origin", cache: "no-store", signal: controller.signal })
      .then(async (r) => { const body = await r.json(); if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`); return body; })
      .then((body) => { if (!controller.signal.aborted) setEvents(Array.isArray(body.events) ? body.events : []); })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message || "Could not load custody history"); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [caseId, reload]);
  async function save(event) {
    event.preventDefault();
    if (!caseId || saving) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/custody`, {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...draft, evidence_id: Number(draft.evidence_id) })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      setNotice(`Custody event #${data.event?.event_id ?? "new"} recorded as an investigator declaration.`);
      setDraft({ evidence_id: "", action: "Examined", actor: "", counterparty: "", purpose: "", storage_location: "", event_time: "", integrity_sha256: "", integrity_note: "" });
      setReload((n) => n + 1);
    } catch (err) { setError(err.message || "Unable to save custody event"); }
    finally { setSaving(false); }
  }
  const filtered = events.filter((e) => !filterId.trim() || String(e.evidence_id) === filterId.trim());
  if (demoMode) return <>
    <PageHeading kicker="EVIDENCE HANDLING" title="Chain of Custody" detail="Select REAL DATA to view and record case-specific custody events." badge="DEMO MODE" />
    <section className="surface" style={{ padding: 24 }}><p>No custody records are created in demonstration mode.</p></section>
  </>;
  return <>
    <PageHeading kicker="EVIDENCE HANDLING · STEP 76B" title="Chain of Custody"
      detail={`Append-only custody journal for ${activeCase?.case_number || "the active case"}.`} badge="MYSQL · LIVE" context="INVESTIGATOR-DECLARED EVENTS" />
    <div className="api-error-card" style={{ marginBottom: 18 }}><AlertTriangle size={18} />
      <div><b>Provenance notice</b><span>These entries are investigator declarations, not automatically authenticated historical events. Event time requires a timezone offset. The server independently records when each entry is submitted. A supplied SHA-256 is a reference only, not proof of a successful integrity check.</span></div>
    </div>
    <div className="stats-grid" style={{ marginBottom: 18 }}>
      <StatCard icon={Link2} label="CUSTODY EVENTS" value={loading ? "…" : events.length} detail="Recorded journal entries" tone="teal" />
      <StatCard icon={Files} label="EVIDENCE ITEMS" value={new Set(events.map((e) => e.evidence_id)).size} detail="With custody history" tone="blue" />
      <StatCard icon={ArrowUpRight} label="TRANSFERS" value={events.filter((e) => e.action === "Transferred").length} detail="Investigator-declared transfers" tone="amber" />
      <StatCard icon={ShieldCheck} label="HASH REFERENCES" value={events.filter((e) => e.integrity_sha256).length} detail="Unverified supplied hash values" tone="green" />
    </div>
    <section className="surface" style={{ padding: 20, marginBottom: 18 }}>
      <SectionTitle eyebrow="NEW CUSTODY ENTRY" title="Record evidence handling" />
      <form onSubmit={save} style={{ display: "grid", gap: 13, marginTop: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
          <label style={{ display: "grid", gap: 5 }}>Registered evidence ID
            <input type="number" min="1" step="1" required value={draft.evidence_id} onChange={(e) => setDraft({ ...draft, evidence_id: e.target.value })} placeholder="e.g. 21" />
          </label>
          <label style={{ display: "grid", gap: 5 }}>Custody action
            <select value={draft.action} onChange={(e) => setDraft({ ...draft, action: e.target.value })}>
              {["Acquired", "Received", "Transferred", "Examined", "Stored", "Released", "Verified", "Other"].map((a) => <option key={a}>{a}</option>)}
            </select>
          </label>
          <label style={{ display: "grid", gap: 5 }}>Actor / investigator
            <input required maxLength={200} value={draft.actor} onChange={(e) => setDraft({ ...draft, actor: e.target.value })} placeholder="Person performing action" />
          </label>
          <label style={{ display: "grid", gap: 5 }}>Other party (optional)
            <input maxLength={200} value={draft.counterparty} onChange={(e) => setDraft({ ...draft, counterparty: e.target.value })} placeholder="Sender / recipient" />
          </label>
          <label style={{ display: "grid", gap: 5 }}>Declared event time — ISO 8601 with timezone
            <input required maxLength={40} value={draft.event_time} onChange={(e) => setDraft({ ...draft, event_time: e.target.value })} placeholder="2026-10-24T00:15:00+05:30" />
          </label>
          <label style={{ display: "grid", gap: 5 }}>Storage location (optional)
            <input maxLength={500} value={draft.storage_location} onChange={(e) => setDraft({ ...draft, storage_location: e.target.value })} placeholder="Evidence locker or working-copy location" />
          </label>
        </div>
        <label style={{ display: "grid", gap: 5 }}>Purpose / handling description
          <textarea required rows={3} maxLength={10000} value={draft.purpose} onChange={(e) => setDraft({ ...draft, purpose: e.target.value })} placeholder="Describe the handling action and its purpose" />
        </label>
        <label style={{ display: "grid", gap: 5 }}>SHA-256 reference (optional; 64 hex characters)
          <input maxLength={64} value={draft.integrity_sha256} onChange={(e) => setDraft({ ...draft, integrity_sha256: e.target.value })} placeholder="Only enter a hash supported by a separate verification record" />
        </label>
        <label style={{ display: "grid", gap: 5 }}>Integrity note (optional)
          <input maxLength={500} value={draft.integrity_note} onChange={(e) => setDraft({ ...draft, integrity_note: e.target.value })} placeholder="Verification context or evidence reference" />
        </label>
        <button className="primary-button" type="submit" disabled={!caseId || saving}><Plus size={15} />{saving ? "Saving…" : "Record append-only custody event"}</button>
      </form>
    </section>
    {error && <div role="alert" className="api-error-card" style={{ marginBottom: 16 }}><AlertTriangle size={16} /><span>{error}</span></div>}
    {notice && <p role="status" style={{ marginBottom: 14 }}>{notice}</p>}
    <section className="surface" style={{ padding: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <SectionTitle eyebrow="CASE JOURNAL" title={`Custody history (${events.length})`} />
        <button type="button" className="outline-button" onClick={() => setReload((n) => n + 1)} disabled={loading}>Refresh history</button>
      </div>
      <label style={{ display: "grid", gap: 5, maxWidth: 280, margin: "16px 0" }}>Filter by evidence ID
        <input type="number" min="1" value={filterId} onChange={(e) => setFilterId(e.target.value)} placeholder="All evidence IDs" />
      </label>
      <div className="data-table-wrap"><table className="data-table">
        <thead><tr><th>EVENT / EVIDENCE</th><th>ACTION / ACTOR</th><th>DECLARED EVENT TIME</th><th>SERVER RECORDED (UTC)</th><th>DETAILS</th></tr></thead>
        <tbody>{filtered.map((item) => <tr key={item.event_id}>
          <td><b>#{item.event_id}</b><small style={{ display: "block" }}>Evidence ID {item.evidence_id}</small></td>
          <td><b>{item.action}</b><small style={{ display: "block" }}>{item.actor}</small></td>
          <td>{item.event_time}</td><td>{item.recorded_utc}</td>
          <td style={{ maxWidth: 440, overflowWrap: "anywhere" }}><span style={{ whiteSpace: "pre-wrap" }}>{item.purpose}</span>
            {item.counterparty && <small style={{ display: "block" }}>Other party: {item.counterparty}</small>}
            {item.storage_location && <small style={{ display: "block" }}>Location: {item.storage_location}</small>}
            {item.integrity_sha256 && <small style={{ display: "block", overflowWrap: "anywhere" }}>SHA-256 reference (not verified): {item.integrity_sha256}</small>}
            {item.integrity_note && <small style={{ display: "block" }}>Integrity note: {item.integrity_note}</small>}
            <small style={{ display: "block" }}>{item.provenance}</small>
          </td>
        </tr>)}
          {!loading && filtered.length === 0 && <tr><td colSpan={5}>No custody entries match this evidence ID.</td></tr>}
        </tbody>
      </table></div>
    </section>
  </>;
}


// Step 77B — forensic report preview and export.
function ForensicReportsPage({ demoMode, activeCase, user }) {
  const caseId = demoMode ? null : activeCase?.case_id;
  const [preview, setPreview] = useState(null);
  const [investigator, setInvestigator] = useState(user?.username || "");
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    setPreview(null); setError(""); setNotice("");
    if (!caseId) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true);
    (async () => {
      try {
        const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/reports/preview`, {
          credentials: "same-origin", cache: "no-store", signal: controller.signal
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || `Preview request failed (HTTP ${response.status})`);
        if (!controller.signal.aborted) setPreview(body);
      } catch (err) {
        if (!controller.signal.aborted) setError(err.message || "Unable to load report preview");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [caseId, refresh]);

  async function generate(format) {
    if (!caseId || !investigator.trim() || generating) return;
    setGenerating(format); setError(""); setNotice("");
    try {
      const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/reports/generate`, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format, investigator: investigator.trim(), summary: summary.trim() })
      });
      if (!response.ok) {
        let message = `Report generation failed (HTTP ${response.status})`;
        try { const body = await response.json(); message = body.error || message; } catch (_) { /* non-JSON server error */ }
        throw new Error(message);
      }
      const blob = await response.blob();
      if (!blob.size) throw new Error("The server returned an empty report");
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `MD-DRONE_case_${caseId}_report.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
      setNotice(`${format.toUpperCase()} report received from the server. Check your browser downloads.`);
    } catch (err) {
      setError(err.message || "Report generation failed");
    } finally {
      setGenerating("");
    }
  }

  if (demoMode) return <>
    <PageHeading kicker="FORENSIC REPORTS · STEP 78" title="Forensic Reports"
      detail="Switch to REAL DATA to generate a report from a registered investigation."
      badge="DEMO MODE" context="NO CASE EXPORT" />
    <section className="surface" style={{ padding: 24 }}><p>Report export is available only in REAL DATA mode.</p></section>
  </>;

  return <>
    <PageHeading kicker="FORENSIC REPORTS · STEP 78" title="Forensic Report Generator"
      detail="Export a focused forensic report with five key evidence items, image exhibits, an evidence diagram, and GPS fix-status graph."
      badge="MYSQL · LIVE" context="SOURCE-ATTRIBUTED REPORT" />
    <div className="api-error-card" style={{ marginBottom: 18 }}>
      <AlertTriangle size={17} /><div><b>Review required before formal use</b>
      <span>The generator compiles registered metadata and investigator declarations. It does not recalculate evidence hashes or independently re-analyze telemetry. GPS.csv has no valid geographic fix; boot-relative flight time is not UTC.</span></div>
    </div>
    {error && <div className="api-error-card" role="alert" style={{ marginBottom: 16 }}><AlertTriangle size={16}/><span>{error}</span></div>}
    {notice && <p role="status" style={{ marginBottom: 14 }}>{notice}</p>}
    <section className="surface" style={{ padding: 20, marginBottom: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <SectionTitle eyebrow="CASE SOURCE SNAPSHOT" title="Report preview" />
        <button type="button" className="outline-button" disabled={loading || !caseId} onClick={() => setRefresh((v) => v + 1)}>Refresh preview</button>
      </div>
      {loading ? <p>Loading report source counts…</p> : preview ? <>
        <p style={{ marginTop: 12 }}><b>{preview.case_reference}</b> · {preview.case_title}</p>
        <div className="stats-grid" style={{ marginTop: 16 }}>
          <StatCard icon={Files} label="KEY EVIDENCE" value={preview.selected_evidence_count ?? 5} detail="Five-item report selection" tone="teal" />
          <StatCard icon={Bookmark} label="SAVED FINDINGS" value={preview.findings_count} detail="Investigator annotations" tone="blue" />
          <StatCard icon={Link2} label="CUSTODY EVENTS" value={preview.custody_count} detail="Investigator-declared history" tone="amber" />
          <StatCard icon={Image} label="IMAGE SAMPLES" value={preview.image_sample_count} detail="External samples" tone="green" />
        </div>
        <p style={{ marginTop: 16, fontSize: 12 }}><b>Evidence source:</b> {preview.evidence_note}</p>
        <p style={{ fontSize: 12 }}><b>Limitations:</b> {preview.limitations}</p>
      </> : <p style={{ marginTop: 12 }}>No report preview available. Confirm the backend route is installed and the case is selected.</p>}
    </section>
    <section className="surface" style={{ padding: 20 }}>
      <SectionTitle eyebrow="GENERATE REPORT" title="Investigator details and export" />
      <div style={{ display: "grid", gap: 14, marginTop: 16 }}>
        <label style={{ display: "grid", gap: 6 }}>Investigator name (required)
          <input value={investigator} maxLength={200} onChange={(e) => setInvestigator(e.target.value)} placeholder="Investigator responsible for report" />
        </label>
        <label style={{ display: "grid", gap: 6 }}>Executive summary (investigator-provided; optional)
          <textarea rows={6} maxLength={5000} value={summary} onChange={(e) => setSummary(e.target.value)}
            placeholder="Summarize only evidence-supported observations. Distinguish confirmed records from interpretations." />
        </label>
        <p style={{ fontSize: 12 }}>The exported report includes only five key inventory items, their available specifications, a five-item diagram, image samples and GPS fix-status visualization. No geographic path is invented. Investigator review is required.</p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button type="button" className="primary-button" disabled={!preview || !investigator.trim() || !!generating}
            onClick={() => generate("pdf")}><FileBarChart size={16}/>{generating === "pdf" ? "Generating PDF…" : "Generate PDF"}</button>
          <button type="button" className="outline-button" disabled={!preview || !investigator.trim() || !!generating}
            onClick={() => generate("docx")}><FileCheck2 size={16}/>{generating === "docx" ? "Generating DOCX…" : "Generate DOCX"}</button>
        </div>
      </div>
    </section>
  </>;
}

function ModulePage({ page, setPage }) {
  const [title, phase, description] = phaseInfo[page];
  const selected = navigation.find((item) => item.id === page);
  const Icon = selected.icon;
  return <><PageHeading kicker={selected.group || "INVESTIGATION TOOLS"} title={title} detail="This module is scheduled for a later implementation phase. No case or evidence data is displayed here." badge="ROADMAP" context="IMPLEMENTATION ROADMAP" />
    <section className="surface module-preview"><div className="module-preview-icon"><Icon size={22} /></div><span className="phase-label">IMPLEMENTATION ROADMAP · {phase.toUpperCase()}</span><h2>{title}</h2><p>{description}</p><div className="module-preview-rule" /><div className="module-preview-meta"><span><CheckCircle2 size={15} /> Sidebar and route are active</span><span><Clock3 size={15} /> Data operations are planned for a later phase</span></div><button className="primary-button" onClick={() => setPage("dashboard")}>Back to dashboard <ArrowUpRight size={14} /></button></section>
  </>;
}

export default function App() {
  const [authLoading, setAuthLoading] = useState(true);
  const [authUser, setAuthUser] = useState(null);
  const [authError, setAuthError] = useState("");
  const [authPage, setAuthPage] = useState("login");
  const [page, setPage] = useState("dashboard");
  const [demoMode, setDemoMode] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeCase, setActiveCase] = useState(demoCases[0]);
  const [realCases, setRealCases] = useState([]);
  const [activeRealCaseId, setActiveRealCaseId] = useState(null);
  const [realLoading, setRealLoading] = useState(false);
  const [realError, setRealError] = useState("");
  const [apiStatus, setApiStatus] = useState("unknown");
  const [search, setSearch] = useState("");
  const [series, setSeries] = useState("altitude");

  useEffect(() => {
    let current = true;
    authApi.session()
      .then(({ user }) => { if (current) setAuthUser(user); })
      .catch((error) => { if (current) setAuthError(error.message); })
      .finally(() => { if (current) setAuthLoading(false); });
    return () => { current = false; };
  }, []);

  async function signIn(credentials) {
    const result = await authApi.login(credentials);
    setAuthUser(result.user);
    setAuthError("");
  }

  async function register(credentials) {
    const result = await authApi.register(credentials);
    setAuthUser(result.user);
    setAuthError("");
  }

  async function signOut() {
    try { await authApi.logout(); } catch { /* Local session state is cleared even if the API is offline. */ } finally {
      setAuthUser(null);
      setRealCases([]);
      setActiveRealCaseId(null);
      setPage("dashboard");
    }
  }

  const refreshRealCases = useCallback(async () => {
    setRealLoading(true);
    setRealError("");
    try {
      const [health, result] = await Promise.all([caseApi.health(), caseApi.list()]);
      setApiStatus(health.status);
      setRealCases(result.cases || []);
      setActiveRealCaseId((current) => current || result.cases?.[0]?.case_id || null);
    } catch (error) {
      setApiStatus("offline");
      setRealError(error.message);
    } finally {
      setRealLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!demoMode) refreshRealCases();
  }, [demoMode, refreshRealCases]);

  useEffect(() => {
    const refresh = () => refreshRealCases();
    window.addEventListener("refresh-cases", refresh);
    return () => window.removeEventListener("refresh-cases", refresh);
  }, [refreshRealCases]);

  useEffect(() => {
    const navigate = (event) => setPage(event.detail);
    const searchShortcut = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        document.querySelector("#global-search-input")?.focus();
      }
    };
    window.addEventListener("navigate", navigate);
    window.addEventListener("keydown", searchShortcut);
    return () => {
      window.removeEventListener("navigate", navigate);
      window.removeEventListener("keydown", searchShortcut);
    };
  }, []);

  const realCase = realCases.find((item) => item.case_id === activeRealCaseId) || realCases[0] || null;
  const headerCases = demoMode ? demoCases : realCases;
  const headerActiveCase = demoMode ? activeCase : realCase;
  function selectHeaderCase(value) {
    if (demoMode) {
      const item = demoCases.find((entry) => entry.id === value);
      if (item) setActiveCase(item);
    } else {
      setActiveRealCaseId(Number(value));
    }
  }

  if (authLoading) return <div className="auth-loading">VERIFYING EXAMINER SESSION…</div>;
  if (!authUser) return <LoginPage mode={authPage} onModeChange={(mode) => { setAuthPage(mode); setAuthError(""); }} onLogin={signIn} onRegister={register} initialError={authError} />;

  return <div className="application">
      <Sidebar page={page} setPage={setPage} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} demoMode={demoMode} apiStatus={apiStatus} user={authUser} onLogout={signOut} />
    <div className="workspace">
      <Header activeCase={headerActiveCase} setActiveCase={selectHeaderCase} cases={headerCases} demoMode={demoMode} setDemoMode={setDemoMode} setMobileOpen={setMobileOpen} search={search} setSearch={setSearch} page={page} user={authUser} />
      <main className="page-content">
        {page === "dashboard" ? <Dashboard demoMode={demoMode} activeCase={activeCase} setPage={setPage} query={search} series={series} setSeries={setSeries} setDemoMode={setDemoMode} realCases={realCases} realCase={realCase} loading={realLoading} apiError={realError} apiStatus={apiStatus} /> : page === "cases" ? <CasesPage demoMode={demoMode} query={search} setActiveCase={demoMode ? setActiveCase : (item) => setActiveRealCaseId(item.case_id)} setPage={setPage} cases={realCases} loading={realLoading} apiError={realError} refreshCases={refreshRealCases} /> : page === "acquisition" ? <EvidenceAcquisition /> : page === "explorer" ? <EvidenceExplorerPage demoMode={demoMode} activeCase={realCase} query={search} /> : page === "integrity" ? <IntegrityDashboardPage demoMode={demoMode} activeCase={realCase} query={search} /> : page === "flight" ? <FlightAnalysisPage demoMode={demoMode} activeCase={realCase} /> : page === "gps" ? <GPSAnalysisPage demoMode={demoMode} activeCase={realCase} /> : page === "sensors" ? <SensorAnalysisPage demoMode={demoMode} activeCase={realCase} /> : page === "image" ? <ImageAnalysisPage demoMode={demoMode} activeCase={realCase} /> : page === "timeline" ? <IncidentTimelinePage demoMode={demoMode} activeCase={realCase} /> : page === "bookmarks" ? <BookmarksFindingsPage demoMode={demoMode} activeCase={realCase} /> : page === "custody" ? <ChainOfCustodyPage demoMode={demoMode} activeCase={realCase} /> : page === "reports" ? <ForensicReportsPage demoMode={demoMode} activeCase={realCase} user={authUser} /> : <ModulePage page={page} setPage={setPage} />}
      </main>
      <footer className="app-footer"><span>DRONE FORENSICS & DIGITAL INCIDENT INVESTIGATION SYSTEM</span><span>LOCAL INSTANCE <i /> PHASE 2</span></footer>
    </div>
  </div>;
}

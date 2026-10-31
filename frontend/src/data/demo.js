// Synthetic data for the isolated Phase 1 demonstration dashboard.
// These records are never sent to or stored by the Flask backend.
export const demoCases = [
  {
    id: "DEMO-0417",
    title: "North Ridge perimeter review",
    examiner: "M. Chen",
    date: "2026-10-21",
    status: "In progress",
    evidence: 12,
    flightLogs: 4,
    description: "Synthetic training case for validating the investigation workspace.",
  },
  {
    id: "DEMO-0392",
    title: "Harbor facility overflight",
    examiner: "A. Patel",
    date: "2026-10-18",
    status: "Review",
    evidence: 8,
    flightLogs: 2,
    description: "Synthetic training case. No real aircraft or incident data is represented.",
  },
  {
    id: "DEMO-0368",
    title: "Test range telemetry audit",
    examiner: "J. Rivera",
    date: "2026-10-11",
    status: "Closed",
    evidence: 16,
    flightLogs: 2,
    description: "Synthetic training case used to demonstrate closed-case review.",
  },
];

export const demoSummary = {
  evidenceCount: 36,
  verifiedCount: 34,
  reviewCount: 2,
  evidenceTypes: [
    { type: "Flight logs", count: 8, color: "#087f83" },
    { type: "Images", count: 14, color: "#6c91b4" },
    { type: "Sensor data", count: 9, color: "#d6a34f" },
    { type: "Other files", count: 5, color: "#9ba9a5" },
  ],
};

export const demoTelemetry = [
  { time: "09:14", altitude: 8, speed: 0, heading: 92 },
  { time: "09:16", altitude: 24, speed: 5, heading: 96 },
  { time: "09:18", altitude: 42, speed: 9, heading: 102 },
  { time: "09:20", altitude: 58, speed: 13, heading: 108 },
  { time: "09:22", altitude: 67, speed: 16, heading: 112 },
  { time: "09:24", altitude: 63, speed: 12, heading: 120 },
  { time: "09:26", altitude: 74, speed: 18, heading: 126 },
  { time: "09:28", altitude: 82, speed: 21, heading: 132 },
  { time: "09:30", altitude: 77, speed: 15, heading: 138 },
  { time: "09:32", altitude: 61, speed: 10, heading: 145 },
  { time: "09:34", altitude: 33, speed: 7, heading: 151 },
  { time: "09:36", altitude: 4, speed: 0, heading: 158 },
];

export const demoRoute = [
  [17.4120, 78.4370], [17.4125, 78.4384], [17.4134, 78.4391],
  [17.4142, 78.4406], [17.4150, 78.4411], [17.4162, 78.4422],
  [17.4171, 78.4438], [17.4165, 78.4454], [17.4154, 78.4462],
  [17.4140, 78.4457], [17.4130, 78.4441], [17.4120, 78.4370],
];

export const demoEvents = [
  { time: "09:14:08", label: "Armed", detail: "Synthetic flight session started", level: "normal" },
  { time: "09:20:42", label: "Mode change", detail: "GUIDED → AUTO", level: "normal" },
  { time: "09:27:16", label: "Speed review", detail: "Demo threshold observation · 21 m/s", level: "review" },
  { time: "09:36:03", label: "Disarmed", detail: "Synthetic flight session ended", level: "normal" },
];

export const demoEvidence = [
  { name: "flight_0417.csv", type: "Flight log", size: "248 KB", hash: "MATCH", time: "09:41:22" },
  { name: "frame_0021.jpg", type: "Image", size: "3.8 MB", hash: "MATCH", time: "09:42:05" },
  { name: "bmp280_readings.csv", type: "Sensor data", size: "64 KB", hash: "MATCH", time: "09:43:11" },
  { name: "autopsy_manifest.json", type: "Manifest", size: "4 KB", hash: "MATCH", time: "09:43:11" },
];

export const demoSensor = [
  { time: "09:14", temp: 24.2, pressure: 1008.2 },
  { time: "09:18", temp: 24.4, pressure: 1008.0 },
  { time: "09:22", temp: 24.6, pressure: 1007.8 },
  { time: "09:26", temp: 24.8, pressure: 1007.6 },
  { time: "09:30", temp: 24.9, pressure: 1007.4 },
  { time: "09:34", temp: 25.1, pressure: 1007.2 },
  { time: "09:38", temp: 25.0, pressure: 1007.3 },
];

export const demoActivity = [
  { icon: "file", title: "Flight log imported", meta: "DEMO-0417 · 09:41", tint: "teal" },
  { icon: "shield", title: "SHA-256 verified", meta: "flight_0417.csv · 09:42", tint: "green" },
  { icon: "image", title: "Image evidence added", meta: "DEMO-0417 · 09:42", tint: "blue" },
  { icon: "flag", title: "Finding bookmarked", meta: "Speed review · 09:44", tint: "amber" },
];

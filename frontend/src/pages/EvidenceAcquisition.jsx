import { useRef, useState } from "react";
import { CheckCircle2, Files, FileUp, ShieldCheck, Upload, X } from "lucide-react";

const MAX_FILE_SIZE = 1024 * 1024 * 1024;

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function EvidenceAcquisition() {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [result, setResult] = useState(null);

  function chooseFile(event) {
    const selected = event.target.files?.[0] || null;
    setFile(selected);
    setError("");
    setNotice("");
    setResult(null);
    if (selected && !selected.name.toLowerCase().endsWith(".bin")) {
      setError("Select an ArduPilot .BIN flight log.");
      setFile(null);
    } else if (selected && selected.size > MAX_FILE_SIZE) {
      setError("The selected file exceeds the 1 GB upload limit.");
      setFile(null);
    }
  }

  async function convert() {
    if (!file || busy) return;
    setError("");
    setNotice("");
    setResult(null);
    setBusy(true);

    try {
      // Browsers do not expose the original file's absolute path. Ask the examiner
      // to grant access to its containing directory before writing the result.
      let destination = null;
      if (window.showDirectoryPicker) {
        setNotice("Choose the folder containing your BIN file. The converted files will be saved in a new folder beside it.");
        destination = await window.showDirectoryPicker({ mode: "readwrite" });
        setNotice("Folder selected. Uploading the BIN for conversion…");
      } else {
        setNotice("Converting BIN. You can download the generated files individually when conversion completes.");
      }

      const form = new FormData();
      form.append("file", file, file.name);
      const response = await fetch("/api/flight-logs/convert-bin", {
        method: "POST",
        body: form,
        credentials: "same-origin",
      });

      const contentType = (response.headers.get("content-type") || "").toLowerCase();
      if (response.ok && !contentType.includes("application/json")) {
        if (contentType.includes("application/zip") || contentType.includes("application/octet-stream")) {
          throw new Error("Flask is still using the older ZIP converter. Stop all Flask processes on port 5001 and restart `python -m backend.mysql_app`, then refresh this page.");
        }
        throw new Error(`The conversion API returned ${contentType || "an unexpected response"}. Restart Flask and try again.`);
      }
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || `Conversion failed (${response.status}).`);
      }

      const converted = await response.json();
      const outputFolderName = `${file.name.replace(/\.bin$/i, "")}_converted_${new Date().toISOString().replace(/[:.]/g, "-")}`;
      const summary = {
        sha256: converted.source_sha256,
        totalRecords: converted.total_records,
        fileCount: converted.files.length,
        counts: converted.records_by_type,
        files: converted.files,
        conversionId: converted.conversion_id,
        outputFolderName,
        savedBesideSource: false,
      };
      setResult(summary);

      if (destination) {
        const outputFolder = await destination.getDirectoryHandle(outputFolderName, { create: true });
        for (let index = 0; index < converted.files.length; index += 1) {
          const output = converted.files[index];
          setNotice(`Writing converted files: ${index + 1} of ${converted.files.length}…`);
          const fileResponse = await fetch(output.url, { credentials: "same-origin" });
          if (!fileResponse.ok) throw new Error(`Could not retrieve ${output.name} (${fileResponse.status}).`);
          const outputFile = await outputFolder.getFileHandle(output.name, { create: true });
          const writer = await outputFile.createWritable();
          await writer.write(await fileResponse.blob());
          await writer.close();
        }
        await fetch(`/api/flight-logs/conversions/${converted.conversion_id}`, { method: "DELETE", credentials: "same-origin" });
        setResult({ ...summary, savedBesideSource: true });
        setNotice(`${converted.files.length} converted files were saved directly into “${destination.name}/${outputFolderName}”. The original BIN was not modified.`);
      } else {
        setNotice("Conversion complete. Use the output links below to download the files individually.");
      }
    } catch (conversionError) {
      if (conversionError.name === "AbortError") {
        setNotice("Folder selection was cancelled, so conversion did not start. Click the button again and choose the folder containing the BIN file.");
      } else {
        setNotice("");
        setError(conversionError.message || "Could not convert this BIN file.");
      }
    } finally {
      setBusy(false);
    }
  }

  return <>
    <div className="page-title-row module-heading">
      <div><div className="page-kicker"><span>EVIDENCE</span><span className="kicker-divider">/</span><span>ACQUISITION</span></div><h1>Evidence acquisition</h1><p>Import an ArduPilot DataFlash BIN and run the project’s Python converter.</p></div>
      <span className="demo-readonly-badge"><span />LOCAL CONVERSION</span>
    </div>

    <div className="acquisition-grid">
      <section className="surface acquisition-card">
        <div className="acquisition-card-heading"><span className="acquisition-icon"><FileUp size={19} /></span><div><span className="phase-label">PYTHON CONVERTER · PYMAVLINK</span><h2>Convert a flight log</h2></div></div>
        <p className="acquisition-description">Select a .BIN file. The server runs <code>bin_file_converter.py</code> and saves each generated CSV, TXT, JSONL, and hash summary file separately.</p>

        <input ref={inputRef} className="acquisition-file-input" type="file" accept=".bin,application/octet-stream" onChange={chooseFile} />
        {!file ? <button className="acquisition-dropzone" type="button" onClick={() => inputRef.current?.click()}>
          <span className="dropzone-icon"><Upload size={20} /></span><b>Add BIN file</b><span>Choose a Pixhawk / ArduPilot .BIN flight log</span><small>Maximum file size: 1 GB</small>
        </button> : <div className="acquisition-selected-file"><span className="selected-file-icon"><Files size={18} /></span><div><b>{file.name}</b><small>{formatBytes(file.size)} · original remains unchanged</small></div><button type="button" aria-label="Remove selected BIN" onClick={() => { setFile(null); if (inputRef.current) inputRef.current.value = ""; }}><X size={16} /></button></div>}

        {error && <div className="acquisition-message error" role="alert">{error}</div>}
        {notice && <div className="acquisition-message success" role="status"><CheckCircle2 size={16} /><span>{notice}</span></div>}
        <div className="acquisition-actions"><button type="button" className="primary-button acquisition-submit" onClick={convert} disabled={!file || busy}>{busy ? "Converting BIN…" : "Convert and save beside BIN"}<span>→</span></button><span>Original BIN is never modified.</span></div>
      </section>

      <aside className="surface acquisition-info">
        <div className="section-title"><div><span className="phase-label">CONVERSION OUTPUT</span><h2>What you’ll receive</h2></div></div>
        <ul className="conversion-files"><li><b>One CSV per message type</b><span>For example, GPS, ATT, MODE, and other message types present in the log.</span></li><li><b>all_flight_logs.txt</b><span>Readable records from the full flight log.</span></li><li><b>all_flight_logs.jsonl</b><span>JSON Lines records for downstream analysis.</span></li><li><b>forensic_summary.json</b><span>Source SHA-256, extraction time, record counts, and output hashes.</span></li></ul>
        <div className="acquisition-integrity"><ShieldCheck size={17} /><span>The original file is uploaded to a temporary server workspace for conversion and is not altered. On Edge, choose the folder containing the BIN and each output is saved directly into a new subfolder beside it.</span></div>
      </aside>
    </div>

    {result && <section className="surface conversion-result">
      <div className="section-title"><div><span className="phase-label">CONVERSION COMPLETE</span><h2>Flight log summary</h2></div><span className="conversion-check"><CheckCircle2 size={16} /> COMPLETE</span></div>
      <div className="conversion-stats"><div><small>RECORDS</small><b>{result.totalRecords.toLocaleString()}</b></div><div><small>OUTPUT FILES</small><b>{result.fileCount}</b></div><div className="conversion-hash"><small>ORIGINAL SHA-256</small><code>{result.sha256 || "Unavailable"}</code></div></div>
      {Object.keys(result.counts).length > 0 && <div className="record-type-list">{Object.entries(result.counts).sort((a, b) => a[0].localeCompare(b[0])).map(([type, count]) => <span key={type}><b>{type}</b>{count.toLocaleString()}</span>)}</div>}
      {!result.savedBesideSource && <div className="converted-file-links"><span>OUTPUT FILES · SELECT TO DOWNLOAD</span>{result.files.map((output) => <a key={output.name} href={output.url} download={output.name}>{output.name}<small>{formatBytes(output.size)}</small></a>)}</div>}
    </section>}
  </>;
}

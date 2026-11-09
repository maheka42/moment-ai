import { useState } from "react";
import type { ReactNode } from "react";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

type Mode = "corporate" | "student";
type Language = "en-IN" | "hi-IN" | "te-IN" | "ta-IN" | "kn-IN" | "ml-IN" | "mr-IN" | "bn-IN" | "gu-IN" | "pa-IN";

const voiceByLanguage: Record<Language, string> = {
  "en-IN": "Kaveri", "hi-IN": "Nalini", "te-IN": "Suhana",
  "ta-IN": "Asmita", "kn-IN": "Saanvi", "ml-IN": "Reshma",
  "mr-IN": "Zahira", "bn-IN": "Kirra", "gu-IN": "Falak", "pa-IN": "Mehuli",
};

type BatchResult = {
  job_id: string;
  status: string;
  transcripts?: Array<{ filename?: string; text: string; segments?: unknown[] }>;
  file_results?: Array<{ original_path?: string; status?: string; error_message?: string }>;
};


const sectionLabels: Record<string, string> = {
  meeting_title: "Meeting title", date: "Date", attendees: "Attendees",
  executive_summary: "Executive summary", agenda: "Agenda",
  discussion_points: "Discussion points", decisions: "Decisions",
  action_items: "Action items", open_questions: "Open questions",
  risks_and_dependencies: "Risks and dependencies", follow_up_email: "Follow-up email",
  title: "Title", topic_summary: "Topic summary", topic_wise_notes: "Topic-wise notes",
  definitions: "Definitions", formulas: "Formulas", examples: "Examples",
  key_takeaways: "Key takeaways", revision_sheet: "Revision sheet",
  practice_questions: "Practice questions",
};

function readable(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not specified";
  if (typeof value === "string" && value.trim().toLowerCase() === "unknown") return "Not available in source";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function StructuredValue({ value }: { value: unknown }): ReactNode {
  if (Array.isArray(value)) {
    return <ul className="structured-list">{value.map((item, index) => (
      <li key={index}><StructuredValue value={item} /></li>
    ))}</ul>;
  }
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).filter(([key]) => key !== "evidence" && key !== "source_evidence");
    return <div className="structured-fields">{entries.map(([key, item]) => (
      <div className="structured-field" key={key}>
        <b>{sectionLabels[key] || key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())}</b>
        <div><StructuredValue value={item} /></div>
      </div>
    ))}</div>;
  }
  return <>{readable(value)}</>;
}

function StructuredOutput({ output }: { output: string }) {
  let parsed: Record<string, unknown> | null = null;
  try {
    const cleaned = output.trim().replace(/^\`\`\`(?:json)?\s*/i, "").replace(/\s*\`\`\`$/, "");
    const candidate: unknown = JSON.parse(cleaned);
    if (candidate && typeof candidate === "object" && !Array.isArray(candidate)) parsed = candidate as Record<string, unknown>;
  } catch {
    parsed = null;
  }
  if (!parsed) return <StructuredOutput output={output} />;

  const entries = Object.entries(parsed).filter(([key, value]) =>
    key !== "source_evidence" && key !== "evidence" && value !== undefined && value !== ""
  );
  return (
    <div className="structured-output">
      {entries.map(([key, value]) => (
        <section className="structured-section" key={key}>
          <h3>{sectionLabels[key] || key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())}</h3>
          <StructuredValue value={value} />
        </section>
      ))}
    </div>
  );
}
\nasync function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail.message === "string") return detail.message;
    return JSON.stringify(detail || body);
  } catch {
    return `Request failed (${response.status})`;
  }
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function App() {
  const [mode, setMode] = useState<Mode>("corporate");
  const [language, setLanguage] = useState<Language>("en-IN");
  const [file, setFile] = useState<File | null>(null);
  const [useBatch, setUseBatch] = useState(false);
  const [sourceText, setSourceText] = useState("");
  const [output, setOutput] = useState("");
  const [batchJobId, setBatchJobId] = useState("");
  const [batchStatus, setBatchStatus] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  async function ingestFile() {
    if (!file) {
      setError("Choose a PDF, text file, or audio recording first.");
      return;
    }
    if (useBatch && (language === "gu-IN" || language === "pa-IN")) {
      setError("Gnani Batch STT does not currently list Gujarati or Punjabi. Turn off Batch STT to use the short-clip REST route.");
      return;
    }
    setBusy("upload");
    setError("");
    setOutput("");
    try {
      if (useBatch && /\.(mp3|wav|m4a|ogg|flac|aac)$/i.test(file.name)) {
        const form = new FormData();
        form.append("file", file);
        form.append("language_code", language);
        const response = await fetch(`${API_BASE}/api/transcribe/batch`, { method: "POST", body: form });
        if (!response.ok) throw new Error(await readError(response));
        const result = await response.json();
        setBatchJobId(result.job_id);
        setBatchStatus(result.status || "STARTING");
        setSourceText("");
        return;
      }
      const form = new FormData();
      form.append("file", file);
      form.append("mode", mode);
      form.append("language_code", language);
      const response = await fetch(`${API_BASE}/api/ingest`, { method: "POST", body: form });
      if (!response.ok) throw new Error(await readError(response));
      const result = await response.json();
      setSourceText(result.text || "");
      setBatchJobId("");
      setBatchStatus("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not process this file.");
    } finally {
      setBusy("");
    }
  }

  async function checkBatch() {
    if (!batchJobId) return;
    setBusy("batch");
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/transcribe/batch/${encodeURIComponent(batchJobId)}`);
      if (!response.ok) throw new Error(await readError(response));
      const result: BatchResult = await response.json();
      setBatchStatus(result.status);
      if (result.transcripts?.length) {
        setSourceText(result.transcripts.map((item) => item.text).join("\n\n"));
      }
      const failed = result.file_results?.filter((item) => item.status === "FAILED" || item.status === "SKIPPED") || [];
      if (failed.length) setError(failed.map((item) => item.error_message || item.original_path || "A file failed").join("; "));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not retrieve batch status.");
    } finally {
      setBusy("");
    }
  }

  async function generate() {
    if (!sourceText.trim()) {
      setError("Add source text or upload a file before generating.");
      return;
    }
    setBusy("generate");
    setError("");
    setOutput("");
    try {
      const response = await fetch(`${API_BASE}/api/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, source_text: sourceText }),
      });
      if (!response.ok) throw new Error(await readError(response));
      const result = await response.json();
      setOutput(result.output || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setBusy("");
    }
  }

  async function exportFile(format: "pdf" | "docx") {
    if (!output) return;
    setBusy(format);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: mode === "corporate" ? "Meeting Minutes" : "Study Notes", body: output, format }),
      });
      if (!response.ok) throw new Error(await readError(response));
      saveBlob(await response.blob(), `moment-ai-output.${format}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setBusy("");
    }
  }

  async function narrate() {
    if (!output) return;
    setBusy("narrate");
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/narrate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: output, voice: voiceByLanguage[language], language, speed: 1.0 }),
      });
      if (!response.ok) throw new Error(await readError(response));
      saveBlob(await response.blob(), "moment-ai-narration.mp3");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Narration failed.");
    } finally {
      setBusy("");
    }
  }

  const batchIsRunning = ["CREATED", "STARTING", "QUEUED", "IN_PROGRESS", "CANCELLING"].includes(batchStatus);

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="MOMENT AI home">
          <span className="brand-mark">M</span>
          <span>MOMENT <b>AI</b></span>
        </a>
        <span className="topbar-note">MEETING & LEARNING INTELLIGENCE</span>
        <span className="status-pill"><i /> Workspace</span>
      </header>

      <main className="workspace">
        <section className="hero">
          <div>
            <p className="eyebrow">TURN INFORMATION INTO ACTION</p>
            <h1>Make every moment<br /><em>count.</em></h1>
            <p className="hero-copy">Turn meeting recordings and lecture material into structured, source-grounded outputs.</p>
          </div>
          <div className="hero-orbit" aria-hidden="true">
            <div className="orbit orbit-one" /><div className="orbit orbit-two" />
            <span className="orbit-core">M</span><span className="orbit-dot dot-one" /><span className="orbit-dot dot-two" />
          </div>
        </section>

        <section className="mode-switch" aria-label="Choose workspace">
          <button className={mode === "corporate" ? "mode-card active" : "mode-card"} onClick={() => { setMode("corporate"); setOutput(""); }}>
            <span className="mode-icon">▤</span>
            <span><b>Corporate</b><small>Meetings, decisions & action items</small></span>
            <span className="mode-arrow">↗</span>
          </button>
          <button className={mode === "student" ? "mode-card active" : "mode-card"} onClick={() => { setMode("student"); setOutput(""); }}>
            <span className="mode-icon">⌁</span>
            <span><b>Student</b><small>Lectures, concepts & revision notes</small></span>
            <span className="mode-arrow">↗</span>
          </button>
        </section>

        <div className="content-grid">
          <section className="panel input-panel">
            <div className="panel-heading">
              <div><p className="eyebrow">01 / SOURCE</p><h2>Add your material</h2></div>
              <span className="step-number">01</span>
            </div>

            <label className="upload-zone">
              <input
                type="file"
                accept=".pdf,.txt,.mp3,.wav,.m4a,.ogg,.flac,.aac"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
              <span className="upload-icon">↑</span>
              <b>{file ? file.name : "Choose a file or browse"}</b>
              <small>PDF, TXT, MP3, WAV, M4A, OGG, FLAC · Short audio: ≤30 sec (Batch: ≤10 MB)</small>
            </label>

            <div className="upload-options">
              <label className="field-label" htmlFor="language">Audio language</label>
              <select id="language" value={language} onChange={(event) => setLanguage(event.target.value as Language)}>
                <option value="en-IN">English (India)</option>
                <option value="hi-IN">Hindi</option>
                <option value="te-IN">Telugu</option>
                <option value="ta-IN">Tamil</option>
                <option value="kn-IN">Kannada</option>
                <option value="ml-IN">Malayalam</option>
                <option value="mr-IN">Marathi</option>
                <option value="bn-IN">Bengali</option>
                <option value="gu-IN" disabled={useBatch}>Gujarati (REST only)</option>
                <option value="pa-IN" disabled={useBatch}>Punjabi (REST only)</option>
              </select>
              <label className="batch-toggle">
                <input type="checkbox" checked={useBatch} onChange={(event) => setUseBatch(event.target.checked)} />
                <span>Long recording (Batch STT)</span>
              </label>
            </div>
            <button className="button button-secondary full-width" onClick={ingestFile} disabled={!file || !!busy}>
              {busy === "upload" ? "Processing file…" : useBatch ? "Start batch transcription" : "Upload & extract text"}
            </button>

            {batchJobId && (
              <div className="batch-card">
                <div><b>Batch job</b><span>{batchStatus}</span></div>
                <small>Job ID: {batchJobId}</small>
                <button className="button button-secondary" onClick={checkBatch} disabled={!!busy || !batchIsRunning && batchStatus !== "PARTIAL_FAILURE" && batchStatus !== "COMPLETED"}>
                  {busy === "batch" ? "Checking…" : "Check transcription status"}
                </button>
              </div>
            )}

            <div className="or-divider"><span>OR PASTE TEXT</span></div>
            <label className="field-label" htmlFor="source">Source material</label>
            <textarea
              id="source"
              className="source-textarea"
              value={sourceText}
              onChange={(event) => setSourceText(event.target.value)}
              placeholder={mode === "corporate" ? "Paste meeting transcript, notes, or discussion…" : "Paste lecture transcript, textbook extract, or class notes…"}
            />
            <div className="textarea-footer"><span>{sourceText.length.toLocaleString()} characters</span><span>Source-grounded processing</span></div>
          </section>

          <section className="panel output-panel">
            <div className="panel-heading">
              <div><p className="eyebrow">02 / RESULT</p><h2>{mode === "corporate" ? "Meeting intelligence" : "Learning intelligence"}</h2></div>
              <span className="step-number">02</span>
            </div>
            <div className="output-intro">
              <span className="sparkle">✳</span>
              <div><b>{mode === "corporate" ? "From discussion to direction." : "From information to understanding."}</b>
                <p>{mode === "corporate" ? "Get clear minutes, decisions, owners, deadlines and follow-ups." : "Get topic-wise notes, definitions, formulas, examples and revision questions."}</p>
              </div>
            </div>
            <button className="button button-primary full-width" onClick={generate} disabled={!!busy}>
              {busy === "generate" ? "Generating…" : "Generate output"}
              <span>↗</span>
            </button>

            {error && <div className="error-box" role="alert">{error}</div>}
            {output ? (
              <>
                <div className="result-heading"><b>Generated output</b><span>Review before sharing</span></div>
                <pre className="result-output">{output}</pre>
                <div className="export-actions">
                  <button className="button button-secondary" onClick={() => exportFile("pdf")} disabled={!!busy}>{busy === "pdf" ? "Creating…" : "↓ PDF"}</button>
                  <button className="button button-secondary" onClick={() => exportFile("docx")} disabled={!!busy}>{busy === "docx" ? "Creating…" : "↓ DOCX"}</button>
                  <button className="button button-secondary" onClick={narrate} disabled={!!busy}>{busy === "narrate" ? "Creating…" : "♫ MP3"}</button>
                </div>
              </>
            ) : (
              <div className="empty-result">
                <div className="empty-document"><span /><span /><span /><span /></div>
                <b>Your output will appear here</b>
                <p>Add a source and generate to create your {mode === "corporate" ? "meeting minutes" : "study notes"}.</p>
              </div>
            )}
          </section>
        </div>

        <footer className="footer">
          <span>© 2026 MOMENT AI</span>
          <span>Built for clarity. Grounded in your source.</span>
        </footer>
      </main>
    </div>
  );
}

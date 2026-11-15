import React, { useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { apiClient, ApiError, type Evaluation, type Job } from "./api";
import "./style.css";

const statusLabel = (item: Evaluation) => item.review ? "Reviewed" : "Needs your review";
function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [connected, setConnected] = useState(false);
  const [jobs, setJobs] = useState<Record<string, Job>>({});
  const [job, setJob] = useState("");
  const [email, setEmail] = useState("");
  const [tenant, setTenant] = useState("group2-corp");
  const [file, setFile] = useState<File | null>(null);
  const [history, setHistory] = useState<Evaluation[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const [mode, setMode] = useState("");
  const running = useRef(false);
  const upload = useRef<HTMLInputElement>(null);
  const api = apiClient("");
  async function run(label: string, action: () => Promise<void>) {
    if (running.current) return;
    running.current = true;
    setBusy(label); setError(""); setNotice("");
    try { await action(); }
    catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        clearSession(); setError("Your session ended. Please sign in again.");
      } else setError(e instanceof Error ? e.message : "Request failed. Please try again.");
    }
    finally { running.current = false; setBusy(""); }
  }
  async function connect() {
    const response = await fetch("/api/v1/auth/login", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({username, password}),
    });
    const auth = await response.json();
    if (!response.ok) throw Error(auth.error ?? "Sign-in failed.");
    setPassword("");
    const [catalog, items] = await Promise.all([api.jobs(), api.list()]);
    const healthResponse = await fetch("/health");
    if (!healthResponse.ok) throw Error("Service unavailable. Please try again.");
    const health = await healthResponse.json();
    setJobs(catalog); setJob(Object.keys(catalog)[0] ?? "");
    setHistory(items); setMode(health.mode); setConnected(true);
  }
  async function evaluate() {
    if (!file) throw Error("Choose a résumé first.");
    if (file.size > 512 * 1024) throw Error("Choose a file smaller than 512 KiB.");
    const form = new FormData();
    form.set("request_id", crypto.randomUUID()); form.set("job_id", job);
    form.set("candidate_email", email); form.set("resume", file);
    const item = await api.evaluate(form);
    setHistory(old => [item, ...old.filter(x => x.evaluation_id !== item.evaluation_id)]);
    setSelected(item.evaluation_id); setChecked(false);
    setFile(null); setEmail(""); if (upload.current) upload.current.value = "";
    setNotice("Evidence is ready. Check it against the original résumé before saving a review.");
  }
  async function review(item: Evaluation, outcome: "CONFIRMED_EVIDENCE" | "FOLLOW_UP_REQUIRED") {
    const saved = await api.review(item.evaluation_id, outcome);
    setHistory(old => old.map(x => x.evaluation_id === saved.evaluation_id ? saved : x));
    setChecked(false); setNotice("Review saved. No hiring decision was made.");
  }
  async function disconnect() {
    const response = await fetch("/api/v1/auth/logout", {method: "POST"});
    if (!response.ok && response.status !== 401) throw Error("Sign-out failed. Please try again.");
    clearSession();
  }
  function clearSession() {
    setConnected(false); setPassword(""); setHistory([]); setSelected(null);
    setEmail(""); setFile(null); setChecked(false); setError(""); setNotice("");
  }
  return <>
    <header className="topbar"><a href="#main" className="brand">Résumé<span> / Alpha</span></a>
      {connected && <button className="quiet" disabled={!!busy} onClick={() => void run("Signing out…", disconnect)}>Sign out</button>}
    </header>
    <main id="main">
      {!connected ? <section className="card welcome">
        <p className="eyebrow">REVIEWER WORKSPACE</p><h1>Let’s review a résumé.</h1>
        <p>Upload a document. Check the evidence. Save your review.</p>
        <form onSubmit={e => { e.preventDefault(); void run("Signing in…", connect); }}>
          <label htmlFor="username">Username</label>
          <input id="username" autoComplete="username" required value={username} disabled={!!busy} onChange={e => setUsername(e.target.value)} />
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" required value={password} disabled={!!busy} onChange={e => setPassword(e.target.value)} />
          <p className="hint">Your local reviewer account. No access key needed.</p>
          <button id="connect" disabled={!!busy || !username.trim() || !password}>{busy || "Sign in"}</button>
        </form>
      </section> : <>
        <div className="page-heading"><div><h1>Your review feed</h1><p>Skill evidence, not hiring decisions.</p></div>
          <span className="badge">{mode === "demo" ? "Demo · simulated AI" : mode === "hermes" ? "Live Hermes / Groq" : "Model mode unknown"}</span>
        </div>
        <section className="card composer" aria-labelledby="upload-title">
          <h2 id="upload-title">Add a résumé</h2>
          <form onSubmit={e => { e.preventDefault(); void run("Checking evidence…", evaluate); }}>
            <fieldset disabled={!!busy}><div className="form-row">
              <div><label htmlFor="email">Candidate email</label><input id="email" type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="candidate@example.com" /></div>
              <div><label htmlFor="job">Role</label><select id="job" value={job} onChange={e => setJob(e.target.value)}>{Object.entries(jobs).map(([id, j]) => <option key={id} value={id}>{j.title}</option>)}</select></div>
            </div>
            <label htmlFor="resume">Résumé file</label><input ref={upload} id="resume" type="file" accept=".pdf,.docx,.txt" required onChange={e => setFile(e.target.files?.[0] ?? null)} />
            <p className="hint">Text-based PDF, DOCX or TXT · up to 512 KiB. Only approved skill IDs and page references go to AI, never the original text or contact details.</p>
            <button id="evaluate" disabled={!job}>{busy === "Checking evidence…" ? busy : "Check evidence"}</button>
            </fieldset>
          </form>
        </section>
      </>}
      {busy && <p className="message" role="status" aria-live="polite">{busy}</p>}
      {error && <p className="message error" role="alert">{error}</p>}
      {notice && <p className="message" role="status">{notice}</p>}
      {connected && <>
        <div className="feed-heading"><h2>Recent activity</h2><button className="quiet" disabled={!!busy} onClick={() => void run("Refreshing…", async () => { setHistory(await api.list()); setChecked(false); })}>Refresh</button></div>
        {history.length === 0 && <section className="empty"><h3>No reviews yet</h3><p>Your uploaded résumés will appear here. Start with a synthetic example for this class prototype.</p></section>}
        <div className="feed">{history.map(item => {
          const open = selected === item.evaluation_id;
          return <article className="card" key={item.evaluation_id}>
            <div className="post-heading"><div className="avatar" aria-hidden="true">R</div><div><h3>{jobs[item.job_id]?.title ?? item.job_id}</h3><p className="hint">Record {item.evaluation_id.slice(-8)}</p></div><span className="badge">{statusLabel(item)}</span></div>
            <p>{item.facts.observed_skills.length} skill mentions · {item.facts.required_skills.length} required skills</p>
            <button className="secondary" disabled={!!busy} aria-expanded={open} aria-controls={`details-${item.evaluation_id}`} onClick={() => { setSelected(open ? null : item.evaluation_id); setChecked(false); }}>{open ? "Close details" : item.review ? "View review" : "Review evidence"}</button>
            {open && <div id={`details-${item.evaluation_id}`} className="evidence">
              {item.failure_code && <p className="error">Automated processing could not finish ({item.failure_code}). Check the evidence manually.</p>}
              <ul className="skills">{item.facts.required_skills.map(skill => {
                const evidence = item.facts.observed_skills.find(s => s.skill_id === skill);
                return <li key={skill}><strong>{skill}</strong><span>{evidence ? `Mentioned · page/section ${evidence.pages.join(", ")}` : "Not found · ask for evidence"}</span></li>;
              })}</ul>
              <p className="hint">A mention is not proof of proficiency. Missing text is not proof of missing ability. Check the original résumé.</p>
              {item.review ? <p className="review-saved">Review saved: {item.review.outcome === "CONFIRMED_EVIDENCE" ? "Evidence checked" : "Follow-up required"}</p> : <>
                <label className="check"><input id={`review-check-${item.evaluation_id}`} type="checkbox" checked={checked} disabled={!!busy} onChange={e => setChecked(e.target.checked)} />I checked the original résumé and this evidence.</label>
                <div className="actions"><button disabled={!!busy || !checked} onClick={() => void run("Saving review…", () => review(item, "CONFIRMED_EVIDENCE"))}>Confirm evidence review</button><button className="secondary" disabled={!!busy || !checked} onClick={() => void run("Saving review…", () => review(item, "FOLLOW_UP_REQUIRED"))}>Needs follow-up</button></div>
                <p className="hint">Saved reviews cannot be edited. Neither action accepts or rejects a candidate.</p>
              </>}
              <details><summary>Technical details</summary><p>Policy: <strong>{item.policy_status}</strong> · OPA: {item.policy?.status ?? "No result"}</p><p className="hint">“Allowed” and “blocked” describe evidence policy checks, not candidate suitability. Human review is always required.</p><p className="hint">AI: {item.ai_metrics.latency_ms} ms · Cost: {item.ai_metrics.cost_usd === null ? "unavailable" : `$${item.ai_metrics.cost_usd}`}<br />Model: {item.model_version}<br />Privacy: {item.privacy_version}<br />ID: {item.evaluation_id}</p></details>
            </div>}
          </article>;
        })}</div>
        <details className="utilities"><summary>Record lookup & audit tools</summary><fieldset disabled={!!busy}><label htmlFor="tenant">Tenant</label><input id="tenant" value={tenant} onChange={e => setTenant(e.target.value)} /><p className="hint">Lookup uses the candidate email in the upload form.</p><button className="secondary" disabled={!email} onClick={() => void run("Looking up record…", async () => { const found = await api.lookup(tenant, email); setNotice(found.status === "FOUND" ? `Existing record: ${found.candidate?.candidate_id}` : "No existing record found."); })}>Find existing record</button><button className="secondary" onClick={() => void run("Checking audits…", async () => { const audit = await api.audits(); setNotice(`${audit.total_records} completed policy audit records`); })}>Check saved audits</button></fieldset></details>
      </>}
      <footer>Class prototype · Human evidence review required · No automated hiring decisions</footer>
    </main>
  </>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);

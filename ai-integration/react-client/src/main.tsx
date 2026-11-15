import React, { useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { apiClient, ApiError, type Evaluation, type Job } from "./api";
import "./style.css";

const statusLabel = (item: Evaluation) => item.review ? "Reviewed" : "Needs your review";
function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [signup, setSignup] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("");
  const [pending, setPending] = useState<{id: string; username: string}[]>([]);
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
  async function authCall(path: string, body?: object) {
    const response = await fetch(`/api/v1/auth/${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: {"Content-Type": "application/json"},
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const result = await response.json();
    if (!response.ok) throw new ApiError(result.error ?? "Account request failed.", response.status);
    return result;
  }
  async function loadWorkspace(nextRole: string) {
    setRole(nextRole); setConnected(true);
    if (nextRole === "pending") return;
    const [catalog, items] = await Promise.all([api.jobs(), api.list()]);
    const healthResponse = await fetch("/health");
    if (!healthResponse.ok) throw Error("Service unavailable. Please try again.");
    const health = await healthResponse.json();
    setJobs(catalog); setJob(Object.keys(catalog)[0] ?? "");
    setHistory(items); setMode(health.mode);
  }
  async function connect() {
    if (signup && password !== confirmPassword) throw Error("Passwords do not match.");
    const response = await fetch(`/api/v1/auth/${signup ? "register" : "login"}`, {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({username, password}),
    });
    const auth = await response.json();
    if (!response.ok) throw Error(auth.error ?? "Sign-in failed.");
    setPassword(""); setConfirmPassword("");
    await loadWorkspace(auth.role);
  }

  async function evaluate(inputFile = file, inputEmail = email, inputJob = job) {
    if (!inputFile) throw Error("Choose a résumé first.");
    if (inputFile.size > 512 * 1024) throw Error("Choose a file smaller than 512 KiB.");
    const form = new FormData();
    form.set("request_id", crypto.randomUUID()); form.set("job_id", inputJob);
    form.set("candidate_email", inputEmail); form.set("resume", inputFile);
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
    setConnected(false); setRole(""); setPending([]); setSignup(false); setConfirmPassword(""); setPassword(""); setHistory([]); setSelected(null);
    setEmail(""); setFile(null); setChecked(false); setError(""); setNotice("");
  }
  return <>
    <a className="skip-link" href="#main">Skip to workspace</a>
    <header className="topbar"><a href="#main" className="brand"><span className="brand-mark" aria-hidden="true">✳</span>Résumé<span className="brand-tag">Alpha</span></a>
      {connected && role !== "pending" && <nav aria-label="Workspace"><a href="#main">Overview</a><a href="#upload-title">Upload</a><a href="#activity">Reviews <span>{history.length}</span></a></nav>}
      {connected && <button className="quiet" disabled={!!busy} onClick={() => void run("Signing out…", disconnect)}>Sign out</button>}
    </header>
    <main id="main" tabIndex={-1}>
      {!connected ? <section className="card welcome">
        <div className="welcome-symbol" aria-hidden="true">✳</div><p className="eyebrow">YOUR REVIEW WORKSPACE</p><h1>{signup ? "Create your account." : "Good evidence. Clearer reviews."}</h1>
        <p>One calm place to upload, check skill evidence and record your review.</p>
        <form onSubmit={e => { e.preventDefault(); void run(signup ? "Creating account…" : "Signing in…", connect); }}>
          <label htmlFor="username">Username</label>
          <input id="username" autoComplete="username" minLength={signup ? 3 : undefined} maxLength={signup ? 64 : 128} pattern={signup ? "[A-Za-z0-9._-]+" : undefined} required value={username} disabled={!!busy} onChange={e => setUsername(e.target.value)} />
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete={signup ? "new-password" : "current-password"} minLength={signup ? 12 : undefined} maxLength={256} required value={password} disabled={!!busy} onChange={e => setPassword(e.target.value)} />
          {signup && <><label htmlFor="confirm-password">Confirm password</label><input id="confirm-password" type="password" autoComplete="new-password" required value={confirmPassword} disabled={!!busy} onChange={e => setConfirmPassword(e.target.value)} /></>}
          <p className="hint">{signup ? "Use at least 12 characters. Demo accounts can enter immediately and share the demo workspace. Live workspaces require owner approval for additional reviewers." : "Your local reviewer account. No access key needed."}</p>
          <button id="connect" disabled={!!busy || !username.trim() || !password}>{busy || (signup ? "Create account" : "Sign in")}</button>
        </form>
        <button className="quiet" disabled={!!busy} onClick={() => { setSignup(!signup); setPassword(""); setConfirmPassword(""); setError(""); }}>{signup ? "Already have an account? Sign in" : "Create an account"}</button>
      </section> : role === "pending" ? <section className="card"><h1>Account created.</h1><p>Your account is waiting for the workspace owner to approve reviewer access. Résumés and audit records stay private until then.</p><button disabled={!!busy} onClick={() => void run("Checking access…", async () => { const user = await authCall("me"); await loadWorkspace(user.role); if (user.role === "pending") setNotice("Approval is still pending."); })}>Check approval</button></section> : <>
        <div className="page-heading"><div><p className="eyebrow">RÉSUMÉ REVIEW / CLASSROOM ALPHA</p><h1>Your résumé workspace</h1><p>Upload a résumé. Explore the evidence. Make the review yours.</p>{(mode === "demo" || mode === "keyless") && <p className="hint">Shared demo workspace. Use synthetic résumés only.</p>}</div>
          <span className="badge">{mode === "demo" ? "Demo · simulated AI" : mode === "hermes" ? "Live Hermes / Groq" : mode === "keyless" ? "Keyless · local MiniLM AI" : "Model mode unknown"}</span>
        </div>
        <section className="quick-actions" aria-label="Start a review">
          <a className="action-tile upload-tile" href="#upload-title"><span className="tile-icon" aria-hidden="true">↑</span><strong>Upload a résumé</strong><span>Bring a PDF, DOCX or text file.</span><span className="tile-arrow" aria-hidden="true">↗</span></a>
          {[true, false].map(complete => <button key={String(complete)} className={`action-tile ${complete ? "complete-tile" : "missing-tile"}`} disabled={!!busy} onClick={() => void run("Checking synthetic example…", () => evaluate(new File([complete ? "Synthetic Candidate. Skills: Python, FastAPI, SQL, Git." : "Synthetic Candidate. Skills: Python."], "synthetic.txt", {type: "text/plain"}), "synthetic@example.test", "backend-engineer"))}>
            <span className="tile-icon" aria-hidden="true">{complete ? "✓" : "＋"}</span><strong>{complete ? "Try complete example" : "Try missing-skills example"}</strong><span>{complete ? "Python, FastAPI, SQL and Git." : "Python only. Find the evidence gaps."}</span><span className="tile-arrow" aria-hidden="true">↗</span>
          </button>)}
        </section>
        <p className="sample-note">Examples are synthetic, not real applicants. Both use the backend-engineer role and the active model mode.</p>
        <section className="card composer" aria-labelledby="upload-title">
          <div className="section-intro"><div><p className="eyebrow">START WITH A DOCUMENT</p><h2 id="upload-title" tabIndex={-1}>Add a résumé</h2></div><span className="format-note">PDF · DOCX · TXT</span></div>
          <details className="sample-source"><summary>Read the original synthetic examples</summary><p className="hint">Complete: “Synthetic Candidate. Skills: Python, FastAPI, SQL, Git.” Missing skills: “Synthetic Candidate. Skills: Python.” Use these originals to verify the example evidence before saving a review.</p></details>
          <form onSubmit={e => { e.preventDefault(); void run("Checking evidence…", () => evaluate()); }}>
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
      {connected && role !== "pending" && <>
        <div className="feed-heading" id="activity"><div><p className="eyebrow">YOUR DOCUMENTS</p><h2>Recent reviews <span className="count">{history.length}</span></h2></div><button className="quiet" disabled={!!busy} onClick={() => void run("Refreshing…", async () => { setHistory(await api.list()); setChecked(false); })}>Refresh</button></div>
        {history.length === 0 && <section className="empty"><h3>No reviews yet</h3><p>Your uploaded résumés will appear here. Start with a synthetic example for this class prototype.</p></section>}
        <div className="feed">{history.map(item => {
          const open = selected === item.evaluation_id;
          return <article className={`card review-card ${open ? "is-open" : ""}`} key={item.evaluation_id}>
            <div className="post-heading"><div className={`document-mark ${item.review ? "document-reviewed" : ""}`} aria-hidden="true"><span></span><span></span><span></span></div><div><h3>{jobs[item.job_id]?.title ?? item.job_id}</h3><p className="hint">Record {item.evaluation_id.slice(-8)}</p></div><span className={`badge ${item.review ? "status-reviewed" : "status-pending"}`}>{statusLabel(item)}</span></div>
            <p className="coverage"><strong>{item.facts.observed_skills.length}</strong> skill mentions <span> / {item.facts.required_skills.length} required skills</span></p>
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
        {role === "owner" && mode === "hermes" && <details className="utilities"><summary>Account requests</summary><p className="hint">Approving grants access to every résumé and audit in this classroom workspace. Approve only your intended collaborators.</p><button className="secondary" disabled={!!busy} onClick={() => void run("Loading requests…", async () => { const result = await authCall("accounts"); setPending(result.accounts); setNotice(result.accounts.length ? "Pending requests loaded." : "No pending account requests."); })}>Load requests</button>{pending.map(account => <div className="account-request" key={account.id}><span>{account.username}</span><button disabled={!!busy} onClick={() => void run("Approving reviewer…", async () => { await authCall(`accounts/${account.id}/approve`, {}); setPending(old => old.filter(x => x.id !== account.id)); setNotice(`Reviewer access approved for ${account.username}.`); })}>Approve reviewer access</button></div>)}</details>}
        <details className="utilities"><summary>Record lookup & audit tools</summary><fieldset disabled={!!busy}><label htmlFor="tenant">Tenant</label><input id="tenant" value={tenant} onChange={e => setTenant(e.target.value)} /><p className="hint">Lookup uses the candidate email in the upload form.</p><button className="secondary" disabled={!email} onClick={() => void run("Looking up record…", async () => { const found = await api.lookup(tenant, email); setNotice(found.status === "FOUND" ? `Existing record: ${found.candidate?.candidate_id}` : "No existing record found."); })}>Find existing record</button><button className="secondary" onClick={() => void run("Checking audits…", async () => { const audit = await api.audits(); setNotice(`${audit.total_records} completed policy audit records`); })}>Check saved audits</button></fieldset></details>
      </>}
      <footer>Class prototype · Human evidence review required · No automated hiring decisions</footer>
    </main>
  </>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);

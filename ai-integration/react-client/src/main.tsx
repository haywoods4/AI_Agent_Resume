import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { apiClient, ApiError, type Evaluation, type Job } from "./api";
import "./style.css";

const completeSample = "Synthetic Candidate. Skills: Python, FastAPI, SQL, Git.";
const missingSample = "Synthetic Candidate. Skills: Python.";
const samples = {
  complete: new File([completeSample], "synthetic.txt", {type: "text/plain"}),
  missing: new File([missingSample], "synthetic.txt", {type: "text/plain"}),
};
const sizeLimit = 512 * 1024;
const browserApi = apiClient("");
const statusLabel = (item: Evaluation) => item.review ? "Reviewed" :
  item.failure_code ? "Manual check needed" :
  item.policy_status === "blocked" ? "Evidence missing" : "Ready for review";
const evidenceCheck = (file: File) =>
  !/\.(pdf|docx|txt)$/i.test(file.name) ? "Choose a text-based PDF, DOCX or TXT file." :
  file.size === 0 ? "This file is empty. Choose a résumé with readable text." :
  file.size > sizeLimit ? "The file is over 512 KiB. Choose a smaller copy." : "";
function actionError(error: unknown, action: string) {
  if (error instanceof ApiError) {
    if (error.status === 413) return "The upload is too large. Choose a document no larger than 512 KiB.";
    if (error.status === 429)
      return error.code === "CAPACITY_EXCEEDED"
        ? "The evidence checker is busy. Wait a moment, then try again."
        : "Too many requests. Wait a minute, then try again.";
    if (error.status === 503 && error.code === "DEPENDENCY")
      return "The workspace couldn't save this result. Refresh reviews to verify it before retrying.";
    if (error.status >= 500) return "The workspace is temporarily unavailable. Try again shortly.";
  }
  if (error instanceof TypeError) {
    return action === "Saving review…" || action === "Checking evidence…" ||
      action === "Checking synthetic example…"
      ? "The connection was interrupted. Refresh reviews to check whether it was saved before trying again."
      : "Couldn't reach the workspace. Check your connection and try again.";
  }
  return error instanceof Error ? error.message : "Request failed. Please try again.";
}
function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [signup, setSignup] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("");
  const [pending, setPending] = useState<{id: string; username: string}[]>([]);
  const [connected, setConnected] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [jobs, setJobs] = useState<Record<string, Job>>({});
  const [job, setJob] = useState("");
  const [email, setEmail] = useState("");
  const [tenant, setTenant] = useState("group2-corp");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");
  const request = useRef<{ file: File; email: string; job: string; id: string } | null>(null);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const focusResult = useRef(false);
  const [history, setHistory] = useState<Evaluation[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const [mode, setMode] = useState("");
  const [audits, setAudits] = useState<Awaited<ReturnType<typeof api.audits>> | null>(null);
  const running = useRef(false);
  const upload = useRef<HTMLInputElement>(null);
  const api = browserApi;
  useEffect(() => {
    let cancelled = false;
    async function restoreSession() {
      try {
        const user = await authCall("me");
        if (!cancelled) await loadWorkspace(user.role, () => cancelled);
      } catch (e) {
        if (!cancelled && !(e instanceof ApiError && e.status === 401))
          setError(actionError(e, "Restoring session…"));
      } finally {
        if (!cancelled) setInitializing(false);
      }
    }
    void restoreSession();
    return () => { cancelled = true; };
  }, []);
  useEffect(() => {
    if (!busy && focusResult.current && resultHeading.current) {
      focusResult.current = false;
      resultHeading.current.focus();
    }
  }, [busy, selected]);
  async function run(label: string, action: () => Promise<void>) {
    if (running.current) return;
    running.current = true;
    setBusy(label); setError(""); setNotice("");
    try { await action(); }
    catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        clearSession(); setError("Your session ended. Please sign in again.");
      } else setError(actionError(e, label));
    }
    finally { running.current = false; setBusy(""); }
  }
  async function authCall(path: string, body?: object) {
    const response = await fetch(`/api/v1/auth/${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: {"Content-Type": "application/json"},
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const result = await response.json().catch(() => null);
    if (!response.ok || result === null)
      throw new ApiError(result?.message ?? result?.error ?? "Account request failed.", response.status);
    return result;
  }
  async function loadWorkspace(nextRole: string, cancelled = () => false) {
    if (nextRole !== "pending") {
      const [catalog, items, healthResponse] = await Promise.all([
        api.jobs(), api.list(), fetch("/health"),
      ]);
      if (!healthResponse.ok) throw Error("The workspace isn't ready. Try signing in again shortly.");
      const health = await healthResponse.json();
      if (cancelled()) return;
      setJobs(catalog); setJob(Object.keys(catalog)[0] ?? "");
      setHistory(items); setMode(health.mode); setAudits(null);
    }
    if (cancelled()) return;
    setRole(nextRole); setConnected(true);
  }
  async function connect() {
    if (signup && password !== confirmPassword) throw Error("Passwords do not match.");
    let auth;
    try {
      auth = await authCall(signup ? "register" : "login", {username, password});
    } catch (e) {
      if (e instanceof ApiError && e.status === 401)
        throw Error("Username or password didn't match. Try signing in again.");
      throw e;
    }
    await loadWorkspace(auth.role);
    setPassword(""); setConfirmPassword("");
  }

  async function evaluate(inputFile = file, inputEmail = email, inputJob = job) {
    if (!inputFile) throw Error("Choose a résumé first.");
    const problem = evidenceCheck(inputFile);
    if (problem) throw Error(problem);
    const previous = request.current;
    const same = previous?.file === inputFile &&
      previous.email === inputEmail && previous.job === inputJob;
    const id = same ? previous.id : crypto.randomUUID();
    request.current = { file: inputFile, email: inputEmail, job: inputJob, id };
    const form = new FormData();
    form.set("request_id", id);
    form.set("job_id", inputJob);
    if (inputEmail.trim()) form.set("candidate_email", inputEmail.trim());
    form.set("file", inputFile);
    const item = await api.evaluate(form);
    setHistory(old => [item, ...old.filter(x => x.evaluation_id !== item.evaluation_id)]);
    request.current = null;
    focusResult.current = true;
    setSelected(item.evaluation_id); setChecked(false);
    if (inputFile === file) {
      setFile(null); setFileError(""); setEmail("");
      if (upload.current) upload.current.value = "";
    }
    setAudits(null);
    setNotice(item.failure_code
      ? "Automated processing was incomplete. Open the result to see how to proceed."
      : "Result saved. Check the evidence against the original before recording your review.");
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
    setEmail(""); setFile(null); setFileError(""); setChecked(false); setError(""); setNotice("");
    request.current = null; focusResult.current = false; setAudits(null);
  }
  return <>
    <a className="skip-link" href="#main">Skip to workspace</a>
    <header className="topbar"><a href="#main" className="brand"><span className="brand-mark" aria-hidden="true">✳</span>Résumé<span className="brand-tag">Alpha</span></a>
      {connected && role !== "pending" && <nav aria-label="Workspace"><a href="#main">Overview</a><a href="#upload-title">Upload</a><a href="#activity">Reviews <span>{history.length}</span></a></nav>}
      {connected && <button className="quiet" disabled={!!busy} onClick={() => void run("Signing out…", disconnect)}>Sign out</button>}
    </header>
    <main id="main" tabIndex={-1}>
      {initializing ? <p className="message" role="status">Checking for an existing session…</p> : !connected ? <section className="card welcome">
        <div className="welcome-symbol" aria-hidden="true">✳</div><p className="eyebrow">YOUR REVIEW WORKSPACE</p><h1>{signup ? "Create your account." : "Good evidence. Clearer reviews."}</h1>
        <p>Upload a résumé, check the skill evidence, then record your review. No hiring decisions are made here.</p>
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
        <div className="page-heading"><div><p className="eyebrow">RÉSUMÉ REVIEW / CLASSROOM ALPHA</p><h1>Your résumé workspace</h1><p>Start with a synthetic example or choose a résumé. Review the evidence before saving an outcome.</p>{(mode === "demo" || mode === "keyless") && <p className="hint">Shared demo workspace. Use synthetic résumés only.</p>}</div>
          <span className="badge">{mode === "demo" ? "Demo · simulated AI" : mode === "hermes" ? "Live Hermes / Groq" : mode === "keyless" ? "Keyless · local MiniLM AI" : "Model mode unknown"}</span>
        </div>
        <section className="quick-actions" aria-label="Start a review">
          <a className="action-tile upload-tile" href="#upload-title"><span className="tile-icon" aria-hidden="true">↑</span><strong>Upload a résumé</strong><span>Bring a PDF, DOCX or text file.</span><span className="tile-arrow" aria-hidden="true">↗</span></a>
          {[true, false].map(complete => <button key={String(complete)} className={`action-tile ${complete ? "complete-tile" : "missing-tile"}`} disabled={!!busy} onClick={() => void run("Checking synthetic example…", () => evaluate(complete ? samples.complete : samples.missing, "synthetic@example.test", "backend-engineer"))}>
            <span className="tile-icon" aria-hidden="true">{complete ? "✓" : "＋"}</span><strong>{complete ? "Try complete example" : "Try missing-skills example"}</strong><span>{complete ? "Python, FastAPI, SQL and Git." : "Python only. Find the evidence gaps."}</span><span className="tile-arrow" aria-hidden="true">↗</span>
          </button>)}
        </section>
        <p className="sample-note">Examples are synthetic, not real applicants. Both use the backend-engineer role and the active model mode.</p>
        <section className="card composer" aria-labelledby="upload-title">
          <div className="section-intro"><div><p className="eyebrow">START WITH A DOCUMENT</p><h2 id="upload-title" tabIndex={-1}>Add a résumé</h2></div><span className="format-note">PDF · DOCX · TXT</span></div>
          <details className="sample-source"><summary>Read the original synthetic examples</summary><p className="hint">Complete: “{completeSample}” Missing skills: “{missingSample}” Use these originals to verify the example evidence before saving a review.</p></details>
          <form onSubmit={e => { e.preventDefault(); void run("Checking evidence…", () => evaluate()); }}>
            <fieldset disabled={!!busy}><div className="form-row">
              <div><label htmlFor="email">Candidate email (optional)</label><input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="candidate@example.com" /></div>
              <div><label htmlFor="job">Role</label><select id="job" value={job} onChange={e => setJob(e.target.value)}>{Object.entries(jobs).map(([id, j]) => <option key={id} value={id}>{j.title}</option>)}</select></div>
            </div>
            <label htmlFor="resume">Résumé file</label><input ref={upload} id="resume" type="file" accept=".pdf,.docx,.txt" required aria-invalid={!!fileError} aria-describedby={fileError ? "file-rules file-error" : "file-rules"} onChange={e => {
              const choice = e.target.files?.[0] ?? null;
              setFile(choice); setFileError(choice ? evidenceCheck(choice) : "");
            }} />
            <p className="hint" id="file-rules">Text-based PDF, DOCX or TXT · up to 512 KiB. Scans without readable text are not supported. The model receives only approved skill IDs, page references and job context.</p>
            {fileError && <p id="file-error" className="message error" role="alert">{fileError}</p>}
            <button id="evaluate" disabled={!job || !!fileError}>{busy === "Checking evidence…" ? busy : "Check evidence"}</button>
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
          const mentioned = new Set(item.facts.observed_skills.map(skill => skill.skill_id));
          const coverage = item.facts.required_skills.filter(skill => mentioned.has(skill)).length;
          return <article className={`card review-card ${open ? "is-open" : ""}`} key={item.evaluation_id}>
            <div className="post-heading"><div className={`document-mark ${item.review ? "document-reviewed" : ""}`} aria-hidden="true"><span></span><span></span><span></span></div><div><h3 ref={open ? resultHeading : undefined} tabIndex={open ? -1 : undefined}>{jobs[item.job_id]?.title ?? item.job_id}</h3><p className="hint">Record {item.evaluation_id.slice(-8)}</p></div><span className={`badge ${item.review ? "status-reviewed" : "status-pending"}`}>{statusLabel(item)}</span></div>
            <p className="coverage"><strong>{coverage} of {item.facts.required_skills.length}</strong> required skills mentioned</p>
            <button className="secondary" disabled={!!busy} aria-expanded={open} aria-controls={`details-${item.evaluation_id}`} onClick={() => { setSelected(open ? null : item.evaluation_id); setChecked(false); }}>{open ? "Close details" : item.review ? "View review" : "Review evidence"}</button>
            {open && <div id={`details-${item.evaluation_id}`} className="evidence">
              {item.failure_code ? <p className="message error">Automated processing did not finish. Check the source document manually and record a follow-up if needed. The technical details show where processing stopped.</p>
                : item.policy_status === "blocked" ? <p className="message">Some required evidence was not found. Check the original; if wording or formatting obscured a skill, record a follow-up rather than assuming the applicant lacks it.</p> : null}
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
              <details><summary>Technical details</summary><p>Policy: <strong>{item.policy_status}</strong> · OPA: {item.policy?.status ?? "No result"}{item.failure_code && <><br />Processing code: {item.failure_code}</>}</p><p className="hint">“Allowed” and “blocked” describe evidence policy checks, not candidate suitability. Human review is always required.</p><p className="hint">AI: {item.ai_metrics.latency_ms} ms · Cost: {item.ai_metrics.cost_usd === null ? "unavailable" : `$${item.ai_metrics.cost_usd}`}<br />Model: {item.model_version}<br />Privacy: {item.privacy_version}<br />ID: {item.evaluation_id}</p></details>
            </div>}
          </article>;
        })}</div>
        {role === "owner" && mode === "hermes" && <details className="utilities"><summary>Account requests</summary><p className="hint">Approving grants access to every résumé and audit in this classroom workspace. Approve only your intended collaborators.</p><button className="secondary" disabled={!!busy} onClick={() => void run("Loading requests…", async () => { const result = await authCall("accounts"); setPending(result.accounts); setNotice(result.accounts.length ? "Pending requests loaded." : "No pending account requests."); })}>Load requests</button>{pending.map(account => <div className="account-request" key={account.id}><span>{account.username}</span><button disabled={!!busy} onClick={() => void run("Approving reviewer…", async () => { await authCall(`accounts/${account.id}/approve`, {}); setPending(old => old.filter(x => x.id !== account.id)); setNotice(`Reviewer access approved for ${account.username}.`); })}>Approve reviewer access</button></div>)}</details>}
        <details className="utilities"><summary>Record lookup & audit tools</summary><fieldset disabled={!!busy}><label htmlFor="tenant">Tenant</label><input id="tenant" value={tenant} onChange={e => setTenant(e.target.value)} /><p className="hint">Lookup uses the candidate email in the upload form.</p><button className="secondary" disabled={!email} onClick={() => void run("Looking up record…", async () => { const found = await api.lookup(tenant, email); setNotice(found.status === "FOUND" ? `Existing record: ${found.candidate?.candidate_id}` : "No existing record found."); })}>Find existing record</button><button className="secondary" onClick={() => void run("Checking audits…", async () => { setAudits(await api.audits()); })}>Load saved audits</button></fieldset>
          {audits && <><p className="hint">{audits.total_records} policy audit records. Showing up to the latest 10.</p>
            <ul className="skills audit-list">{audits.logs.slice(0, 10).map(entry => <li key={entry.audit_id}>
              <strong>Record {entry.evaluation_id.slice(-8)} · {entry.audit_id}</strong>
              <span>{entry.verdict === "PASS" ? "Evidence documented" : entry.verdict === "FAIL" ?
                "Evidence missing" : "Manual check needed"} · <time dateTime={entry.timestamp}>{new Date(entry.timestamp).toLocaleString()}</time></span>
            </li>)}</ul></>}
        </details>
      </>}
      <footer>Class prototype · Human evidence review required · No automated hiring decisions</footer>
    </main>
  </>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);

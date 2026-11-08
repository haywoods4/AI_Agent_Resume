import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { apiClient, type Evaluation, type Job } from "./api";
import "./style.css";

function App() {
  const [token, setToken] = useState(""),
    [connected, setConnected] = useState(false),
    [jobs, setJobs] = useState<Record<string, Job>>({});
  const [job, setJob] = useState(""),
    [email, setEmail] = useState(""),
    [tenant, setTenant] = useState("group2-corp");
  const [file, setFile] = useState<File | null>(null),
    [result, setResult] = useState<Evaluation | null>(null),
    [history, setHistory] = useState<Evaluation[]>([]);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [checked, setChecked] = useState(false),
    [mode, setMode] = useState("");
  const api = apiClient(token);
  async function run(action: () => Promise<void>) {
    setError("");
    setNotice("");
    setBusy(true);
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  async function connect() {
    const catalog = await api.jobs();
    setJobs(catalog);
    setJob(Object.keys(catalog)[0]);
    setHistory(await api.list());
    setConnected(true);
    const health = await (await fetch("/health")).json();
    setMode(health.mode);
  }
  async function evaluate() {
    if (!file) throw Error("Select a resume");
    const form = new FormData();
    form.set("request_id", crypto.randomUUID());
    form.set("job_id", job);
    form.set("candidate_email", email);
    form.set("resume", file);
    setResult(await api.evaluate(form));
    setChecked(false);
    setHistory(await api.list());
  }
  async function review(outcome: "CONFIRMED_EVIDENCE" | "FOLLOW_UP_REQUIRED") {
    if (!result) return;
    setResult(await api.review(result.evaluation_id, outcome));
    setHistory(await api.list());
    setNotice("Human evidence review saved. No hiring decision was made.");
  }
  return (
    <main>
      <header>
        <p className="eyebrow">AI RESUME EVALUATOR · INTEGRATION WORKSPACE</p>
        <h1>
          Evidence first.
          <br />A person makes the decision.
        </h1>
        <p>Review documented job skills with Hermes, Groq and OPA.</p>
      </header>
      <section className="connection">
        <label>
          Reviewer access token
          <input
            id="token"
            type="password"
            autoComplete="off"
            value={token}
            onChange={(e) => {
              setToken(e.target.value);
              setConnected(false);
              setResult(null);
              setHistory([]);
            }}
          />
        </label>
        <button id="connect" disabled={busy} onClick={() => void run(connect)}>
          Connect
        </button>
        {connected && (
          <span className="badge">
            {mode === "demo"
              ? "Demo model · real policy engine"
              : "Hermes / Groq mode"}
          </span>
        )}
      </section>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      {connected && (
        <div className="layout">
          <div>
            <section>
              <h2>1. Check a candidate</h2>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void run(evaluate);
                }}
              >
                <label>
                  Tenant
                  <input
                    id="tenant"
                    value={tenant}
                    onChange={(e) => setTenant(e.target.value)}
                  />
                </label>
                <label>
                  Candidate email
                  <input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </label>
                <button
                  type="button"
                  id="lookup"
                  disabled={busy || !email}
                  onClick={() =>
                    void run(async () => {
                      const found = await api.lookup(tenant, email);
                      setNotice(
                        found.status === "FOUND"
                          ? `Existing record: ${found.candidate?.candidate_id}`
                          : "No existing record. Uploading will create an opaque candidate record.",
                      );
                    })
                  }
                >
                  Check existing record
                </button>
                <label>
                  Job
                  <select
                    id="job"
                    value={job}
                    onChange={(e) => setJob(e.target.value)}
                  >
                    {Object.entries(jobs).map(([id, j]) => (
                      <option key={id} value={id}>
                        {j.title}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Resume
                  <input
                    id="resume"
                    type="file"
                    accept=".pdf,.docx,.txt"
                    required
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                </label>
                <p className="hint">
                  Text-based PDF, DOCX or TXT · maximum 512 KiB. Raw text stays
                  in the backend and is discarded after extraction. Only
                  approved skill IDs and page references reach the AI.
                </p>
                <button id="evaluate" disabled={busy}>
                  {busy ? "Processing…" : "Evaluate evidence"}
                </button>
              </form>
            </section>
            {result && (
              <section id="result">
                <div className="toolbar">
                  <h2>2. Review evidence</h2>
                  <span className="badge">
                    {result.status.replaceAll("_", " ")}
                  </span>
                </div>
                <p className="hint">{result.evaluation_id}</p>
                {result.failure_code && (
                  <p className="error">
                    {result.failure_code}: automated processing could not
                    finish. Review the extracted evidence manually.
                  </p>
                )}
                <table>
                  <thead>
                    <tr>
                      <th>Required skill</th>
                      <th>Document evidence</th>
                      <th>Reviewer action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.facts.required_skills.map((skill) => {
                      const evidence = result.facts.observed_skills.find(
                        (s) => s.skill_id === skill,
                      );
                      return (
                        <tr key={skill}>
                          <td>{skill}</td>
                          <td>
                            {evidence
                              ? `Mentioned · page/section ${evidence.pages.join(", ")}`
                              : "Not found"}
                          </td>
                          <td>
                            {evidence
                              ? "Verify proficiency"
                              : "Request evidence"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <p>
                  Policy status: <strong>{result.policy_status}</strong> · OPA:{" "}
                  <strong>
                    {result.policy?.status.replaceAll("_", " ") ??
                      "No policy result"}
                  </strong>
                </p>
                <p className="hint">
                  Mentions do not establish proficiency. Missing text does not
                  establish a lack of ability. Confirm against the original
                  resume; this result never accepts or rejects a candidate.
                </p>
                <p className="hint">
                  AI latency: {result.ai_metrics.latency_ms} ms · Cost:{" "}
                  {result.ai_metrics.cost_usd === null
                    ? "unavailable (provider billing not supplied)"
                    : `$${result.ai_metrics.cost_usd}`}{" "}
                  · Model: {result.model_version} · Privacy:{" "}
                  {result.privacy_version}
                </p>
                {result.review ? (
                  <p role="status">
                    Recorded review:{" "}
                    {result.review.outcome.replaceAll("_", " ")}
                  </p>
                ) : (
                  <>
                    <label className="check">
                      <input
                        id="review-check"
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => setChecked(e.target.checked)}
                      />
                      I checked the original resume and the listed evidence.
                    </label>
                    <button
                      id="confirm"
                      disabled={busy || !checked}
                      onClick={() =>
                        void run(() => review("CONFIRMED_EVIDENCE"))
                      }
                    >
                      Confirm evidence review
                    </button>
                    <button
                      id="follow-up"
                      className="secondary"
                      disabled={busy || !checked}
                      onClick={() =>
                        void run(() => review("FOLLOW_UP_REQUIRED"))
                      }
                    >
                      Mark for follow-up
                    </button>
                  </>
                )}
              </section>
            )}
          </div>
          <aside>
            <h2>Recent evaluations</h2>
            <p className="hint">
              Opaque IDs only. Contact fields are not shown in model output.
            </p>
            {history.length === 0 && <p>No evaluations yet.</p>}
            {history.map((item) => (
              <button
                className="history"
                key={item.evaluation_id}
                onClick={() => {
                  setResult(item);
                  setChecked(false);
                }}
              >
                <strong>{item.job_id}</strong>
                <span>{item.status.replaceAll("_", " ")}</span>
                <small>{item.evaluation_id.slice(-12)}</small>
              </button>
            ))}
          </aside>
        </div>
      )}
      <footer>
        Integration reference client · React → FastAPI → Hermes / Groq → OPA ·
        SQLite persistence
      </footer>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

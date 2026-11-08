import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from app.contracts import Evaluation, Review


class ConflictError(Exception):
    pass


class Store:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(path, timeout=1, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
          PRAGMA journal_mode=WAL;
          PRAGMA foreign_keys=ON;
          CREATE TABLE IF NOT EXISTS candidates (
            id TEXT PRIMARY KEY, tenant TEXT NOT NULL, email_hash TEXT NOT NULL,
            phone_hash TEXT, phone_last4 TEXT, phi_flag INTEGER NOT NULL DEFAULT 0,
            UNIQUE(tenant,email_hash), UNIQUE(tenant,phone_hash)
          );
          CREATE TABLE IF NOT EXISTS evaluations (
            id TEXT PRIMARY KEY, tenant TEXT NOT NULL,
            candidate_id TEXT NOT NULL REFERENCES candidates(id), payload TEXT NOT NULL,
            created REAL NOT NULL
          );
          CREATE TABLE IF NOT EXISTS requests (
            tenant TEXT NOT NULL, operation TEXT NOT NULL, request_id TEXT NOT NULL,
            fingerprint TEXT NOT NULL, result TEXT NOT NULL, expires REAL NOT NULL,
            PRIMARY KEY(tenant,operation,request_id)
          );
          CREATE TABLE IF NOT EXISTS reviews (
            evaluation_id TEXT PRIMARY KEY REFERENCES evaluations(id), reviewer TEXT NOT NULL,
            outcome TEXT NOT NULL, reason TEXT NOT NULL, created REAL NOT NULL
          );
          CREATE TABLE IF NOT EXISTS decision_audit (
            id INTEGER PRIMARY KEY, tenant TEXT NOT NULL, evaluation_id TEXT NOT NULL,
            phase TEXT NOT NULL, job_requirements TEXT NOT NULL, approved_inputs TEXT NOT NULL,
            model_version TEXT NOT NULL, policy_result TEXT NOT NULL, ai_metrics TEXT NOT NULL,
            created REAL NOT NULL
          );
          CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY, tenant TEXT NOT NULL, request_id TEXT NOT NULL,
            action TEXT NOT NULL, status TEXT NOT NULL, source TEXT NOT NULL,
            latency_ms INTEGER NOT NULL, created REAL NOT NULL
          );
        """)

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def candidate(self, tenant, email_hash, phone_hash=None, phone_last4=None, sensitive=False):
        with self.transaction():
            row = self.db.execute(
                "SELECT * FROM candidates WHERE tenant=? AND email_hash=?", (tenant, email_hash)
            ).fetchone()
            if row:
                if phone_hash and row["phone_hash"] not in {None, phone_hash}:
                    raise ConflictError("Candidate contact conflict; verify the existing record")
                self.db.execute(
                    "UPDATE candidates SET phi_flag=max(phi_flag,?), "
                    "phone_hash=coalesce(phone_hash,?),"
                    "phone_last4=coalesce(phone_last4,?) WHERE id=?",
                    (int(sensitive), phone_hash, phone_last4, row["id"]),
                )
                return row["id"]
            candidate_id = f"cand_{uuid.uuid4().hex}"
            try:
                self.db.execute(
                    "INSERT INTO candidates VALUES (?,?,?,?,?,?)",
                    (candidate_id, tenant, email_hash, phone_hash, phone_last4, int(sensitive)),
                )
            except sqlite3.IntegrityError as error:
                raise ConflictError(
                    "Contact identifier already belongs to another record"
                ) from error
            return candidate_id

    def lookup(self, tenant, kind, digest):
        column = "email_hash" if kind == "email" else "phone_hash"
        row = self.db.execute(
            f"SELECT * FROM candidates WHERE tenant=? AND {column}=?", (tenant, digest)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def public_candidate(row):
        return {
            "candidate_id": row["id"],
            "email_hash": f"hmac-sha256:{row['email_hash']}",
            "phone_last4": row["phone_last4"],
            "phi_flag": bool(row["phi_flag"]),
        }

    def replay(self, tenant, operation, request_id, fingerprint):
        row = self.db.execute(
            "SELECT * FROM requests WHERE tenant=? AND operation=? AND request_id=? AND expires>?",
            (tenant, operation, request_id, time.time()),
        ).fetchone()
        if row:
            if row["fingerprint"] != fingerprint:
                raise ConflictError("request_id was already used for a different payload")
            return json.loads(row["result"])
        return None

    def remember(self, tenant, operation, request_id, fingerprint, result):
        self.db.execute(
            "INSERT OR REPLACE INTO requests VALUES (?,?,?,?,?,?)",
            (tenant, operation, request_id, fingerprint, json.dumps(result), time.time() + 86400),
        )
        self.db.execute("DELETE FROM requests WHERE expires<?", (time.time(),))

    def save_evaluation(self, tenant, evaluation: Evaluation, request_id, fingerprint, phase=None):
        with self.transaction():
            self.db.execute(
                "INSERT INTO evaluations VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE "
                "SET payload=excluded.payload",
                (
                    evaluation.evaluation_id,
                    tenant,
                    evaluation.candidate_id,
                    evaluation.model_dump_json(),
                    time.time(),
                ),
            )
            if phase:
                self.decision_audit(tenant, evaluation, phase)
            self.remember(
                tenant,
                "evaluation",
                request_id,
                fingerprint,
                {"evaluation_id": evaluation.evaluation_id},
            )

    def evaluation(self, tenant, evaluation_id):
        row = self.db.execute(
            "SELECT payload FROM evaluations WHERE tenant=? AND id=?", (tenant, evaluation_id)
        ).fetchone()
        return Evaluation.model_validate_json(row["payload"]) if row else None

    def list_evaluations(self, tenant):
        rows = self.db.execute(
            "SELECT payload FROM evaluations WHERE tenant=? ORDER BY created DESC LIMIT 100",
            (tenant,),
        ).fetchall()
        return [Evaluation.model_validate_json(row["payload"]) for row in rows]

    def review(self, tenant, reviewer, evaluation_id, review: Review):
        with self.transaction():
            evaluation = self.evaluation(tenant, evaluation_id)
            if evaluation is None:
                return None
            if evaluation.review:
                if evaluation.review != review:
                    raise ConflictError("Review is already recorded; conflicting overwrite refused")
                return evaluation
            self.db.execute(
                "INSERT INTO reviews VALUES (?,?,?,?,?)",
                (evaluation_id, reviewer, review.outcome, review.reason, time.time()),
            )
            evaluation.review = review
            evaluation.status = "REVIEWED"
            self.db.execute(
                "UPDATE evaluations SET payload=? WHERE id=?",
                (evaluation.model_dump_json(), evaluation_id),
            )
            self.audit(tenant, evaluation_id, "review", review.outcome, "sqlite", 0)
            return evaluation

    def audit(self, tenant, request_id, action, status, source, latency_ms):
        self.db.execute(
            "INSERT INTO audit(tenant,request_id,action,status,source,latency_ms,created) "
            "VALUES (?,?,?,?,?,?,?)",
            (tenant, request_id, action, status, source, latency_ms, time.time()),
        )

    def decision_audit(self, tenant, evaluation, phase):
        """Append-only snapshots include all four fields required by the sprint backlog."""
        self.db.execute(
            "INSERT INTO decision_audit(tenant,evaluation_id,phase,job_requirements,"
            "approved_inputs,model_version,policy_result,ai_metrics,created) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                tenant,
                evaluation.evaluation_id,
                phase,
                json.dumps(evaluation.facts.required_skills),
                evaluation.facts.model_dump_json(),
                evaluation.model_version,
                json.dumps(
                    {
                        "status": evaluation.policy_status,
                        "decision": evaluation.policy.model_dump() if evaluation.policy else None,
                        "failure_code": evaluation.failure_code,
                    }
                ),
                evaluation.ai_metrics.model_dump_json(),
                time.time(),
            ),
        )

    def close(self):
        self.db.close()

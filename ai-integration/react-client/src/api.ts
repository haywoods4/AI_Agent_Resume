export interface Evaluation {
  evaluation_id: string;
  candidate_id: string;
  job_id: string;
  status: "READY_FOR_REVIEW" | "MANUAL_REVIEW_REQUIRED" | "REVIEWED";
  facts: {
    required_skills: string[];
    observed_skills: { skill_id: string; pages: number[] }[];
    page_count: number;
  };
  assessment: {
    skills: {
      skill_id: string;
      status: "MENTIONED" | "NOT_FOUND";
      evidence_pages: number[];
      review_focus: string;
    }[];
  } | null;
  policy: {
    status: string;
    matched_skills: string[];
    missing_skills: string[];
    requires_human_review: true;
    policy_version: string;
  } | null;
  failure_code: string | null;
  model_version: string;
  privacy_version: string;
  review: { outcome: string; reason: string } | null;
}
export interface Job {
  title: string;
  required_skills: string[];
}
export function apiClient(token: string) {
  async function call<T>(path: string, body?: object | FormData): Promise<T> {
    const form = body instanceof FormData;
    const response = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        ...(form ? {} : { "Content-Type": "application/json" }),
      },
      body: body === undefined ? undefined : form ? body : JSON.stringify(body),
    });
    const result = await response.json();
    if (!response.ok)
      throw new Error(
        result.message ??
          result.detail ??
          result.error ??
          `Request failed (${response.status})`,
      );
    return result;
  }
  return {
    jobs: () => call<Record<string, Job>>("/api/v1/jobs"),
    list: () => call<Evaluation[]>("/api/v1/evaluations"),
    evaluate: (form: FormData) => call<Evaluation>("/api/v1/evaluations", form),
    lookup: (tenant: string, email: string) =>
      call<{
        status: string;
        source: string;
        candidate: { candidate_id: string } | null;
      }>("/api/v1/candidates/inquiry", {
        request_id: crypto.randomUUID(),
        tenant_id: tenant,
        candidate_email: email,
        query_type: "lookup_by_email",
      }),
    review: (
      id: string,
      outcome: "CONFIRMED_EVIDENCE" | "FOLLOW_UP_REQUIRED",
    ) =>
      call<Evaluation>(`/api/v1/evaluations/${id}/review`, {
        outcome,
        reason:
          outcome === "CONFIRMED_EVIDENCE"
            ? "VERIFIED_AGAINST_RESUME"
            : "INSUFFICIENT_EVIDENCE",
      }),
  };
}

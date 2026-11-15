package resume.screening

import rego.v1

# Only explicit job skill evidence is evaluated. No identity/demographic inputs.
required := {skill | some skill in input.required_skills}
observed := {skill | some skill in input.observed_skills}
matched := required & observed
missing := required - observed

status := "REQUIREMENTS_DOCUMENTED" if count(missing) == 0
else := "MISSING_REQUIRED_EVIDENCE"

result := {
  "policy_version": "job-evidence-v1",
  "status": status,
  "matched_skills": sort(matched),
  "missing_skills": sort(missing),
  "requires_human_review": true,
}

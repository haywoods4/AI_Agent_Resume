package resume.screening_test

import rego.v1
import data.resume.screening

test_documented_still_requires_review if {
  r := screening.result with input as {"required_skills": ["python"], "observed_skills": ["python"]}
  r.status == "REQUIREMENTS_DOCUMENTED"
  r.requires_human_review == true
}

test_missing_is_evidence_gap_not_rejection if {
  r := screening.result with input as {"required_skills": ["python", "sql"], "observed_skills": ["python"]}
  r.missing_skills == ["sql"]
  r.status == "MISSING_REQUIRED_EVIDENCE"
  r.requires_human_review == true
}

test_unrelated_skills_do_not_satisfy_requirement if {
  r := screening.result with input as {"required_skills": ["python"], "observed_skills": ["java"]}
  r.matched_skills == []
}

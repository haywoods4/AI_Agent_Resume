# Résumé Screening Alpha: Verification and Release Evidence

## Evidence available for the portfolio

| Evidence | What it shows | What it does not show |
| --- | --- | --- |
| [AI integration CI](https://github.com/haywoods4/AI_Agent_Resume/actions/runs/43771731116), [Interface contracts CI](https://github.com/haywoods4/AI_Agent_Resume/actions/runs/43771731143) | 58 Python tests, three OPA checks, Ruff, React production build and interface examples passed at the same `develop` commit, `8f281bc1981343e20688bf824be049b663aea1c4`. | Production deployment, load capacity, or coverage percentage. |
| [Merged Alpha PR #4](https://github.com/haywoods4/AI_Agent_Resume/pull/4) | Reports 58 tests and three OPA policy tests, Ruff, startup checks and React build at its cited PR head `bc90ecbd`. It also records a fresh Codespaces browser run using keyless MiniLM, including both examples and save/relogin persistence. | A full production deployment; live Groq behavior in the browser. The PR-head count is separate from the merge-commit CI result. |
| [Live verification record](https://github.com/haywoods4/AI_Agent_Resume/blob/8f281bc1981343e20688bf824be049b663aea1c4/ai-integration/docs/live-verification-2026-11-15.md) | November 15 synthetic Hermes/Groq API checks with real OPA and SQLite. Complete case: 2,393 ms model, 2,557 ms total. Missing-evidence case: 841 ms model, 962 ms total. Both required human review. A follow-up review was saved and the evaluation appeared in the audit API. | A production latency estimate, average or percentile; load capacity, cost, fairness, or a live Groq browser test. Sample size: two evaluations. |

## Capture for the final team video and repository

1. Start from the chosen release revision. Record its SHA, environment, and mode label. Use synthetic fixtures only.
2. Show the two synthetic examples, page evidence, a saved human follow-up review and audit history. Retain images or logs that identify the build and mode. Do not show customer data or credentials.
3. Capture the green workflows for the exact submitted revision. If the team has an actual deployment job, record its run and environment separately. The Codespaces run is evidence of a working cloud development preview, not a production CD pipeline.
4. Report coverage percentage, workload, and measured reliability only if the team has collected them. If a release cannot be verified, state the gap rather than using old numbers. For a benchmark, record sample size, hardware, mode, concurrency and errors.
5. Include the repository link, installation/user/API links, final video link, and each team member's confirmed contributions. Associate collaborative work with the actual PRs and reviews.

## Automated classroom preview

On changes covered by the AI integration workflow, the runner builds the React client and stages that build on its loopback interface. FastAPI runs with local MiniLM, OPA and a fresh SQLite database. A headless browser registers a synthetic reviewer, submits both fixtures, checks the policy outcomes, saves a follow-up, reloads and verifies the corresponding audit references. A failure in this sequence fails the job.

Open the run's **classroom-preview-evidence** artifact for the workspace, saved review, audit screenshots, revision and Python application coverage XML. The screenshots come from the application served on that runner. The preview is torn down at the end of the job. Hosting a persistent service, testing concurrent production traffic and verifying per-opening access controls remain separate work.

### November 21, 2026 | Run 44879456611

The [branch build](https://github.com/haywoods4/AI_Agent_Resume/actions/runs/44879456611) exercised [revision b17a169](https://github.com/haywoods4/AI_Agent_Resume/tree/b17a169eb1befcca008c7b70d2e5a64987e8f0ee). It passed 62 Python tests, all three OPA policy tests, Ruff, the React build and the browser preview check. The [coverage report](evidence/unit8/backend-coverage.xml) records 899 of 992 executable Python application statements (90.63%, about 91%). The [job log](https://github.com/haywoods4/AI_Agent_Resume/actions/runs/44879456611/job/136771314310) records the commands and outcomes.

| Evidence from this run | What to look for |
| --- | --- |
| [Actions summary](evidence/unit8/actions-summary.jpg) | Successful build at b17a169, linked artifact and branch. |
| [Staged review workspace](evidence/unit8/workspace.png) | Two synthetic records and the local MiniLM mode label on the built client. |
| [Saved follow-up](evidence/unit8/saved-review.png) and [audit list](evidence/unit8/audit.png) | Record ending in 50b3b471 had one of four required skill mentions. The follow-up survived reload and the audit list shows the same reference. |
| [Machine-readable result](evidence/unit8/preview.json) | The two fixture outcomes and exact tested revision. |

For the separate macOS timing experiment and its workload, see [workspace verification](UNIT8_WORKSPACE_VERIFICATION.md). The uploaded report and images come from synthetic data in a temporary classroom preview.

# Stakeholder Video: Résumé Screening Integration Segment

**Presenter:** Justin Gaffney · **Time:** about 2½ minutes of the 10–15 minute team video
**Placement:** After the architecture overview, before the team's validation results.

Use the agreed team build and a private Codespaces preview with synthetic data. Rehearse the two examples and saved review before filming. For the run shown, name the model mode visible in the UI.

| Time | Show | Say |
| --- | --- | --- |
| 0:00–0:30 | Sign in; identify the keyless mode if using the Codespaces demo. | “My role was connecting the review screen, backend, model, policy check and audit history. This demo runs local MiniLM inference in Codespaces. The separate live Hermes and Groq path was checked through the API.” |
| 0:30–1:05 | Choose **Try complete example** and expand the evidence. | “FastAPI reduces the résumé to approved skill IDs and page references before it goes to the model. The résumé and contact details stay out of that model request. OPA checks whether the required skills are documented. A mention tells the reviewer where to look, not what the applicant can do.” |
| 1:05–1:45 | Choose **Try missing-skills example**. Show what needs follow-up and save a review. | “Here we're missing evidence for a required skill, so I can mark it for follow-up. This isn't an automated rejection. The reviewer still makes the judgment, and the app saves the outcome separately from the initial assessment.” |
| 1:45–2:30 | Open saved reviews/audit history and show the matching evaluation. Then show the pinned CI links if the next presenter will not. | “The saved review and audit record let us trace the result back to the evidence and policy check. We recorded two synthetic live API timings separately, but those two requests don't establish capacity. Next, we'll show what the checks actually tested and what still needs work.” |

Use the missing-evidence fixture or a recorded API result to describe limitations only after labeling which path ran. Do not describe the keyless browser preview or a simulated screenshot as a live Groq browser run.

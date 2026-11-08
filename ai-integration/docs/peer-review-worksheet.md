# My peer-review and refinement-report worksheet

I am waiting for my teammates to implement their modules and provide feedback. I have not completed a formal peer review, and I will not submit this worksheet as a completed review.

I will record my name, my teammate’s name, the module, PR URL, exact commit, review date and test commands. I will review one actual teammate module against these categories:

| Category | My review questions | My evidence |
|---|---|---|
| Quality/readability | Can I follow the responsibilities, names, types and functions? | File/line, issue and concrete correction |
| Security | Can I find exposed PII, missing authorization or unsafe model/policy output? | Reproduction and expected boundary |
| Performance | Can I verify bounded time/memory and the under-ten-second AI target? | Measured workload and timing |
| Integration | Can I connect the JSON fields, statuses, errors and SQLite records? | Contract test and observed mismatch |
| Documentation | Can I install and run the module from its README? | Verified commands and missing steps |

For each finding, I will record severity, evidence, a proposed fix, my teammate’s response, the resolution commit and verification. I will record “no issue found” only after inspecting that category. I will request feedback on my contribution and link any resulting changes to the original feedback.

## My exactly 250-word report plan

I will write my final report after I have actual review evidence. I will use these word budgets:

- 45 words: I identify the module and commit I reviewed, my review method, and feedback I received.
- 90 words: I explain changes I made because of that feedback and how I verified them.
- 80 words: I identify concrete technical debt, its maintenance/reliability cost, completed mitigation and remaining actions.
- 35 words: I assess my collaboration and identify my next improvement.

I will count the final report body to confirm exactly 250 words. I will distinguish my own testing and observations from actual peer feedback. I cannot complete the feedback-dependent report until my teammates provide code and review my contribution.

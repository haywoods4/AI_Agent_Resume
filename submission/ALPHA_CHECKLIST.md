# My Unit 5 submission checklist

I reviewed the supplied Unit 5 instructions in full. I must submit a shared repository link containing a functional Alpha and my exactly250-word individual refinement report. I keep this checklist separate from the report word count.

## My evidence

- I reviewed [Sophia's PR #2](https://github.com/haywoods4/AI_Agent_Resume/pull/2#pullrequestreview-5835176477), covering startup, readability, security/privacy, performance limits, interface compatibility and documentation. I do not repeat the old empty-database finding as a current defect; Sophia subsequently implemented it.
- I received [Sophia's approval on PR #1](https://github.com/haywoods4/AI_Agent_Resume/pull/1#pullrequestreview-5822823062). I do not treat that earlier approval as approval of my new assembly changes.
- I incorporated [Similun's interface feedback](https://github.com/haywoods4/AI_Agent_Resume/pull/2#issuecomment-6757120181) into the shared upload and audit routes.
- I addressed [Sophia's request for explicit errors](https://github.com/haywoods4/AI_Agent_Resume/pull/3#pullrequestreview-5906569923) with OpenAPI error schemas, examples, and tests.
- I verified28 backend tests with real Redis/OPA, three OPA policy tests, Ruff, the React build, and root application import locally. I verified allowed/blocked uploads, a saved review and audit lookup in Chromium. I used a simulated model for that browser run.
- I installed the pinned original Hermes source/runtime successfully. I have not performed live Groq inference.
- I verified that the original AI integration branch had successful GitHub Actions runs. I still need CI on the new assembled commit; prior CI does not validate it.

## My remaining release gates

1. I open UMGC locally and verify the exact deadline and submission destination. The PDF says Tuesday11:59p.m.ET, while the date communicated in chat was the18th. I use the actual LMS entry to resolve that difference.
2. I configure Groq locally with `uv run python scripts/configure_groq.py`, start live services, and run the allowed/blocked smoke test. I retain evidence labeled `hermes` mode. I fix any actual provider/model/runtime failure instead of treating the fixture as live success.
3. I publish `justin/alpha-integration` from my authorized Mac account and open a PR against `develop`. I coordinate the overlapping original PRs; I do not merge competing versions blindly.
4. I confirm CI passes for the exact commit and obtain team review of consolidated storage, effective contracts, and skill-only scope. I keep `main` untouched unless the team authorizes release promotion.
5. I update my report only with completed facts and recount exactly250 words. I submit the shared repository URL with a clear link to the approved Alpha revision and my report according to UMGC instructions. I do not submit a local-only ZIP in place of the required shared repository.

## My demonstration sequence

I connect the React client with the local reviewer token. I select backend-engineer and upload fixtures/allowed.txt, then fixtures/blocked.txt. I show the policy outcome and evidence, explain that a blocked result means missing documented skill evidence rather than automatic rejection, record a human review, and show saved audit records. I identify whether the session uses a simulated model or actual Hermes/Groq. I show the failure-handling tests and the passing CI run for the final revision.

## My technical-debt decisions

I consolidate the two backends into one SQLite store so different entry points do not produce incompatible outcomes. I preserve the foundation and contract contributions in Git history. I keep a single-worker/single-reviewer boundary for the classroom Alpha, literal skill extraction rather than unsupported qualifications, no raw resume persistence, and human review for every outcome. I leave numeric cost unavailable when the provider does not supply it. I do not claim production security, general qualification extraction, bias certification or a completed live run.

# My keyless GitHub launch

[Open this Alpha in GitHub Codespaces](https://codespaces.new/haywoods4/AI_Agent_Resume/tree/justin/alpha-integration)

1. I sign in to GitHub and confirm **Create codespace** for `justin/alpha-integration`. GitHub must grant me access to the repository. A professor without repository access needs the group owner to grant it; this button cannot bypass a private repository.
2. I wait for the setup task to install Python/Node dependencies, verify OPA, and download the pinned public MiniLM model (~87 MB). The private **Resume Alpha** preview opens on port **5173**. If it does not, I open Ports → Resume Alpha → Open in Browser.
3. I choose **Create an account** in the application. On a new codespace the first account owns that isolated classroom workspace. Later accounts need its approval.
4. I open **Try a synthetic example instead**, then click the complete and missing-skills examples. No file download is needed. Alternatively, I upload the repository’s synthetic fixtures. I expand evidence, check it against the fixture, save a human review and inspect audits.
5. I stop the codespace when finished. I download any required evidence before deleting it. Deletion removes its local accounts/data; stopping preserves workspace files but may still incur storage usage.

No Groq key, model account, paid model API or local-machine server is needed for this path. It runs on GitHub’s computer, not my Mac. GitHub provisioning still requires login, repository access and confirmation; “one-click” is a launch shortcut, not a claim of anonymous or instantaneous hosting.

## What the AI actually does

I run the pretrained `sentence-transformers/all-MiniLM-L6-v2` ONNX model on CPU. Its neural embeddings decide which approved skill IDs match observed skill IDs at a conservative 0.90 cosine threshold. Only those predictions are transformed into the structured assessment and sent to OPA. A separate exact-evidence validator rejects unsupported matches or omissions instead of substituting a fabricated passing answer. A model fault leaves manual review required.

This is a deliberately narrow **local neural evidence matcher**, not a generative résumé reader, hiring scorer, or a Hermes/Groq inference. I preserve the original actual Hermes/Groq mode for separate use. I do not claim MiniLM improves on exact matching for this canonical-ID task: the narrowness preserves privacy and provides a small, reproducible keyless AI demonstration. Human review and the same parser limitations remain.

I pin the model revision and SHA-256 hashes in `ai-integration/config/keyless-model.json`, preserve its Apache-2.0 model card/license, and execute no remote model Python. Setup fails on a digest mismatch. Model weights stay ignored, not committed. During evaluation no résumé or skill payload is sent to a model vendor. Infrastructure compute still has a cost even though there is no model API bill.

## Cost, access and security

GitHub personal Free/Pro accounts include some Codespaces compute/storage, but available quota and policy vary. I check the creation screen and [GitHub billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces) before starting. This is **not a promise of unlimited free hosting**. The launch does not enable paid spending, change budgets, make a repository public, or make ports public.

Only the frontend port is explicitly forwarded. FastAPI, OPA and optional Hermes remain local to the codespace. I use the exact HTTPS codespace origin, Secure/HttpOnly cookies and existing app authentication. I keep the preview private; sharing a public demo requires a separate security/access decision. Each person creating their own codespace has their own accounts/database. This is not an always-on hosted website, multi-tenant service or release deployment.

## Troubleshooting and verification

I inspect `ai-integration/data/codespaces.log` if startup fails. I rerun `bash .devcontainer/setup.sh` after fixing a dependency/download failure, then `bash .devcontainer/start.sh`. The startup lock prevents duplicate servers when editors reattach. The UI badge must say **Keyless · local MiniLM AI**; **Demo · simulated AI** is a different mode and is not neural-inference proof.

I run these checks from `ai-integration`:

```sh
uv run --extra keyless pytest -q tests ../test_main.py
tools/opa test policies/ -v
npm --prefix react-client run build
uv run --extra keyless python scripts/alpha_smoke.py
```

The test suite covers all 64 observed-skill subsets across the six current catalog skills with actual model inference, adversarial wrong-model outputs, keyless upload/privacy behavior, and real OPA integration. The original live Hermes/Groq instructions remain in the root README. Tiny Qwen experiments were rejected after incorrect evidence results, not shipped as successful AI.

**Verification boundary:** local actual MiniLM/OPA execution and CI checks are evidence for those components. A fresh GitHub Codespaces provision/browser session has not yet been verified from this account because its current CLI authorization lacks the `codespace` scope. I do not describe that unexecuted cloud launch as passed.

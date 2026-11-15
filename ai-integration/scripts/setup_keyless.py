"""Download pinned public model weights, verify SHA-256; never execute remote model code."""

import hashlib
import json
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent.parent
manifest = json.loads((root / "config/keyless-model.json").read_text())
folder = root / "data/keyless-model"
folder.mkdir(parents=True, exist_ok=True)
base = f"https://huggingface.co/{manifest['repository']}/resolve/{manifest['revision']}"
for source, digest in manifest["files"].items():
    target = folder / Path(source).name
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == digest:
        continue
    temporary = target.with_suffix(".download")
    with urllib.request.urlopen(f"{base}/{source}", timeout=120) as response:
        content = response.read(150 * 1024 * 1024)
    if hashlib.sha256(content).hexdigest() != digest:
        raise SystemExit("Model digest mismatch. Refusing unverified weights.")
    temporary.write_bytes(content)
    temporary.replace(target)
# Preserve upstream model license next to the downloaded weights.
with urllib.request.urlopen(f"{base}/README.md", timeout=30) as response:
    (folder / "MODEL-CARD.md").write_bytes(response.read(100000))
with urllib.request.urlopen(
    "https://www.apache.org/licenses/LICENSE-2.0.txt", timeout=30
) as response:
    (folder / "LICENSE").write_bytes(response.read(100000))
print("Pinned MiniLM model verified. No API key required; no inference performed yet.")

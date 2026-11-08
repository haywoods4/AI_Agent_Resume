"""Fetch a pinned official OPA binary and verify its published SHA-256 digest."""

import hashlib
import os
import platform
import urllib.request
from pathlib import Path

version = "1.0.1"
system = {"Linux": "linux", "Darwin": "darwin", "Windows": "windows"}.get(platform.system())
machine = {"x86_64": "amd64", "AMD64": "amd64", "arm64": "arm64", "aarch64": "arm64"}.get(
    platform.machine()
)
if not system or not machine or (system == "windows" and machine != "amd64"):
    raise SystemExit("Install OPA 1.x manually for this platform")
suffix = (
    "_static" if system == "linux" and machine == "amd64" else ".exe" if system == "windows" else ""
)
asset = f"opa_{system}_{machine}{suffix}"
base = f"https://github.com/open-policy-agent/opa/releases/download/v{version}/{asset}"
target = (
    Path(__file__).resolve().parent.parent / "tools" / ("opa.exe" if system == "windows" else "opa")
)
with urllib.request.urlopen(base + ".sha256", timeout=30) as response:
    expected = response.read().decode().split()[0]
with urllib.request.urlopen(base, timeout=60) as response:
    content = response.read()
if hashlib.sha256(content).hexdigest() != expected:
    raise SystemExit("OPA checksum mismatch; refusing installation")
target.parent.mkdir(exist_ok=True)
target.write_bytes(content)
os.chmod(target, 0o755)
print(f"OPA {version} installed with verified SHA-256 at {target}")

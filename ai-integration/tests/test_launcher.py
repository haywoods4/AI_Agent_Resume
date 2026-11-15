"""Linux-only supervisor ownership check, independent of app/model dependencies."""

import os
import shutil
import signal
import subprocess
import time

import pytest


@pytest.mark.skipif(not shutil.which("setsid"), reason="Linux Codespaces process-group test")
def test_launcher_terminates_owned_service_groups(tmp_path):
    commands = tmp_path / "bin"
    commands.mkdir()
    receipt = tmp_path / "groups"
    for name in ["uv", "npm"]:
        path = commands / name
        path.write_text('#!/bin/bash\necho $$ >> "$GROUP_RECEIPT"\nexec sleep 60\n')
        path.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{commands}:{os.environ['PATH']}",
        "CODESPACES": "true",
        "CODESPACE_NAME": "test",
        "GROUP_RECEIPT": str(receipt),
    }
    process = subprocess.Popen(
        ["bash", "scripts/codespaces_run.sh"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    groups = []
    try:
        for _ in range(100):
            groups = receipt.read_text().splitlines() if receipt.exists() else []
            if len(groups) == 2:
                break
            time.sleep(0.02)
        assert len(groups) == 2
        process.terminate()
        process.wait(timeout=5)
        for group in groups:
            with pytest.raises(ProcessLookupError):
                os.killpg(int(group), 0)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        for group in groups:
            try:
                os.killpg(int(group), signal.SIGKILL)
            except ProcessLookupError:
                pass

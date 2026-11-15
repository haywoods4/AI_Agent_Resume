import io
import resource
from unittest.mock import patch

import pytest

from app import parse_worker
from app.providers import HermesClient, OPAClient


@pytest.mark.parametrize("platform,has_memory_cap", [("darwin", False), ("linux", True)])
def test_parser_resource_limits_preserve_supported_guards(platform, has_memory_cap):
    source = io.TextIOWrapper(io.BytesIO(b"Python"))
    with (
        patch.object(parse_worker.sys, "platform", platform),
        patch.object(parse_worker.sys, "argv", ["parser", "resume.txt"]),
        patch.object(parse_worker.sys, "stdin", source),
        patch.object(parse_worker.sys, "stdout", io.StringIO()),
        patch("resource.setrlimit") as limits,
    ):
        parse_worker.main()
    limits.assert_any_call(resource.RLIMIT_CPU, (4, 4))
    memory_calls = [call for call in limits.call_args_list if call.args[0] == resource.RLIMIT_AS]
    assert bool(memory_calls) == has_memory_cap


@pytest.mark.asyncio
async def test_local_services_ignore_unrelated_proxy_environment(settings, monkeypatch):
    monkeypatch.setenv("ALL_PROXY", "socks5h://127.0.0.1:1")
    for client_type in (HermesClient, OPAClient):
        client = client_type(settings)
        assert client.client.trust_env is False
        await client.close()

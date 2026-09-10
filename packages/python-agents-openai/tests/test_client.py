from unittest.mock import AsyncMock, patch

import pytest
from agents.sandbox.manifest import Manifest
from agents.sandbox.session.sandbox_session import SandboxSession
from superserve.types import SandboxInfo, SandboxStatus
from superserve_agents_openai import (
    SuperserveSandboxClient,
    SuperserveSandboxClientOptions,
)
from superserve_agents_openai.session import SuperserveSandboxSession


@pytest.fixture
def mock_async_sandbox():
    sandbox = AsyncMock()
    sandbox.id = "sbx_test_456"
    sandbox.kill = AsyncMock(return_value=None)
    sandbox.get_info = AsyncMock(
        return_value=SandboxInfo(
            id="sbx_test_456",
            name="openai-agent-sandbox",
            status=SandboxStatus.ACTIVE,
            created_at="2026-09-10T12:00:00Z",
            preview_access="private",
        )
    )
    return sandbox


@pytest.mark.asyncio
async def test_client_create_and_delete(mock_async_sandbox):
    client = SuperserveSandboxClient(
        SuperserveSandboxClientOptions(api_key="ss_test_key")
    )
    manifest = Manifest(root="/workspace")

    with patch(
        "superserve.async_sandbox.AsyncSandbox.create",
        new_callable=AsyncMock,
        return_value=mock_async_sandbox,
    ) as mock_create:
        session = await client.create(manifest=manifest)
        assert isinstance(session, SandboxSession)
        inner = getattr(session, "_inner", session)
        assert isinstance(inner, SuperserveSandboxSession)
        assert inner.state.sandbox_id == "sbx_test_456"
        assert session.state.sandbox_id == "sbx_test_456"
        mock_create.assert_awaited_once()

        # Test delete
        deleted_session = await client.delete(session)
        assert deleted_session is session
        mock_async_sandbox.kill.assert_awaited_once()


def test_sandbox_run_config_accepts_client():
    from agents.sandbox import SandboxRunConfig

    client = SuperserveSandboxClient()
    config = SandboxRunConfig(client=client)
    assert config.client is client

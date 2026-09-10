import io
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from agents.sandbox.manifest import Manifest
from agents.sandbox.snapshot import resolve_snapshot
from superserve.types import CommandResult, SandboxInfo, SandboxStatus
from superserve_agents_openai.client import SuperserveSandboxSessionState
from superserve_agents_openai.session import SuperserveSandboxSession


@pytest.fixture
def mock_sandbox():
    sandbox = MagicMock()
    sandbox.id = "sbx_test_123"
    sandbox.commands = MagicMock()
    sandbox.commands.run = AsyncMock(
        return_value=CommandResult(stdout="hello\n", stderr="", exit_code=0)
    )
    sandbox.files = MagicMock()
    sandbox.files.read = AsyncMock(return_value=b"file content")
    sandbox.files.write = AsyncMock(return_value=None)
    sandbox.get_info = AsyncMock(
        return_value=SandboxInfo(
            id="sbx_test_123",
            name="test-sandbox",
            status=SandboxStatus.ACTIVE,
            created_at="2026-09-10T12:00:00Z",
            preview_access="private",
        )
    )
    return sandbox


@pytest.fixture
def session(mock_sandbox):
    session_id = uuid.uuid4()
    manifest = Manifest(root="/workspace")
    snapshot = resolve_snapshot(None, str(session_id))
    state = SuperserveSandboxSessionState(
        session_id=session_id,
        sandbox_id=mock_sandbox.id,
        manifest=manifest,
        snapshot=snapshot,
    )
    return SuperserveSandboxSession(state=state, sandbox=mock_sandbox)


@pytest.mark.asyncio
async def test_exec_internal(session, mock_sandbox):
    result = await session._exec_internal("echo", "hello")
    assert result.exit_code == 0
    assert result.stdout == b"hello\n"
    assert result.stderr == b""
    mock_sandbox.commands.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_read(session, mock_sandbox):
    session._workspace_root_ready = True
    stream = await session.read(Path("/workspace/hello.txt"))
    assert stream.read() == b"file content"
    mock_sandbox.files.read.assert_awaited_once_with("/workspace/hello.txt")


@pytest.mark.asyncio
async def test_write(session, mock_sandbox):
    session._workspace_root_ready = True
    await session.write(Path("/workspace/hello.txt"), io.BytesIO(b"new content"))
    mock_sandbox.files.write.assert_awaited_once_with(
        "/workspace/hello.txt", b"new content"
    )


@pytest.mark.asyncio
async def test_running(session, mock_sandbox):
    is_running = await session.running()
    assert is_running is True
    mock_sandbox.get_info.assert_awaited_once()


@pytest.mark.asyncio
async def test_read_not_found(session, mock_sandbox):
    from agents.sandbox.errors import WorkspaceReadNotFoundError
    from superserve.errors import NotFoundError

    session._workspace_root_ready = True
    mock_sandbox.files.read.side_effect = NotFoundError("file not found")
    with pytest.raises(WorkspaceReadNotFoundError):
        await session.read(Path("/workspace/missing.txt"))

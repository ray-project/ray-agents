from __future__ import annotations

import io
import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agents.sandbox.errors import (
    WorkspaceArchiveReadError,
    WorkspaceArchiveWriteError,
    WorkspaceReadNotFoundError,
    WorkspaceWriteTypeError,
)
from agents.sandbox.session.base_sandbox_session import BaseSandboxSession
from agents.sandbox.types import ExecResult, User
from agents.sandbox.workspace_paths import sandbox_path_str
from superserve.errors import NotFoundError
from superserve.types import SandboxStatus

if TYPE_CHECKING:
    from .client import SuperserveSandboxSessionState


class SuperserveSandboxSession(BaseSandboxSession):
    """Superserve microVM sandbox session implementation."""

    state: SuperserveSandboxSessionState
    _sandbox: Any
    _workspace_root_ready: bool

    def __init__(
        self,
        *,
        state: SuperserveSandboxSessionState,
        sandbox: Any,
    ) -> None:
        self.state = state
        self._sandbox = sandbox
        self._workspace_root_ready = state.workspace_root_ready

    async def _after_start(self) -> None:
        await super()._after_start()
        self._workspace_root_ready = True

    def _mark_workspace_root_ready_from_probe(self) -> None:
        super()._mark_workspace_root_ready_from_probe()
        self._workspace_root_ready = True

    async def _exec_internal(
        self,
        *command: str | Path,
        timeout: float | None = None,
    ) -> ExecResult:
        command_list = [str(c) for c in command]
        cmd_str = (
            command_list[0] if len(command_list) == 1 else shlex.join(command_list)
        )
        is_ready = self._workspace_root_ready or self.state.workspace_root_ready
        cwd = self.state.manifest.root if is_ready else None
        timeout_seconds = int(timeout) if timeout is not None else None

        res = await self._sandbox.commands.run(
            cmd_str,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
        return ExecResult(
            exit_code=res.exit_code,
            stdout=res.stdout.encode("utf-8", errors="replace"),
            stderr=res.stderr.encode("utf-8", errors="replace"),
        )

    async def read(
        self,
        path: Path,
        *,
        user: str | User | None = None,
    ) -> io.IOBase:
        if user is not None:
            await self._check_read_with_exec(path, user=user)

        workspace_path = await self._validate_path_access(path)
        path_str = sandbox_path_str(workspace_path)

        try:
            content = await self._sandbox.files.read(path_str)
            return io.BytesIO(content)
        except NotFoundError as e:
            raise WorkspaceReadNotFoundError(path=path, cause=e) from e
        except Exception as e:
            raise WorkspaceArchiveReadError(path=path, cause=e) from e

    async def write(
        self,
        path: Path,
        data: io.IOBase,
        *,
        user: str | User | None = None,
    ) -> None:
        if user is not None:
            await self._check_write_with_exec(path, user=user)

        payload = data.read()
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        if not isinstance(payload, bytes | bytearray):
            raise WorkspaceWriteTypeError(path=path, actual_type=type(payload).__name__)

        workspace_path = await self._validate_path_access(path, for_write=True)
        path_str = sandbox_path_str(workspace_path)

        try:
            await self._sandbox.files.write(path_str, bytes(payload))
        except Exception as e:
            raise WorkspaceArchiveWriteError(path=workspace_path, cause=e) from e

    async def running(self) -> bool:
        try:
            info = await self._sandbox.get_info()
            return info.status in (
                SandboxStatus.ACTIVE,
                SandboxStatus.STARTING,
                SandboxStatus.RESUMING,
            )
        except Exception:
            return False

    async def persist_workspace(self) -> io.IOBase:
        raise NotImplementedError(
            "Superserve sandbox workspace snapshot persistence is not supported"
        )

    async def hydrate_workspace(self, data: io.IOBase) -> None:
        raise NotImplementedError(
            "Superserve sandbox workspace hydration is not supported"
        )

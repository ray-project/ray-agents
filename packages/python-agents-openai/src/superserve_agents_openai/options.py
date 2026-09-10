from __future__ import annotations

from typing import Any, Literal
from agents.sandbox.session.sandbox_client import BaseSandboxClientOptions


class SuperserveSandboxClientOptions(BaseSandboxClientOptions):
    """Client options for Superserve microVM sandbox."""

    type: Literal["superserve"] = "superserve"
    api_key: str | None = None
    base_url: str | None = None
    template: str | None = None
    timeout_seconds: int | None = None
    auto_delete_seconds: int | None = None
    metadata: dict[str, str] | None = None
    env_vars: dict[str, str] | None = None

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        template: str | None = None,
        timeout_seconds: int | None = None,
        auto_delete_seconds: int | None = None,
        metadata: dict[str, str] | None = None,
        env_vars: dict[str, str] | None = None,
        type: Literal["superserve"] = "superserve",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type=type,
            api_key=api_key,
            base_url=base_url,
            template=template,
            timeout_seconds=timeout_seconds,
            auto_delete_seconds=auto_delete_seconds,
            metadata=metadata,
            env_vars=env_vars,
            **kwargs,
        )

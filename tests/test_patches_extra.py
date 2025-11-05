"""Additional tests to improve coverage for app.patches.

Covers ensure_sse_server_patch by simulating uvicorn and a FastMCP stub.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app import patches


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio("asyncio")
async def test_ensure_sse_server_patch_wraps_and_runs(
        monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyFastMCP:
        def __init__(self) -> None:
            self.settings = SimpleNamespace(
                host="127.0.0.1", port=9090, log_level="INFO")

        def sse_app(self, mount_path):  # noqa: ANN001
            # Reference the argument so linters don't flag it as unused.
            return f"starlette-app:{mount_path}"

    async def original_run_sse_async(self, mount_path=None):  # noqa: ANN001, D401
        raise AssertionError("Original SSE run should be patched")

    # Install the original attribute that will be wrapped
    # type: ignore[attr-defined]
    DummyFastMCP.run_sse_async = original_run_sse_async

    records = {}

    class DummyConfig:
        def __init__(self, app, host, port, log_level):  # noqa: ANN001
            records["config"] = {
                "app": app,
                "host": host,
                "port": port,
                "log_level": log_level,
            }

    class DummyServer:
        def __init__(self, config: DummyConfig) -> None:
            records["server_config"] = config

        async def serve(self) -> None:
            records["served"] = True

    # Point patches.FastMCP to our dummy and uvicorn to our stubs
    monkeypatch.setattr(patches, "FastMCP", DummyFastMCP)
    monkeypatch.setattr(patches, "_PATCH_SSE_SERVER_APPLIED", False)
    monkeypatch.setitem(
        __import__("sys").modules,
        "uvicorn",
        SimpleNamespace(Config=DummyConfig, Server=DummyServer),
    )

    patches.ensure_sse_server_patch()

    inst = DummyFastMCP()
    # The patched method should be attached and runnable
    await inst.run_sse_async(mount_path="/base")  # type: ignore[attr-defined]

    assert isinstance(records.get("server_config"), DummyConfig)
    assert records["config"]["app"] == "starlette-app:/base"
    assert records["config"]["host"] == "127.0.0.1"
    assert records["config"]["port"] == 9090
    assert records["config"]["log_level"] == "info"
    assert records.get("served") is True

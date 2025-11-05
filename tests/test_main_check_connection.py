from __future__ import annotations

import pytest

from app.grafana_client import GrafanaClient
from app.config import grafana_config_from_env


@pytest.mark.asyncio
@pytest.mark.parametrize("succeeds", [True, False])
async def test_check_connection_via_client(monkeypatch, succeeds):
    async def _ok(self, path):
        return {"status": "ok"}

    async def _fail(self, path):
        raise RuntimeError("connect fail")

    # Patch the instance method on GrafanaClient
    monkeypatch.setattr(GrafanaClient, "get_json", _ok if succeeds else _fail)

    cfg = grafana_config_from_env()
    client = GrafanaClient(cfg)

    if succeeds:
        result = await client.get_json("/api/health")
        assert isinstance(result, dict)
    else:
        with pytest.raises(RuntimeError):
            await client.get_json("/api/health")

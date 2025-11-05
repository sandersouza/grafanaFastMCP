from __future__ import annotations

import os

from app.config import (
    GRAFANA_TLS_CA_FILE_ENV,
    GRAFANA_TLS_CERT_FILE_ENV,
    GRAFANA_TLS_KEY_FILE_ENV,
    GRAFANA_TLS_SKIP_VERIFY_ENV,
    grafana_config_from_env,
)


def test_grafana_config_from_env_tls_parsing(tmp_path, monkeypatch):
    monkeypatch.delenv(GRAFANA_TLS_CERT_FILE_ENV, raising=False)
    monkeypatch.delenv(GRAFANA_TLS_KEY_FILE_ENV, raising=False)
    monkeypatch.delenv(GRAFANA_TLS_CA_FILE_ENV, raising=False)
    monkeypatch.delenv(GRAFANA_TLS_SKIP_VERIFY_ENV, raising=False)

    # Set values
    monkeypatch.setenv(GRAFANA_TLS_CERT_FILE_ENV, "/tmp/cert.pem")
    monkeypatch.setenv(GRAFANA_TLS_KEY_FILE_ENV, "/tmp/key.pem")
    monkeypatch.setenv(GRAFANA_TLS_CA_FILE_ENV, "/tmp/ca.pem")
    monkeypatch.setenv(GRAFANA_TLS_SKIP_VERIFY_ENV, "true")

    cfg = grafana_config_from_env()

    assert cfg.tls_config is not None
    assert cfg.tls_config.cert_file == "/tmp/cert.pem"
    assert cfg.tls_config.key_file == "/tmp/key.pem"
    assert cfg.tls_config.ca_file == "/tmp/ca.pem"
    assert cfg.tls_config.skip_verify is True

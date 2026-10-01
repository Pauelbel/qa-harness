"""Проверки чтения секретов из разных источников."""

import sys
from unittest.mock import MagicMock

import pytest

from qa_core.secrets import SecretError, SecretStore


def test_env_reads_requested_name_and_reports_missing_key(monkeypatch):
    monkeypatch.setenv("STAGE_APP_BEARER", "test-token")
    store = SecretStore("env")

    assert store.get("APP_BEARER", env_key="STAGE_APP_BEARER") == "test-token"
    with pytest.raises(SecretError, match="STAGE_APP_MISSING"):
        store.get("APP_MISSING", env_key="STAGE_APP_MISSING")


def test_vault_v2_uses_approle_and_fetches_only_once(monkeypatch):
    monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com")
    monkeypatch.setenv("VAULT_MOUNT", "kv")
    monkeypatch.setenv("VAULT_PATH", "app/stage")
    monkeypatch.setenv("VAULT_KV_VERSION", "2")
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    monkeypatch.setenv("VAULT_ROLE_ID", "role")
    monkeypatch.setenv("VAULT_SECRET_ID", "secret")
    client = MagicMock()
    client.secrets.kv.v2.read_secret_version.return_value = {
        "data": {"data": {"APP_DATABASE_PORT": 5432, "APP_BEARER": "test-token"}}
    }
    hvac = MagicMock()
    hvac.Client.return_value = client
    monkeypatch.setitem(sys.modules, "hvac", hvac)

    store = SecretStore("vault")
    assert store.get("APP_DATABASE_PORT") == "5432"
    assert store.get("APP_BEARER") == "test-token"
    client.auth.approle.login.assert_called_once_with(role_id="role", secret_id="secret")
    client.secrets.kv.v2.read_secret_version.assert_called_once_with(
        path="app/stage", mount_point="kv", raise_on_deleted_version=True
    )


def test_vault_failure_never_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com")
    monkeypatch.setenv("VAULT_MOUNT", "kv")
    monkeypatch.setenv("VAULT_PATH", "app/stage")
    monkeypatch.setenv("VAULT_TOKEN", "test-token")
    monkeypatch.setenv("STAGE_APP_BEARER", "environment-token")
    client = MagicMock()
    client.secrets.kv.v2.read_secret_version.side_effect = RuntimeError("sensitive response")
    hvac = MagicMock()
    hvac.Client.return_value = client
    monkeypatch.setitem(sys.modules, "hvac", hvac)

    with pytest.raises(SecretError, match="Не удалось прочитать секрет Vault") as error:
        SecretStore("vault").get("APP_BEARER", env_key="STAGE_APP_BEARER")
    assert "sensitive response" not in str(error.value)


def test_vault_v1_token_and_missing_key(monkeypatch):
    monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com")
    monkeypatch.setenv("VAULT_MOUNT", "kv")
    monkeypatch.setenv("VAULT_PATH", "app/stage")
    monkeypatch.setenv("VAULT_KV_VERSION", "1")
    monkeypatch.setenv("VAULT_VERIFY", "false")
    monkeypatch.delenv("VAULT_CACERT", raising=False)
    monkeypatch.setenv("VAULT_TOKEN", "test-token")
    client = MagicMock()
    client.secrets.kv.v1.read_secret.return_value = {"data": {"APP_BEARER": "token"}}
    hvac = MagicMock()
    hvac.Client.return_value = client
    monkeypatch.setitem(sys.modules, "hvac", hvac)

    store = SecretStore("vault")
    assert store.get("APP_BEARER") == "token"
    with pytest.raises(SecretError, match="APP_MISSING"):
        store.get("APP_MISSING")
    client.auth.approle.login.assert_not_called()
    hvac.Client.assert_called_once_with(
        url="https://vault.example.com", token="test-token", verify=False
    )
    client.secrets.kv.v1.read_secret.assert_called_once_with(
        path="app/stage", mount_point="kv"
    )

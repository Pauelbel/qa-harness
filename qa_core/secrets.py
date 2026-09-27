"""Чтение секретов из выбранного источника независимо от pytest."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Literal


class SecretError(ValueError):
    """Источник настроен неверно или запрошенный ключ отсутствует."""


class SecretStore:
    """Один источник на загрузку настроек; Vault читается один раз по запросу."""

    def __init__(self, source: Literal["env", "vault"] | None = None) -> None:
        self.source = (source or os.getenv("SECRETS_SOURCE", "env")).lower()
        if self.source not in {"env", "vault"}:
            raise SecretError("SECRETS_SOURCE должен быть 'env' или 'vault'")
        self._vault_values: Mapping[str, object] | None = None

    def get(self, key: str, *, env_key: str | None = None) -> str:
        """Читает обязательное значение без скрытого перехода к другому источнику."""
        if self.source == "env":
            name = env_key or key
            value = os.getenv(name)
            if not value:
                raise SecretError(f"Не задана обязательная переменная окружения: {name}")
            return value

        if self._vault_values is None:
            self._vault_values = _read_vault()
        value = self._vault_values.get(key)
        if isinstance(value, bool) or not isinstance(value, (str, int, float)) or value == "":
            raise SecretError(f"В Vault отсутствует или пуст обязательный ключ: {key}")
        return str(value)


def _read_vault() -> Mapping[str, object]:
    """Читает KV-секрет с авторизацией по токену или AppRole."""
    address = os.getenv("VAULT_ADDR")
    path = os.getenv("VAULT_PATH")
    mount = os.getenv("VAULT_MOUNT")
    if not address or not path or not mount:
        raise SecretError("Для Vault нужны VAULT_ADDR, VAULT_PATH и VAULT_MOUNT")

    version = os.getenv("VAULT_KV_VERSION", "2")
    if version not in {"1", "2"}:
        raise SecretError("VAULT_KV_VERSION должен быть '1' или '2'")

    token = os.getenv("VAULT_TOKEN")
    role_id = os.getenv("VAULT_ROLE_ID")
    secret_id = os.getenv("VAULT_SECRET_ID")
    if not token and not (role_id and secret_id):
        raise SecretError("Для Vault нужен VAULT_TOKEN или пара VAULT_ROLE_ID и VAULT_SECRET_ID")

    try:
        import hvac
    except ImportError as exc:
        raise SecretError("Для Vault установите дополнительную зависимость 'qa-core[vault]'") from exc

    verify_setting = os.getenv("VAULT_VERIFY", "true").lower()
    if verify_setting not in {"true", "false"}:
        raise SecretError("VAULT_VERIFY должен быть 'true' или 'false'")
    verify = os.getenv("VAULT_CACERT") or (verify_setting == "true")

    try:
        client = hvac.Client(url=address, token=token, verify=verify)
        if not token:
            client.auth.approle.login(role_id=role_id, secret_id=secret_id)
        if version == "2":
            response = client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=mount, raise_on_deleted_version=True
            )
            values = response["data"]["data"]
        else:
            response = client.secrets.kv.v1.read_secret(path=path, mount_point=mount)
            values = response["data"]
    except Exception as exc:
        # Ответ сервера может содержать секреты, поэтому в ошибку попадает только тип исключения.
        raise SecretError(f"Не удалось прочитать секрет Vault ({type(exc).__name__})") from None
    if not isinstance(values, dict):
        raise SecretError("Vault вернул некорректный формат секрета")
    return values

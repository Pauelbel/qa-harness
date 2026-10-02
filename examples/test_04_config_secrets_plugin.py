"""Пример: секреты, конфиг и свой плагин."""

import allure
import pytest

from qa_core.config import load_section
from qa_core.secrets import SecretError, SecretStore
from demo_plugin import DemoSettings


@allure.epic("Примеры")
@allure.title("Секреты: чтение из переменных окружения")
def test_secret_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRETS_SOURCE", "env")
    monkeypatch.setenv("STAGE_API_TOKEN", "тестовый-токен")

    token = SecretStore().get("API_TOKEN", env_key="STAGE_API_TOKEN")

    assert token == "тестовый-токен"


@allure.epic("Примеры")
@allure.title("Секреты: отсутствующий ключ даёт ошибку с его именем")
def test_missing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRETS_SOURCE", "env")
    monkeypatch.delenv("NO_SUCH_SECRET", raising=False)

    with pytest.raises(SecretError, match="NO_SUCH_SECRET"):
        SecretStore().get("NO_SUCH_SECRET")


@allure.epic("Примеры")
@allure.title("Плагин: фикстура со значениями по умолчанию без config.yaml")
def test_plugin_fixture(demo_settings: DemoSettings) -> None:
    assert demo_settings.project == "AG"


@allure.epic("Примеры")
@allure.title("Конфиг: своя секция из указанного YAML")
def test_custom_section(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("demo:\n  project: QA\n", encoding="utf-8")

    settings = load_section("demo", DemoSettings, config_path)

    assert settings.project == "QA"
    assert settings.report_name == "Отчёт.xlsx"

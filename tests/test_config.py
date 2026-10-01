"""Проверки чтения секций config.yaml."""

from pathlib import Path

import allure
import pytest
from pydantic import BaseModel, ConfigDict

from qa_core.clients.http import HttpSettings
from qa_core.config import load_section


class PluginSettings(BaseModel):
    """Секция стороннего плагина: ядро о ней ничего не знает."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    address: str = "localhost:9092"


def write_config(tmp_path: Path, content: str) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(content, encoding="utf-8")
    return config_path


@allure.epic("Ядро")
@allure.title("Без config.yaml действуют значения по умолчанию")
def test_missing_file_uses_defaults(tmp_path: Path) -> None:
    settings = load_section("http", HttpSettings, tmp_path / "нет.yaml")

    assert settings.max_logged_response_body_length == 2000
    assert "token" in settings.sensitive_query_parameters


@allure.epic("Ядро")
@allure.title("Отсутствующая секция заменяется значениями по умолчанию")
def test_missing_section_uses_defaults(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, "browser:\n  headless: false\n")

    settings = load_section("http", HttpSettings, config_path)

    assert settings.max_logged_response_body_length == 2000


@allure.epic("Ядро")
@allure.title("Плагин читает собственную секцию без изменений в ядре")
def test_plugin_defines_own_section(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, "plugin:\n  address: kafka:9092\n")

    settings = load_section("plugin", PluginSettings, config_path)

    assert settings.address == "kafka:9092"


@allure.epic("Ядро")
@allure.title("Имена чувствительных параметров приводятся к нижнему регистру")
def test_sensitive_parameters_are_lowercased(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path, "http:\n  sensitive_query_parameters: [Token, API_KEY]\n"
    )

    settings = load_section("http", HttpSettings, config_path)

    assert settings.sensitive_query_parameters == {"token", "api_key"}


@allure.epic("Ядро")
@allure.title("Неизвестный ключ в секции — понятная ошибка с именем секции")
def test_unknown_key_is_reported(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, "plugin:\n  adress: опечатка\n")

    with pytest.raises(ValueError, match="Некорректная секция 'plugin'"):
        load_section("plugin", PluginSettings, config_path)


@allure.epic("Ядро")
@allure.title("Секция не словарь — понятная ошибка")
def test_section_must_be_mapping(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, "http: 5\n")

    with pytest.raises(ValueError, match="должна быть словарём"):
        load_section("http", HttpSettings, config_path)

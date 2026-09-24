"""Единая точка загрузки и проверки корневого ``config.yaml``.

Зачем нужен файл:
    Модели описывают допустимые секции и типы значений, а ``load_settings`` один
    раз читает каждый YAML. Компоненты ядра получают готовую секцию и не содержат
    собственных парсеров конфигурации.

Как использовать:
    Обычно компоненты вызывают загрузчик сами. Для явного доступа или другого
    файла конфигурации можно вызвать его напрямую.

    >>> settings = load_settings()
    >>> settings.http.max_logged_response_body_length
    2000
    >>> test_settings = load_settings("configs/test.yaml")

При добавлении новой секции в YAML сначала опишите её Pydantic-модель, затем
добавьте поле в ``Settings``. Не создавайте отдельный загрузчик для компонента.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class HttpSettings(BaseModel):
    """Настройки HTTP-клиента."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_logged_response_body_length: int = Field(ge=0)
    sensitive_query_parameters: frozenset[str]

    @field_validator("sensitive_query_parameters")
    @classmethod
    def normalize_parameter_names(cls, value: frozenset[str]) -> frozenset[str]:
        return frozenset(name.lower() for name in value)


class BrowserSettings(BaseModel):
    """Нейтральные настройки браузера для Playwright-фикстуры."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    engine: Literal["chromium", "firefox", "webkit"] = "chromium"
    headless: bool = True
    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    ignore_https_errors: bool = True


class Settings(BaseModel):
    """Все секции корневого config.yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    http: HttpSettings
    browser: BrowserSettings = Field(default_factory=BrowserSettings)


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Возвращает проверенные настройки из указанного или корневого YAML."""
    path = Path(config_path) if config_path is not None else Path.cwd() / "config.yaml"
    return _load_settings(path.resolve())


@lru_cache
def _load_settings(path: Path) -> Settings:
    """Читает каждый файл конфигурации один раз."""
    with path.open(encoding="utf-8") as config_file:
        raw_config = yaml.safe_load(config_file) or {}
    return Settings.model_validate(raw_config)

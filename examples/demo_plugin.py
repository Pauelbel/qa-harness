"""Пример плагина проекта со своей секцией в config.yaml.

Плагин состоит из модели настроек и фикстуры. Ядро qa-core при этом не
меняется: секцию ``demo`` читает сам плагин через ``load_section``.
"""

import pytest
from pydantic import BaseModel, ConfigDict

from qa_core.config import load_section


class DemoSettings(BaseModel):
    """Секция ``demo`` файла config.yaml; без файла действуют эти значения."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project: str = "AG"
    report_name: str = "Отчёт.xlsx"


@pytest.fixture(scope="session")
def demo_settings() -> DemoSettings:
    """Настройки плагина, доступные любому тесту по имени фикстуры."""
    return load_section("demo", DemoSettings)

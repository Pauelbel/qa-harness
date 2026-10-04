"""Общие фикстуры и маркеры, которые нужны почти каждому проекту.

Зачем нужен файл:
    Подготовка, которую иначе каждый автор пишет заново, написана здесь один
    раз. Тест просто просит фикстуру по имени.

Как подключить в ``conftest.py`` проекта:
    pytest_plugins = ["qa_core.pytest_plugins.fixtures"]

Что получает тест:
    ``http_client`` — готовый ``BaseHttpClient``, закрывается сам после теста
    (нужен пакет requests).

Маркеры (запуск ``pytest -m ui``, ``pytest -m "api and smoke"``):
    ``api``, ``ui``, ``db``, ``smoke``, ``regression``.

Фикстуры, которые знают об адресах и данных конкретной системы (создать заказ,
получить токен), в ядро не добавляются: их место — ``conftest.py`` проекта или
папки с тестом.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from qa_core.clients.http import BaseHttpClient

MARKERS = {
    "api": "тесты HTTP/API",
    "ui": "тесты в браузере",
    "db": "тесты, которым нужна база данных",
    "smoke": "быстрая проверка, что система жива",
    "regression": "полная регрессия",
}


def pytest_configure(config) -> None:
    """Регистрирует маркеры, чтобы pytest не предупреждал о неизвестных."""
    for name, description in MARKERS.items():
        config.addinivalue_line("markers", f"{name}: {description}")


@pytest.fixture
def http_client() -> Iterator["BaseHttpClient"]:
    """HTTP-клиент с логами и маскированием токенов; закрывается после теста."""
    # Импорт здесь, чтобы плагин (и маркеры) работали и без пакета requests.
    from qa_core.clients.http import BaseHttpClient

    with BaseHttpClient() as client:
        yield client

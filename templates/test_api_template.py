"""ШАБЛОН API-теста. Скопируйте в tests/api/, переименуйте и замените данные.

1. Скопируйте:  cp templates/test_api_template.py tests/api/test_<тема>.py
2. Замените адрес, путь запроса и ожидаемые значения (места с «ЗАМЕНИТЕ»).
3. Запустите:   python -m pytest tests/api/test_<тема>.py

Нужен плагин qa_core.pytest_plugins.fixtures в conftest.py.
Правила — в Правила.md: один тест — одна мысль, подготовка → действие → проверка,
данные создаёт фикстура, сообщение в assert пишется по-русски.
"""

import os

import pytest

# ЗАМЕНИТЕ: адрес сервиса. Берите его из переменной окружения, не из кода.
BASE_URL = os.getenv("BASE_URL", "https://example.com")

# Маркеры запускают группы тестов: pytest -m smoke. Оставьте нужные.
pytestmark = pytest.mark.api


@pytest.mark.smoke
def test_replace_me(http_client):  # http_client: готовый клиент, закрывается сам
    # Подготовка: нужны данные? Попросите фикстуру в аргументах, не создавайте руками.
    url = f"{BASE_URL}/"  # ЗАМЕНИТЕ: путь запроса

    # Действие
    response = http_client.get(url, timeout=10)

    # Проверка
    assert response.status_code == 200, f"Ожидали 200, получили {response.status_code}"

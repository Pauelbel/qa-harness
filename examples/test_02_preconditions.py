"""Пример: предусловия и постусловия через фикстуры с ``yield``.

Тест не создаёт и не удаляет данные сам. Предусловие (создать заказ через API)
и постусловие (удалить его) описаны один раз в фикстуре ``order`` (см. conftest.py),
а тест просто просит её по имени. Код после ``yield`` выполняется всегда, даже если
тест упал. UI-тест с тем же предусловием — в test_03_ui_page_object.py.

Правила, которые показывает пример:
- данные уникальны для каждого запуска (префикс ``autotest-`` и случайный хвост);
- данные создаются через API, а не кликами в интерфейсе;
- ошибка очистки пишется в лог и не затирает настоящую причину падения теста;
- если нужно несколько заказов в одном тесте, используется фабрика.
"""

from collections.abc import Callable

import pytest

from conftest import ORDER_PREFIX
from qa_core.clients.http import BaseHttpClient

pytestmark = pytest.mark.api


def test_order_exists_via_api(order: dict, demo_url: str) -> None:
    with BaseHttpClient() as http:
        orders = http.get(f"{demo_url}/api/orders").json()["value"]

    assert order in orders


def test_factory_creates_several_orders(order_factory: Callable[[], dict], demo_url: str) -> None:
    first, second = order_factory(), order_factory()

    with BaseHttpClient() as http:
        orders = http.get(f"{demo_url}/api/orders").json()["value"]

    assert first in orders and second in orders
    assert first["id"] != second["id"]


def test_no_leftovers(demo_url: str) -> None:
    with BaseHttpClient() as http:
        orders = http.get(f"{demo_url}/api/orders").json()["value"]

    leftovers = [item for item in orders if item["title"].startswith(ORDER_PREFIX)]
    assert leftovers == [], f"Тесты оставили после себя заказы: {leftovers}"

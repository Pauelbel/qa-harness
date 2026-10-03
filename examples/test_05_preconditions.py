"""Пример: предусловия и постусловия через фикстуры с ``yield``.

Тест не создаёт и не удаляет данные сам. Предусловие (создать заказ через API)
и постусловие (удалить его) описаны один раз в фикстуре, а тест просто просит её
по имени. Код после ``yield`` выполняется всегда, даже если тест упал.

Правила, которые показывает пример:
- данные уникальны для каждого запуска (префикс ``autotest-`` и случайный хвост);
- данные создаются через API, а не кликами в интерфейсе;
- ошибка очистки пишется в лог и не затирает настоящую причину падения теста;
- если нужно несколько заказов в одном тесте, используется фабрика.

UI-часть запускается, когда установлен Chromium и задано ``EXAMPLE_UI=1``.
"""

import logging
import os
from collections.abc import Callable, Iterator
from uuid import uuid4

import allure
import pytest
from playwright.sync_api import Page, expect

from qa_core.clients.http import BaseHttpClient

logger = logging.getLogger(__name__)

ORDER_PREFIX = "autotest-"


def create_order(base_url: str) -> dict:
    """Создаёт заказ через API и возвращает его данные."""
    title = f"{ORDER_PREFIX}{uuid4().hex[:8]}"
    with BaseHttpClient() as http:
        response = http.post(f"{base_url}/api/orders", json={"title": title})
    response.raise_for_status()
    return response.json()


def delete_order(base_url: str, order_id: int) -> None:
    """Удаляет заказ. Ошибка очистки логируется, чтобы не скрыть падение теста."""
    try:
        with BaseHttpClient() as http:
            response = http.delete(f"{base_url}/api/orders/{order_id}")
        response.raise_for_status()
    except Exception:
        logger.exception("Не удалось удалить тестовый заказ %s", order_id)


@pytest.fixture
def order(demo_url: str) -> Iterator[dict]:
    """Один заказ: создаётся до теста, удаляется после него."""
    created = create_order(demo_url)
    yield created
    delete_order(demo_url, created["id"])


@pytest.fixture
def order_factory(demo_url: str) -> Iterator[Callable[[], dict]]:
    """Фабрика заказов для тестов, которым нужно несколько штук. Удаляет всё созданное."""
    created: list[dict] = []

    def make() -> dict:
        created.append(create_order(demo_url))
        return created[-1]

    yield make
    for item in created:
        delete_order(demo_url, item["id"])


@allure.epic("Примеры")
@allure.title("Предусловие: заказ создан через API до теста")
def test_order_exists_via_api(order: dict, demo_url: str) -> None:
    with BaseHttpClient() as http:
        orders = http.get(f"{demo_url}/api/orders").json()["value"]

    assert order in orders


@allure.epic("Примеры")
@allure.title("Фабрика: несколько заказов в одном тесте, все удаляются после него")
def test_factory_creates_several_orders(order_factory: Callable[[], dict], demo_url: str) -> None:
    first, second = order_factory(), order_factory()

    with BaseHttpClient() as http:
        orders = http.get(f"{demo_url}/api/orders").json()["value"]

    assert first in orders and second in orders
    assert first["id"] != second["id"]


@allure.epic("Примеры")
@allure.title("Предусловие и UI: созданный через API заказ виден на странице")
@pytest.mark.skipif(
    os.getenv("EXAMPLE_UI") != "1",
    reason="Установите браузер (python -m playwright install chromium) и задайте EXAMPLE_UI=1",
)
def test_order_visible_in_ui(browser_page: Page, order: dict, demo_url: str) -> None:
    with allure.step("Открыть страницу заказов"):
        browser_page.goto(f"{demo_url}/orders")

    with allure.step("Проверить, что созданный заказ отображается"):
        expect(browser_page.get_by_text(order["title"])).to_be_visible()


@allure.epic("Примеры")
@allure.title("Постусловие: после предыдущих тестов тестовых заказов не осталось")
def test_no_leftovers(demo_url: str) -> None:
    with BaseHttpClient() as http:
        orders = http.get(f"{demo_url}/api/orders").json()["value"]

    leftovers = [item for item in orders if item["title"].startswith(ORDER_PREFIX)]
    assert leftovers == [], f"Тесты оставили после себя заказы: {leftovers}"

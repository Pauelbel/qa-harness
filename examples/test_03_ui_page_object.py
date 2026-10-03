"""Пример: UI-тест с предусловием через API и Page Object.

Как устроен тест:
1. Предусловие. Фикстура ``order`` (conftest.py) создаёт заказ через API: быстро и
   без кликов по интерфейсу. После теста она сама его удаляет.
2. Страница. Фикстура ``orders_page`` отдаёт готовый Page Object (pages/orders_page.py).
3. Тест. Только понятные шаги: открыть страницу, проверить заказ.

Запускается, когда установлен Chromium (``python -m playwright install chromium``)
и задана переменная ``EXAMPLE_UI=1``. В Docker это уже сделано.
"""

import os
from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from pages.orders_page import OrdersPage

pytestmark = [
    pytest.mark.ui,
    pytest.mark.skipif(
        os.getenv("EXAMPLE_UI") != "1",
        reason="Установите браузер (python -m playwright install chromium) и задайте EXAMPLE_UI=1",
    ),
]


@pytest.fixture
def orders_page(browser_page: Page, demo_url: str) -> OrdersPage:
    """Page Object страницы заказов поверх страницы браузера."""
    return OrdersPage(browser_page, demo_url)


@pytest.mark.smoke
def test_order_created_via_api_is_visible(orders_page: OrdersPage, order: dict) -> None:
    orders_page.open()

    orders_page.expect_order_visible(order["title"])


def test_several_orders_are_visible(
    orders_page: OrdersPage, order_factory: Callable[[], dict]
) -> None:
    first, second = order_factory(), order_factory()

    orders_page.open()

    orders_page.expect_order_visible(first["title"])
    orders_page.expect_order_visible(second["title"])

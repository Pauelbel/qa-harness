"""ШАБЛОН UI-теста. Скопируйте в tests/ui/, переименуйте и замените данные.

1. Скопируйте:  cp templates/test_ui_template.py tests/ui/test_<тема>.py
2. Опишите страницу классом в pages/ (образец: examples/pages/orders_page.py).
3. Замените адрес, фикстуры и шаги (места с «ЗАМЕНИТЕ»).
4. Запустите:   python -m pytest tests/ui/test_<тема>.py

Нужен плагин qa_core.pytest_plugins.playwright в conftest.py.
Правила: в тесте нет локаторов и кликов (их прячет Page Object), данные создаются
через API фикстурой, time.sleep не нужен (expect сам ждёт). При падении скриншот
и trace лежат в test-artifacts/.
"""

import os

import pytest
from playwright.sync_api import Page, expect

# ЗАМЕНИТЕ: импортируйте свой Page Object и соберите его фикстурой.
# from pages.orders_page import OrdersPage
#
# @pytest.fixture
# def orders_page(browser_page: Page) -> OrdersPage:
#     return OrdersPage(browser_page, BASE_URL)

pytestmark = pytest.mark.ui

BASE_URL = os.getenv("BASE_URL", "https://example.com")  # ЗАМЕНИТЕ


@pytest.mark.smoke
def test_replace_me(browser_page: Page):  # browser_page: чистая страница из ядра
    # Подготовка: нужны данные? Попросите фикстуру, она создаст их через API.

    # Действие
    browser_page.goto(BASE_URL)  # ЗАМЕНИТЕ: orders_page.open()

    # Проверка
    expect(browser_page).to_have_title("Example Domain")  # ЗАМЕНИТЕ: orders_page.expect_...

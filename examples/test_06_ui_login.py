"""Пример: UI-тесты в одном файле и вход в систему один раз на весь запуск.

Локаторы пишутся прямо в тестах, а повторяющийся вход вынесен в обычную функцию
``login`` в этом же файле. Отдельные файлы Page Object не нужны: смотрите тест
и видите всё, что он делает.

Фикстура ``qa_storage_state`` из плагина ``playwright`` по умолчанию возвращает
``None``. Здесь она переопределена: браузер входит в систему один раз и сохраняет
cookies, а каждый тест получает чистую страницу уже с этим входом. Скриншот и
trace при падении по-прежнему прикладывает плагин.

Пример запускается, когда установлен Chromium (``python -m playwright install
chromium``) и задана переменная ``EXAMPLE_UI=1``.
"""

import os

import allure
import pytest
from playwright.sync_api import Browser, Page, expect

from conftest import DEMO_LOGIN, DEMO_PASSWORD

pytestmark = pytest.mark.skipif(
    os.getenv("EXAMPLE_UI") != "1",
    reason="Установите браузер (python -m playwright install chromium) и задайте EXAMPLE_UI=1",
)


def login(page: Page, base_url: str, username: str, password: str) -> None:
    """Входит в систему. Это единственное повторяющееся действие, поэтому оно вынесено."""
    page.goto(f"{base_url}/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign In").click()
    # Ждём признак успешного входа, а не «тишину в сети».
    page.wait_for_url("**/dashboard")


@pytest.fixture(scope="session")
def qa_storage_state(qa_browser: Browser, demo_url: str) -> dict:
    """Входит в систему один раз и возвращает состояние браузера для всех тестов."""
    context = qa_browser.new_context()
    login(context.new_page(), demo_url, DEMO_LOGIN, DEMO_PASSWORD)
    state = context.storage_state()
    context.close()
    return state


@allure.epic("Примеры")
@allure.title("UI: тест начинается уже после входа")
def test_dashboard_links(browser_page: Page, demo_url: str) -> None:
    with allure.step("Открыть стартовую страницу"):
        browser_page.goto(f"{demo_url}/dashboard")

    with allure.step("Проверить ссылки"):
        expect(browser_page.get_by_role("link", name="Чат поддержки")).to_be_visible()
        expect(browser_page.get_by_role("link", name="Руководство пользователя")).to_be_visible()

    with allure.step("Проверить контакт поддержки"):
        expect(browser_page.locator("section")).to_contain_text("support@example.com")


@allure.epic("Примеры")
@allure.title("UI: каждый тест получает отдельную страницу с тем же входом")
def test_second_test_is_still_logged_in(browser_page: Page, demo_url: str) -> None:
    browser_page.goto(f"{demo_url}/dashboard")

    expect(browser_page).to_have_url(f"{demo_url}/dashboard")
    expect(browser_page.get_by_role("heading")).to_have_text("Стартовая страница")


@allure.epic("Примеры")
@allure.title("UI: без входа стартовая страница перенаправляет на логин")
def test_login_required(qa_browser: Browser, demo_url: str) -> None:
    context = qa_browser.new_context()  # чистый контекст без сохранённого входа
    page = context.new_page()

    page.goto(f"{demo_url}/dashboard")

    expect(page).to_have_url(f"{demo_url}/login")
    context.close()

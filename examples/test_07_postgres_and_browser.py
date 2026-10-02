"""Примеры, которым нужны внешние системы: PostgreSQL и браузер.

Они пропускаются, пока окружение не подготовлено, чтобы остальные примеры
запускались везде.
"""

import os

import allure
import pytest
from playwright.sync_api import Page, expect

from qa_core.clients.postgres import PostgresClient


@allure.epic("Примеры")
@allure.title("PostgreSQL: запрос с параметрами")
@pytest.mark.skipif(
    not os.getenv("EXAMPLE_PG_HOST"),
    reason="Задайте EXAMPLE_PG_HOST, EXAMPLE_PG_DB, EXAMPLE_PG_USER, EXAMPLE_PG_PASSWORD",
)
def test_postgres_query() -> None:
    db = PostgresClient(
        dbname=os.environ["EXAMPLE_PG_DB"],
        user=os.environ["EXAMPLE_PG_USER"],
        password=os.environ["EXAMPLE_PG_PASSWORD"],
        host=os.environ["EXAMPLE_PG_HOST"],
    )

    rows = db.fetch_all("SELECT %s::int", [1])

    assert rows == [(1,)]


@allure.epic("Примеры")
@allure.title("Браузер: страница из фикстуры browser_page")
@pytest.mark.skipif(
    os.getenv("EXAMPLE_UI") != "1",
    reason="Установите браузер (python -m playwright install chromium) и задайте EXAMPLE_UI=1",
)
def test_browser_page(browser_page: Page) -> None:
    browser_page.set_content("<h1>Привет</h1><a href='#'>Ссылка</a>")

    expect(browser_page.get_by_role("heading")).to_have_text("Привет")
    expect(browser_page.get_by_role("link", name="Ссылка")).to_be_visible()

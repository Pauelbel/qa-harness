"""Пример: проверки ответа OData."""

import allure
from pydantic import BaseModel

from qa_core.checks.odata import OdataAssertions
from qa_core.clients.http import BaseHttpClient


class OrderDto(BaseModel):
    """Модель ответа живёт в проекте: ядро о ней ничего не знает."""

    Id: int
    Title: str
    Status: str


@allure.epic("Примеры")
@allure.title("OData: структура и фильтр")
def test_orders(demo_url: str) -> None:
    with BaseHttpClient() as http:
        items = http.get(f"{demo_url}/api/items").json()["value"]

    # Проверки мягкие: тест покажет все найденные ошибки, а не только первую.
    OdataAssertions.response_not_empty(items)
    OdataAssertions.schema(items, OrderDto)
    OdataAssertions.top_limit(items, 10)
    OdataAssertions.filter_eq(items, "Status", "Draft")
    OdataAssertions.orderby(items, "Id")

"""Пример: HTTP-клиент и проектный клиент поверх него."""

import allure

from qa_core.clients.http import BaseHttpClient


class ItemsApiClient:
    """Проектный клиент: знает адрес и авторизацию, а транспорт берёт из qa-core."""

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": token}

    def get_items(self):
        with BaseHttpClient() as http:
            return http.get(f"{self.base_url}/api/items", headers=self.headers)


@allure.epic("Примеры")
@allure.title("HTTP: простой GET-запрос")
def test_simple_get(demo_url: str) -> None:
    with BaseHttpClient() as http:
        response = http.get(f"{demo_url}/api/items?token=secret", timeout=10)

    response.raise_for_status()
    assert response.json()["value"]


@allure.epic("Примеры")
@allure.title("HTTP: проектный клиент поверх BaseHttpClient")
def test_project_client(demo_url: str) -> None:
    client = ItemsApiClient(demo_url, token="Bearer example")

    response = client.get_items()

    assert response.status_code == 200
    assert len(response.json()["value"]) == 2

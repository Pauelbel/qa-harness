"""Подключение плагинов и демо-сервер для примеров.

Примеры работают без внешних систем: сервер поднимается в тестах сам.
Запуск из корня репозитория:  python -m pytest examples
"""

import json
import logging
from collections.abc import Callable, Iterator
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from threading import Lock, Thread
from uuid import uuid4

import pytest

from qa_core.clients.http import BaseHttpClient

logger = logging.getLogger(__name__)

# Так проект подключает плагины ядра. Не нужен плагин: удалите строку.
# Нужен Allure: добавьте "qa_core.pytest_plugins.allure_reporting" (и pip install allure-pytest).
pytest_plugins = [
    "qa_core.pytest_plugins.fixtures",    # маркеры и фикстура http_client
    "qa_core.pytest_plugins.logging",     # логи в консоль и в logs/
    "qa_core.pytest_plugins.playwright",  # фикстура browser_page (нужен набор ui)
]

ITEMS = [
    {"Id": 1, "Title": "Первый заказ", "Status": "Draft"},
    {"Id": 2, "Title": "Второй заказ", "Status": "Draft"},
]

# Заказы демо-сервиса лежат в памяти: так видно создание и удаление данных.
ORDERS: dict[int, str] = {}
ORDERS_LOCK = Lock()
_next_order_id = count(1)

ORDERS_PAGE = """<!doctype html><html lang="ru"><head><title>Заказы</title></head><body>
<h1>Заказы</h1>
<ul>{rows}</ul></body></html>"""


class DemoHandler(BaseHTTPRequestHandler):
    """Демо-сервис: список позиций, API заказов и страница заказов."""

    def do_GET(self) -> None:
        if self.path == "/api/orders":
            with ORDERS_LOCK:
                orders = [{"id": key, "title": title} for key, title in ORDERS.items()]
            self._send(200, json.dumps({"value": orders}).encode("utf-8"), "application/json")
        elif self.path == "/orders":
            with ORDERS_LOCK:
                rows = "".join(f"<li>{escape(title)}</li>" for title in ORDERS.values())
            self._send(200, ORDERS_PAGE.format(rows=rows).encode("utf-8"), "text/html; charset=utf-8")
        elif self.path.startswith("/api/items"):
            self._send(200, json.dumps({"value": ITEMS}).encode("utf-8"), "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        raw_body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path != "/api/orders":
            self._send(404, b"not found", "text/plain")
            return
        title = json.loads(raw_body)["title"]
        with ORDERS_LOCK:
            order_id = next(_next_order_id)
            ORDERS[order_id] = title
        body = json.dumps({"id": order_id, "title": title}).encode("utf-8")
        self._send(201, body, "application/json")

    def do_DELETE(self) -> None:
        prefix = "/api/orders/"
        order_id = int(self.path[len(prefix):]) if self.path.startswith(prefix) else None
        with ORDERS_LOCK:
            removed = ORDERS.pop(order_id, None) if order_id is not None else None
        if removed is None:
            self._send(404, b"not found", "text/plain")
        else:
            self._send(204, b"", "text/plain")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:  # noqa: A002 - тишина в консоли
        pass


@pytest.fixture(scope="session")
def demo_url() -> Iterator[str]:
    """Адрес локального демо-сервера, он живёт на время всех примеров."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


# --- Общие предусловия -------------------------------------------------------
# Заказ нужен и API-, и UI-тестам, поэтому фикстуры лежат здесь. Если он нужен
# одному файлу, фикстуру стоит описать в самом файле.

ORDER_PREFIX = "autotest-"


def create_order(base_url: str) -> dict:
    """Создаёт заказ через API и возвращает его данные."""
    title = f"{ORDER_PREFIX}{uuid4().hex[:8]}"
    with BaseHttpClient() as http:
        response = http.post(f"{base_url}/api/orders", json={"title": title})
    response.raise_for_status()
    return response.json()


def delete_order(base_url: str, order_id: int) -> None:
    """Удаляет заказ. Ошибка очистки пишется в лог и не скрывает падение теста."""
    try:
        with BaseHttpClient() as http:
            http.delete(f"{base_url}/api/orders/{order_id}").raise_for_status()
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
    """Фабрика для тестов, которым нужно несколько заказов. Удаляет всё созданное."""
    created: list[dict] = []

    def make() -> dict:
        created.append(create_order(demo_url))
        return created[-1]

    yield make
    for item in created:
        delete_order(demo_url, item["id"])

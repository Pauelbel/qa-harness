"""Общие настройки примеров: подключение плагинов и демо-сервер.

Примеры работают без внешних систем. Запуск из корня репозитория:

    python -m pytest examples

Здесь же показано, как проект подключает плагины qa-core: списком в conftest.py.
"""

import json
from html import escape
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from itertools import count
from threading import Lock, Thread
from urllib.parse import parse_qs, quote

import pandas as pd
import pytest

pytest_plugins = [
    "qa_core.pytest_plugins.logging",           # логи в консоль и в logs/
    "qa_core.pytest_plugins.allure_reporting",  # логи упавшего теста в Allure
    "qa_core.pytest_plugins.playwright",        # фикстура browser_page
    "demo_plugin",                              # плагин проекта, см. demo_plugin.py
]

ITEMS = [
    {"Id": 1, "Title": "Первый заказ", "Status": "Draft"},
    {"Id": 2, "Title": "Второй заказ", "Status": "Draft"},
]


def make_report_bytes() -> bytes:
    """Собирает небольшой Excel-отчёт, как его мог бы отдать сервис."""
    table = pd.DataFrame(
        {
            "ФИО": ["Иванов Иван Иванович", "Петров Пётр Петрович"],
            "Дата": ["01.09.2026", "02.09.2026"],
            "Часы": [8, 7.5],
        }
    )
    buffer = BytesIO()
    table.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


# Тестовые данные демо-сервера: они существуют только внутри примеров.
DEMO_LOGIN = "demo-user"
DEMO_PASSWORD = "demo-password"
SESSION_COOKIE = "demo_session=ok"

LOGIN_PAGE = """<!doctype html><html lang="ru"><head><title>Вход</title></head><body>
<h1>Вход</h1>
<form method="post" action="/login">
  <label>Username <input name="username" type="text"></label>
  <label>Password <input name="password" type="password"></label>
  <button type="submit">Sign In</button>
</form></body></html>"""

DASHBOARD_PAGE = """<!doctype html><html lang="ru"><head><title>Стартовая</title></head><body>
<h1>Стартовая страница</h1>
<section>
  <a href="#chat">Чат поддержки</a>
  <a href="#guide">Руководство пользователя</a>
  <p>Почта поддержки: support@example.com</p>
</section></body></html>"""


# Заказы демо-сервиса хранятся в памяти: пример показывает создание и удаление данных.
ORDERS: dict[int, str] = {}
ORDERS_LOCK = Lock()
_next_order_id = count(1)

ORDERS_PAGE = """<!doctype html><html lang="ru"><head><title>Заказы</title></head><body>
<h1>Заказы</h1>
<ul>{rows}</ul></body></html>"""


class DemoHandler(BaseHTTPRequestHandler):
    """Демо-сервис: JSON, Excel-файл, вход, стартовая страница и заказы."""

    def do_GET(self) -> None:
        if self.path == "/login":
            self._send(200, LOGIN_PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/dashboard":
            if SESSION_COOKIE in self.headers.get("Cookie", ""):
                self._send(200, DASHBOARD_PAGE.encode("utf-8"), "text/html; charset=utf-8")
            else:
                self._send(302, b"", "text/plain", {"Location": "/login"})
        elif self.path == "/api/orders":
            with ORDERS_LOCK:
                orders = [{"id": key, "title": title} for key, title in ORDERS.items()]
            self._send(200, json.dumps({"value": orders}).encode("utf-8"), "application/json")
        elif self.path == "/orders":
            with ORDERS_LOCK:
                rows = "".join(f"<li>{escape(title)}</li>" for title in ORDERS.values())
            self._send(200, ORDERS_PAGE.format(rows=rows).encode("utf-8"), "text/html; charset=utf-8")
        elif self.path.startswith("/api/items"):
            body = json.dumps({"value": ITEMS}).encode("utf-8")
            self._send(200, body, "application/json")
        elif self.path == "/report":
            filename = quote("Отчёт.xlsx")
            self._send(
                200,
                make_report_bytes(),
                "application/octet-stream",
                {"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
            )
        else:
            self._send(404, b"not found", "text/plain")

    def do_DELETE(self) -> None:
        prefix = "/api/orders/"
        order_id = int(self.path[len(prefix):]) if self.path.startswith(prefix) else None
        with ORDERS_LOCK:
            removed = ORDERS.pop(order_id, None) if order_id is not None else None
        if removed is None:
            self._send(404, b"not found", "text/plain")
        else:
            self._send(204, b"", "text/plain")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length)
        if self.path == "/api/orders":
            title = json.loads(raw_body)["title"]
            with ORDERS_LOCK:
                order_id = next(_next_order_id)
                ORDERS[order_id] = title
            body = json.dumps({"id": order_id, "title": title}).encode("utf-8")
            self._send(201, body, "application/json")
            return

        form = parse_qs(raw_body.decode("utf-8"))
        valid = (
            self.path == "/login"
            and form.get("username") == [DEMO_LOGIN]
            and form.get("password") == [DEMO_PASSWORD]
        )
        if valid:
            self._send(
                302,
                b"",
                "text/plain",
                {"Location": "/dashboard", "Set-Cookie": f"{SESSION_COOKIE}; Path=/"},
            )
        else:
            self._send(401, "Неверный логин или пароль".encode("utf-8"), "text/plain; charset=utf-8")

    def _send(self, status: int, body: bytes, content_type: str, headers=None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:  # noqa: A002 — тишина в консоли
        pass


@pytest.fixture(scope="session")
def demo_url() -> Iterator[str]:
    """Адрес локального демо-сервера, который живёт на время всех примеров."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()

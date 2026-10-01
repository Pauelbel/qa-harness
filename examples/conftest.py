"""Общие настройки примеров: подключение плагинов и демо-сервер.

Примеры работают без внешних систем. Запуск из корня репозитория:

    python -m pytest examples

Здесь же показано, как проект подключает плагины qa-core: списком в conftest.py.
"""

import json
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from threading import Thread
from urllib.parse import quote

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


class DemoHandler(BaseHTTPRequestHandler):
    """Две ручки: JSON со списком и Excel-файл с именем в заголовке."""

    def do_GET(self) -> None:
        if self.path.startswith("/api/items"):
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

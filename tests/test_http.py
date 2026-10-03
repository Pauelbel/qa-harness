"""Проверки HTTP-клиента с подставной сессией и локальным HTTP-сервером."""

from datetime import timedelta
from pathlib import Path

from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import subprocess
import sys
from threading import Thread
import pytest

from qa_core.clients.http import BaseHttpClient


class FakeResponse:
    def __init__(self, text: str = "response body") -> None:
        self.text = text
        self.ok = True
        self.status_code = 200
        self.elapsed = timedelta(milliseconds=25)


class FakeSession:
    def __init__(self, response: FakeResponse | None = None) -> None:
        self.response = response or FakeResponse()
        self.calls: list[tuple[str, str, dict]] = []
        self.closed = False

    def request(self, method: str, url: str, **kwargs) -> FakeResponse:
        self.calls.append((method, url, kwargs))
        return self.response

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def http_config_path(tmp_path: Path) -> Path:
    """Создаёт YAML, нужный только тестам HTTP-клиента."""
    pytest.importorskip("pydantic")
    pytest.importorskip("yaml")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """http:
  max_logged_response_body_length: 5
  sensitive_query_parameters:
    - token
    - api_key
""",
        encoding="utf-8",
    )
    return config_path


def test_safe_url_masks_configured_query_parameters() -> None:
    client = BaseHttpClient(
        session=FakeSession(), sensitive_query_parameters=["TOKEN"]
    )
    safe_url = client._safe_url(
        "https://service.example/items?token=secret&visible=yes"
    )
    assert "secret" not in safe_url
    assert "token=***" in safe_url
    assert "visible=yes" in safe_url


def test_get_returns_original_full_response() -> None:
    response = FakeResponse(text="123456789")
    session = FakeSession(response)
    client = BaseHttpClient(session=session, max_logged_response_body_length=5)

    actual = client.get("https://service.example/items", timeout=10)

    assert actual is response
    assert actual.text == "123456789"
    assert session.calls == [
        ("get", "https://service.example/items", {"timeout": 10})
    ]
    assert client._short_body(response).startswith("12345…")


def test_context_manager_closes_owned_session(
    monkeypatch,
) -> None:
    session = FakeSession()
    monkeypatch.setattr("qa_core.clients.http.requests.Session", lambda: session)

    with BaseHttpClient():
        pass

    assert session.closed is True


def test_explicit_yaml_and_parameter_override(http_config_path: Path) -> None:
    """Явный YAML поддерживается, параметры имеют приоритет над ним."""
    client = BaseHttpClient(session=FakeSession(), config_path=http_config_path)
    assert client._short_body(FakeResponse("123456789")).startswith("12345…")
    assert "secret" not in client._safe_url("https://service.example/?token=secret")
    override = BaseHttpClient(
        session=FakeSession(),
        config_path=http_config_path,
        max_logged_response_body_length=3,
        sensitive_query_parameters=[],
    )
    assert override._short_body(FakeResponse("123456789")).startswith("123…")
    assert "secret" in override._safe_url("https://service.example/?token=secret")


def test_core_without_optional_dependencies(tmp_path: Path) -> None:
    """Клиент работает без YAML-файла и импортов необязательных расширений."""
    script = """
import importlib.abc
import sys

class BlockOptionalImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'allure', 'playwright', 'psycopg2', 'openpyxl', 'pandas', 'hvac'}:
            raise ImportError('Необязательная зависимость: ' + fullname)

sys.meta_path.insert(0, BlockOptionalImports())
from qa_core.clients.http import BaseHttpClient
with BaseHttpClient() as client:
    assert 'secret' not in client._safe_url('https://example.com/?token=secret')
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


def test_get_from_local_server(tmp_path: Path, monkeypatch) -> None:
    """Настоящий GET проходит без общего конфига и внешнего сервиса."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = b'{"status": "ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args) -> None:
            pass

    monkeypatch.chdir(tmp_path)
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with BaseHttpClient() as client:
            client.session.trust_env = False
            response = client.get(
                f"http://127.0.0.1:{server.server_port}/items", timeout=5
            )
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_default_timeout_is_applied(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("http:\n  timeout: 7\n", encoding="utf-8")
    session = FakeSession()
    client = BaseHttpClient(session=session, config_path=config_path)

    client.get("https://service.example/items")

    assert session.calls[0][2]["timeout"] == 7


def test_explicit_timeout_wins(tmp_path: Path) -> None:
    session = FakeSession()
    client = BaseHttpClient(session=session, config_path=tmp_path / "нет.yaml")

    client.get("https://service.example/items", timeout=3)
    client.get("https://service.example/items", timeout=None)

    assert session.calls[0][2]["timeout"] == 3
    assert session.calls[1][2]["timeout"] is None


def test_timeout_default_is_thirty_seconds(tmp_path: Path) -> None:
    session = FakeSession()
    client = BaseHttpClient(session=session, config_path=tmp_path / "нет.yaml")

    client.get("https://service.example/items")

    assert session.calls[0][2]["timeout"] == 30

"""Проверки HTTP-клиента без сетевых запросов."""

from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

import allure
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


@allure.epic("Backend")
@allure.title("Маскирование чувствительных query-параметров")
def test_safe_url_masks_configured_query_parameters(
    http_config_path: Path,
) -> None:
    with allure.step("Сформировать URL для лога"):
        client = BaseHttpClient(session=FakeSession(), config_path=http_config_path)
        safe_url = client._safe_url(
            "https://service.example/items?token=secret&visible=yes"
        )

    with allure.step("Проверить маскирование"):
        assert "secret" not in safe_url
        assert "token=***" in safe_url
        assert "visible=yes" in safe_url


@allure.epic("Backend")
@allure.title("HTTP-клиент возвращает исходный response")
def test_get_returns_original_full_response(http_config_path: Path) -> None:
    response = FakeResponse(text="123456789")
    session = FakeSession(response)
    client = BaseHttpClient(session=session, config_path=http_config_path)

    with allure.step("Отправить GET-запрос"):
        actual = client.get("https://service.example/items", timeout=10)

    with allure.step("Проверить response и диагностическое сокращение"):
        assert actual is response
        assert actual.text == "123456789"
        assert session.calls == [
            ("get", "https://service.example/items", {"timeout": 10})
        ]
        assert client._short_body(response).startswith("12345…")


@allure.epic("Backend")
@allure.title("HTTP-клиент закрывает созданную сессию")
def test_context_manager_closes_owned_session(
    http_config_path: Path,
    monkeypatch,
) -> None:
    session = FakeSession()
    monkeypatch.setattr("qa_core.clients.http.requests.Session", lambda: session)

    with allure.step("Открыть и закрыть HTTP-клиент"):
        with BaseHttpClient(config_path=http_config_path):
            pass

    with allure.step("Проверить закрытие сессии"):
        assert session.closed is True


@allure.epic("Backend")
@allure.title("HTTP-клиент подставляет таймаут из настроек, если он не указан")
def test_default_timeout_is_applied(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("http:\n  timeout: 7\n", encoding="utf-8")
    session = FakeSession()
    client = BaseHttpClient(session=session, config_path=config_path)

    client.get("https://service.example/items")

    assert session.calls[0][2]["timeout"] == 7


@allure.epic("Backend")
@allure.title("HTTP-клиент оставляет таймаут, переданный в вызове")
def test_explicit_timeout_wins(tmp_path: Path) -> None:
    session = FakeSession()
    client = BaseHttpClient(session=session, config_path=tmp_path / "нет.yaml")

    client.get("https://service.example/items", timeout=3)
    client.get("https://service.example/items", timeout=None)

    assert session.calls[0][2]["timeout"] == 3
    assert session.calls[1][2]["timeout"] is None


@allure.epic("Backend")
@allure.title("Без настроек таймаут по умолчанию — 30 секунд")
def test_timeout_default_is_thirty_seconds(tmp_path: Path) -> None:
    session = FakeSession()
    client = BaseHttpClient(session=session, config_path=tmp_path / "нет.yaml")

    client.get("https://service.example/items")

    assert session.calls[0][2]["timeout"] == 30


@allure.epic("Backend")
@allure.title("Параметры конструктора важнее значений из config.yaml")
def test_constructor_arguments_override_config(http_config_path: Path) -> None:
    client = BaseHttpClient(
        session=FakeSession(),
        config_path=http_config_path,
        sensitive_query_parameters=["TOKEN"],
        max_logged_response_body_length=3,
    )

    assert "token=***" in client._safe_url("https://service.example/?token=secret")
    assert "api_key=abc" in client._safe_url("https://service.example/?api_key=abc")
    assert client._short_body(FakeResponse(text="123456789")).startswith("123…")


@allure.epic("Backend")
@allure.title("Настоящий GET проходит через локальный сервер")
def test_get_from_local_server(tmp_path: Path, monkeypatch) -> None:
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
            response = client.get(f"http://127.0.0.1:{server.server_port}/items", timeout=5)
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

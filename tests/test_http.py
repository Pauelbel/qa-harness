"""Проверки HTTP-клиента без сетевых запросов."""

from datetime import timedelta
from pathlib import Path

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

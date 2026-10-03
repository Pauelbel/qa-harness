"""Базовый HTTP-транспорт для проектных API-клиентов.

Зачем нужен файл:
    Здесь находятся только отправка запросов, управление ``requests.Session``
    и диагностическое логирование. Эндпоинтов, авторизации и моделей конкретной
    системы здесь быть не должно — их добавляет клиент проекта.

Как использовать:
    Создайте ``BaseHttpClient`` самостоятельно или передайте готовую session,
    затем вызывайте ``get``, ``post``, ``put`` и ``delete``. Контекстный менеджер
    автоматически закроет session, созданную самим клиентом.

    >>> with BaseHttpClient() as http:
    ...     response = http.get("https://service.example/api/items", timeout=10)
    ...     response.raise_for_status()

Настройки маскирования URL и длины ответа передаются через параметры.
Для совместимости YAML загружается только при явном указании ``config_path``.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path
from types import TracebackType
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

logger = logging.getLogger(__name__)


class BaseHttpClient:
    """Выполняет HTTP-запросы через переданную или собственную сессию."""

    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        print_response: bool = False,
        config_path: str | Path | None = None,
        sensitive_query_parameters: Iterable[str] | None = None,
        max_logged_response_body_length: int | None = None,
    ) -> None:
        if config_path is not None:
            from qa_core.config import load_settings

            settings = load_settings(config_path).http
            if sensitive_query_parameters is None:
                sensitive_query_parameters = settings.sensitive_query_parameters
            if max_logged_response_body_length is None:
                max_logged_response_body_length = settings.max_logged_response_body_length

        if sensitive_query_parameters is None:
            sensitive_query_parameters = (
                "token", "access_token", "api_key", "key", "password"
            )
        if max_logged_response_body_length is None:
            max_logged_response_body_length = 2000
        if max_logged_response_body_length < 0:
            raise ValueError("Длина тела ответа в логе не может быть отрицательной")

        self._sensitive_query_parameters = frozenset(
            name.lower() for name in sensitive_query_parameters
        )
        self._max_logged_response_body_length = max_logged_response_body_length
        self.session = session or requests.Session()
        self.print_response = print_response
        self._owns_session = session is None

    def _safe_url(self, url: str) -> str:
        """Скрывает чувствительные параметры запроса перед записью в лог."""
        parsed = urlsplit(url)
        query = urlencode(
            [
                (
                    key,
                    "***"
                    if key.lower() in self._sensitive_query_parameters
                    else value,
                )
                for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            ]
        )
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))

    def _short_body(self, response: requests.Response) -> str:
        """Возвращает ограниченный фрагмент ответа для диагностики ошибки."""
        body = response.text.strip()
        if len(body) <= self._max_logged_response_body_length:
            return body
        return (
            f"{body[:self._max_logged_response_body_length]}… "
            "[ответ сокращён в логе]"
        )

    def _request(self, method: str, full_url: str, **kwargs) -> requests.Response:
        safe_url = self._safe_url(full_url)
        method_name = method.upper()

        try:
            response = self.session.request(method, full_url, **kwargs)
        except requests.RequestException:
            logger.exception("%s %s → ошибка подключения", method_name, safe_url)
            raise

        elapsed = response.elapsed.total_seconds()
        log_message = "%s %s → %s за %.3f сек."
        if response.ok:
            logger.info(log_message, method_name, safe_url, response.status_code, elapsed)
        else:
            logger.error(log_message, method_name, safe_url, response.status_code, elapsed)
            body = self._short_body(response)
            if body:
                logger.error("Ответ сервиса: %s", body)

        if self.print_response:
            logger.debug("Тело ответа: %s", self._short_body(response))
        return response

    def close(self) -> None:
        """Закрывает сессию, если клиент создал её самостоятельно."""
        if self._owns_session:
            self.session.close()

    def __enter__(self) -> BaseHttpClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self.close()
        return False

    def get(self, *args, **kwargs) -> requests.Response:
        return self._request("get", *args, **kwargs)

    def post(self, *args, **kwargs) -> requests.Response:
        return self._request("post", *args, **kwargs)

    def put(self, *args, **kwargs) -> requests.Response:
        return self._request("put", *args, **kwargs)

    def delete(self, *args, **kwargs) -> requests.Response:
        return self._request("delete", *args, **kwargs)

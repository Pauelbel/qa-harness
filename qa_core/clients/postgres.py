"""Минимальный клиент для чтения данных из PostgreSQL.

Зачем нужен файл:
    Клиент скрывает повторяющийся код открытия соединения и курсора. Он не знает
    таблиц, схем и SQL конкретного проекта и поэтому подходит разным тестам.

Как использовать:
    Передайте параметры подключения, затем вызовите ``fetch_all`` с SQL и,
    при необходимости, отдельными параметрами запроса.

    >>> db = PostgresClient("app", "tester", "secret", host="db.example")
    >>> rows = db.fetch_all("SELECT id FROM orders WHERE status = %s", ["new"])

Соединение создаётся на время одного вызова и закрывается автоматически.
"""

from __future__ import annotations

from contextlib import closing
from typing import Any, Sequence

import psycopg2


class PostgresClient:
    """Открывает соединение на время запроса и возвращает все строки."""

    def __init__(
        self,
        dbname: str,
        user: str,
        password: str,
        host: str = "localhost",
        port: str | int = "5432",
    ) -> None:
        self.connection_params = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port,
        }

    def fetch_all(
        self,
        query: str,
        params: Sequence[Any] | None = None,
    ) -> list[tuple[Any, ...]]:
        """Выполняет SELECT и возвращает все найденные строки."""
        # Контекст самого соединения psycopg2 лишь завершает транзакцию и не
        # закрывает соединение, поэтому закрытие выполняется отдельно.
        with closing(psycopg2.connect(**self.connection_params)) as connection:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, params)
                    return cursor.fetchall()

"""Проверки PostgreSQL-клиента без реальной базы данных."""

from unittest.mock import MagicMock

import allure

from qa_core.clients import postgres
from qa_core.clients.postgres import PostgresClient


@allure.epic("Backend")
@allure.title("PostgreSQL-клиент выполняет параметризованный запрос")
def test_fetch_all_executes_parameterized_query(monkeypatch) -> None:
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = [(1,), (2,)]
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr(postgres.psycopg2, "connect", connect)

    client = PostgresClient(
        dbname="app",
        user="tester",
        password="secret",
        host="db.example",
        port=5432,
    )
    with allure.step("Выполнить SELECT с параметром"):
        rows = client.fetch_all("SELECT id FROM orders WHERE status = %s", ["new"])

    with allure.step("Проверить подключение, запрос и результат"):
        assert rows == [(1,), (2,)]
        connect.assert_called_once_with(
            dbname="app",
            user="tester",
            password="secret",
            host="db.example",
            port=5432,
        )
        cursor.execute.assert_called_once_with(
            "SELECT id FROM orders WHERE status = %s",
            ["new"],
        )

    with allure.step("Проверить, что соединение закрыто"):
        connection.close.assert_called_once_with()

"""Проверки PostgreSQL-клиента без реальной базы данных."""

from unittest.mock import MagicMock

from qa_core.clients import postgres
from qa_core.clients.postgres import PostgresClient


def test_fetch_all_executes_parameterized_query(monkeypatch) -> None:
    connect_context = MagicMock()
    connection = connect_context.__enter__.return_value
    cursor_context = connection.cursor.return_value
    cursor = cursor_context.__enter__.return_value
    cursor.fetchall.return_value = [(1,), (2,)]
    connect = MagicMock(return_value=connect_context)
    monkeypatch.setattr(postgres.psycopg2, "connect", connect)

    client = PostgresClient(
        dbname="app",
        user="tester",
        password="secret",
        host="db.example",
        port=5432,
    )
    rows = client.fetch_all("SELECT id FROM orders WHERE status = %s", ["new"])

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


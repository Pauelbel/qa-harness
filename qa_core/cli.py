"""Команда ``qa-core init``: создаёт заготовку проекта автотестов.

Зачем нужен файл:
    Новичку не нужно знать, какие файлы и с каким содержимым нужны для старта.
    Команда создаёт ``conftest.py``, ``config.yaml``, ``pytest.ini``,
    ``requirements.txt`` и по одному рабочему тесту на каждый выбранный компонент.

Как использовать:

    qa-core init                                  # папка: текущая, компоненты: http, allure
    qa-core init мой-проект --components http,excel,allure
    python -m qa_core init                        # то же самое без установки команды

Существующие файлы не перезаписываются: команда пропускает их и сообщает об этом.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Адрес, откуда ставится qa-core в новом проекте. Замените на свой, если пакет
# лежит в другом репозитории или во внутреннем индексе пакетов.
PACKAGE_SOURCE = "git+https://github.com/Pauelbel/qa-harness.git"

COMPONENTS = {
    "http": "HTTP-клиент",
    "db": "PostgreSQL",
    "excel": "проверки Excel-отчётов",
    "odata": "проверки OData",
    "allure": "отчёты Allure",
    "ui": "браузер Playwright",
}
DEFAULT_COMPONENTS = ("http", "allure")

TEST_TEMPLATES = {
    "http": '''"""Первый тест: проверка HTTP-ответа. Замените адрес на адрес вашего сервиса."""

import allure

from qa_core.clients.http import BaseHttpClient


@allure.epic("Пример")
@allure.title("Сервис отвечает кодом 200")
def test_service_is_available():
    with BaseHttpClient() as http:
        response = http.get("https://example.com")

    assert response.status_code == 200
''',
    "excel": '''"""Пример проверки Excel-отчёта. Файл создаётся тут же, поэтому тест работает без сервера."""

import allure
import pandas as pd

from qa_core.checks.excel import ExcelDataQualityChecker


@allure.epic("Пример")
@allure.title("Excel-отчёт имеет нужные колонки и корректные значения")
def test_report_is_valid(tmp_path):
    report = tmp_path / "report.xlsx"
    pd.DataFrame({"ФИО": ["Иванов Иван"], "Дата": ["01.09.2026"]}).to_excel(report, index=False)

    checker = ExcelDataQualityChecker(report)
    checker.check_columns(["ФИО", "Дата"], strict_order=True)
    checker.check_required(["ФИО", "Дата"])
    checker.check_date("Дата")
    checker.assert_valid()  # вызывайте в конце: покажет все найденные ошибки сразу
''',
    "odata": '''"""Пример проверок OData. Данные заданы в тесте, поэтому он работает без сервера."""

import allure

from qa_core.checks.odata import OdataAssertions


@allure.epic("Пример")
@allure.title("Ответ OData не пуст и подходит под фильтр")
def test_odata_response():
    items = [{"Id": 1, "Status": "Draft"}, {"Id": 2, "Status": "Draft"}]

    OdataAssertions.response_not_empty(items)
    OdataAssertions.filter_eq(items, "Status", "Draft")
''',
    "db": '''"""Пример запроса к PostgreSQL. Пропускается, пока не заданы переменные окружения."""

import os

import allure
import pytest

from qa_core.clients.postgres import PostgresClient

pytestmark = pytest.mark.skipif(
    not os.getenv("DB_HOST"),
    reason="Задайте переменные окружения DB_HOST, DB_NAME, DB_USER, DB_PASSWORD",
)


@allure.epic("Пример")
@allure.title("База данных отвечает на запрос")
def test_database_answers():
    db = PostgresClient(
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
    )

    assert db.fetch_all("SELECT 1") == [(1,)]
''',
    "ui": '''"""Пример UI-теста. Перед запуском один раз выполните: python -m playwright install chromium"""

import allure
from playwright.sync_api import Page, expect


@allure.epic("Пример")
@allure.title("На странице есть заголовок")
def test_page_heading(browser_page: Page):
    browser_page.goto("https://example.com")

    expect(browser_page.get_by_role("heading")).to_have_text("Example Domain")
''',
}


def build_conftest(components: list[str]) -> str:
    lines = ['    "qa_core.pytest_plugins.logging",           # логи в консоль и в папку logs/']
    if "allure" in components or "ui" in components:
        lines.append('    "qa_core.pytest_plugins.allure_reporting",  # логи упавшего теста в Allure')
    if "ui" in components:
        lines.append('    "qa_core.pytest_plugins.playwright",        # фикстура browser_page')
    body = "\n".join(lines)
    return f'"""Подключение плагинов qa-core."""\n\npytest_plugins = [\n{body}\n]\n'


def build_config(components: list[str]) -> str:
    parts = ["# Настройки qa-core. Файл необязателен: без него действуют значения по умолчанию.\n"]
    if "http" in components:
        parts.append(
            "http:\n"
            "  # Секунды ожидания ответа, если в вызове не указан свой timeout.\n"
            "  timeout: 30\n"
            "  # Значения этих параметров адреса заменяются на *** в логах.\n"
            "  sensitive_query_parameters: [token, api_key, password]\n"
        )
    if "ui" in components:
        parts.append(
            "browser:\n"
            "  headless: true   # false — показывать окно браузера\n"
            "  width: 1920\n"
            "  height: 1080\n"
        )
    return "\n".join(parts)


def build_requirements(components: list[str]) -> str:
    extras = ",".join(sorted(components))
    return f"qa-core[{extras}] @ {PACKAGE_SOURCE}\n"


PYTEST_INI = """[pytest]
testpaths = tests
pythonpath = .
addopts = -ra
"""

GITIGNORE = """.venv/
__pycache__/
.pytest_cache/
logs/
allure-results/
allure-report/
.env
"""


def build_files(components: list[str]) -> dict[str, str]:
    """Возвращает путь файла и его содержимое для выбранных компонентов."""
    files = {
        "conftest.py": build_conftest(components),
        "pytest.ini": PYTEST_INI,
        "requirements.txt": build_requirements(components),
        ".gitignore": GITIGNORE,
    }
    if "http" in components or "ui" in components:
        files["config.yaml"] = build_config(components)
    for component in components:
        if component in TEST_TEMPLATES:
            files[f"tests/test_example_{component}.py"] = TEST_TEMPLATES[component]
    return files


def parse_components(value: str) -> list[str]:
    components = [item.strip().lower() for item in value.split(",") if item.strip()]
    unknown = [item for item in components if item not in COMPONENTS]
    if unknown:
        known = ", ".join(COMPONENTS)
        raise argparse.ArgumentTypeError(
            f"Неизвестные компоненты: {', '.join(unknown)}. Доступны: {known}"
        )
    if not components:
        raise argparse.ArgumentTypeError("Укажите хотя бы один компонент")
    return list(dict.fromkeys(components))


def init_project(target: Path, components: list[str]) -> tuple[list[str], list[str]]:
    """Создаёт файлы проекта и возвращает списки созданных и пропущенных путей."""
    created: list[str] = []
    skipped: list[str] = []
    for relative_path, content in build_files(components).items():
        path = target / relative_path
        if path.exists():
            skipped.append(relative_path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        created.append(relative_path)
    return created, skipped


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qa-core", description="Инструменты qa-core")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="создать заготовку проекта автотестов")
    init.add_argument("path", nargs="?", default=".", help="папка проекта (по умолчанию текущая)")
    init.add_argument(
        "--components",
        type=parse_components,
        default=list(DEFAULT_COMPONENTS),
        metavar="СПИСОК",
        help=(
            "компоненты через запятую: "
            + ", ".join(f"{name} ({title})" for name, title in COMPONENTS.items())
            + ". По умолчанию: " + ",".join(DEFAULT_COMPONENTS)
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = Path(args.path)

    created, skipped = init_project(target, args.components)

    for name in created:
        print(f"создан:   {name}")
    for name in skipped:
        print(f"пропущен: {name} (уже существует)")

    print("\nДальше:")
    print("  1. python -m venv .venv && .venv\\Scripts\\Activate.ps1   (Windows PowerShell)")
    print("  2. python -m pip install -r requirements.txt")
    if "ui" in args.components:
        print("  3. python -m playwright install chromium")
        print("  4. python -m pytest")
    else:
        print("  3. python -m pytest")
    return 0


if __name__ == "__main__":
    sys.exit(main())

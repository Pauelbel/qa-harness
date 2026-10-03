"""Проверки команды qa-core init."""

import subprocess
import sys
from pathlib import Path

import allure
import pytest

from qa_core.cli import COMPONENTS, init_project, main, parse_components


def run_pytest_in(project: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--color=no", "-q"],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


@allure.epic("Ядро")
@allure.title("init создаёт файлы проекта и по тесту на каждый компонент")
def test_init_creates_files(tmp_path: Path) -> None:
    created, skipped = init_project(tmp_path, ["http", "excel", "allure"])

    assert skipped == []
    for name in (
        "conftest.py",
        "pytest.ini",
        "config.yaml",
        "requirements.txt",
        "tests/test_example_http.py",
        "tests/test_example_excel.py",
    ):
        assert name in created
        assert (tmp_path / name).is_file()
    assert "qa-core[allure,excel,http]" in (tmp_path / "requirements.txt").read_text(encoding="utf-8")
    assert "allure_reporting" in (tmp_path / "conftest.py").read_text(encoding="utf-8")
    assert "playwright" not in (tmp_path / "conftest.py").read_text(encoding="utf-8")


@allure.epic("Ядро")
@allure.title("init не перезаписывает существующие файлы")
def test_init_does_not_overwrite(tmp_path: Path) -> None:
    (tmp_path / "conftest.py").write_text("# мой файл\n", encoding="utf-8")

    created, skipped = init_project(tmp_path, ["http"])

    assert "conftest.py" in skipped
    assert "conftest.py" not in created
    assert (tmp_path / "conftest.py").read_text(encoding="utf-8") == "# мой файл\n"


@allure.epic("Ядро")
@allure.title("Неизвестный компонент даёт понятную ошибку со списком доступных")
def test_unknown_component_is_reported() -> None:
    with pytest.raises(Exception, match="Неизвестные компоненты: kafka") as error:
        parse_components("http,kafka")

    for name in COMPONENTS:
        assert name in str(error.value)


@allure.epic("Ядро")
@allure.title("Сгенерированный проект сразу запускается и тесты проходят")
def test_generated_project_runs(tmp_path: Path) -> None:
    # Выбраны компоненты, чьи примеры работают без сети и внешних систем.
    exit_code = main(["init", str(tmp_path), "--components", "excel,odata,allure"])
    assert exit_code == 0

    result = run_pytest_in(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 passed" in result.stdout


@allure.epic("Ядро")
@allure.title("Команда запускается как python -m qa_core")
def test_module_entry_point(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "qa_core", "init", str(tmp_path), "--components", "odata"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "tests" / "test_example_odata.py").is_file()

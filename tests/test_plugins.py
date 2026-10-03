"""Проверки того, что плагины работают по отдельности и вместе."""

import allure
import pytest

pytest_plugins = ["pytester"]

LOGGING = "qa_core.pytest_plugins.logging"
ALLURE = "qa_core.pytest_plugins.allure_reporting"


def run(pytester: pytest.Pytester, *plugins: str, args: tuple[str, ...] = ()):
    pytester.makepyfile("def test_ok():\n    assert True\n")
    plugin_args = [item for plugin in plugins for item in ("-p", plugin)]
    return pytester.runpytest_subprocess(*plugin_args, *args)


@allure.epic("Ядро")
@allure.title("Плагин логирования работает без остальных плагинов")
def test_logging_plugin_alone(pytester: pytest.Pytester) -> None:
    result = run(pytester, LOGGING, args=("--qa-environment=dev",))

    result.assert_outcomes(passed=1)
    assert (pytester.path / "logs" / "pytest_dev.log").is_file()


@allure.epic("Ядро")
@allure.title("Плагин Allure работает без остальных плагинов")
def test_allure_plugin_alone(pytester: pytest.Pytester) -> None:
    result = run(
        pytester,
        ALLURE,
        args=("--qa-environment=dev", "--alluredir=allure-results"),
    )

    result.assert_outcomes(passed=1)
    assert (pytester.path / "allure-results" / "environment.xml").is_file()


@allure.epic("Ядро")
@allure.title("Плагины логирования и Allure подключаются вместе без конфликта опций")
def test_plugins_together(pytester: pytest.Pytester) -> None:
    result = run(pytester, LOGGING, ALLURE, args=("--qa-environment=stage",))

    result.assert_outcomes(passed=1)
    assert (pytester.path / "logs" / "pytest_stage.log").is_file()


@allure.epic("Ядро")
@allure.title("Плагин логирования не перебивает уровень, заданный в командной строке")
def test_logging_respects_cli_level(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        "import logging\n"
        "def test_ok():\n"
        "    logging.getLogger('demo').debug('debug-marker')\n"
    )

    default_run = pytester.runpytest_subprocess("-p", LOGGING)
    debug_run = pytester.runpytest_subprocess("-p", LOGGING, "--log-cli-level=DEBUG")

    assert "debug-marker" not in default_run.stdout.str()
    assert "debug-marker" in debug_run.stdout.str()


@allure.epic("Ядро")
@allure.title("Плагин логирования уважает настройки из pytest.ini")
def test_logging_respects_ini(pytester: pytest.Pytester) -> None:
    pytester.makeini("[pytest]\nlog_cli_level = DEBUG\n")
    pytester.makepyfile(
        "import logging\n"
        "def test_ok():\n"
        "    logging.getLogger('demo').debug('ini-marker')\n"
    )

    result = pytester.runpytest_subprocess("-p", LOGGING)

    assert "ini-marker" in result.stdout.str()


@allure.epic("Ядро")
@allure.title("Свой --log-file не заменяется файлом из logs/")
def test_logging_respects_log_file(pytester: pytest.Pytester) -> None:
    pytester.makepyfile("def test_ok():\n    assert True\n")

    pytester.runpytest_subprocess("-p", LOGGING, "--log-file=свой.log")

    assert (pytester.path / "свой.log").is_file()
    assert not (pytester.path / "logs").exists()


@allure.epic("Ядро")
@allure.title("Консольные логи отключаются параметром -o log_cli=false")
def test_logging_can_be_switched_off(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        "import logging\n"
        "def test_ok():\n"
        "    logging.getLogger('demo').info('info-marker')\n"
    )

    enabled = pytester.runpytest_subprocess("-p", LOGGING)
    disabled = pytester.runpytest_subprocess("-p", LOGGING, "-o", "log_cli=false")

    assert "info-marker" in enabled.stdout.str()
    assert "info-marker" not in disabled.stdout.str()

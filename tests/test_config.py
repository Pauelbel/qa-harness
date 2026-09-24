"""Проверки единого загрузчика YAML-конфигурации."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from qa_core.config import load_settings


@pytest.fixture
def http_config_path(tmp_path: Path) -> Path:
    """Создаёт минимальный корректный config.yaml."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """http:
  max_logged_response_body_length: 5
  sensitive_query_parameters:
    - token
    - api_key
browser:
  engine: firefox
  headless: false
  width: 1440
  height: 900
  ignore_https_errors: false
""",
        encoding="utf-8",
    )
    return config_path


def test_load_settings_reads_and_normalizes_http_section(
    http_config_path: Path,
) -> None:
    settings = load_settings(http_config_path)

    assert settings.http.max_logged_response_body_length == 5
    assert settings.http.sensitive_query_parameters == frozenset(
        {"token", "api_key"}
    )
    assert settings.browser.engine == "firefox"
    assert settings.browser.headless is False
    assert settings.browser.width == 1440
    assert settings.browser.height == 900
    assert settings.browser.ignore_https_errors is False


def test_load_settings_rejects_negative_log_limit(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text(
        """http:
  max_logged_response_body_length: -1
  sensitive_query_parameters: []
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_settings(config_path)

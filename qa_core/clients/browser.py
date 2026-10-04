"""Базовые классы для Page Object на Playwright: страница и элемент.

Элемент сам ждёт появления, пишет шаг в лог (и в Allure, если он есть) и сообщает
по-русски, какой именно элемент не найден. В Page Object остаются только локаторы
и сценарии страницы.

    class LoginPage(BasePage):
        def login(self, user: str, password: str) -> None:
            self.element("Поле логина", "#username").fill(user)
            self.element("Поле пароля", "#password").fill(password)
            self.element("Кнопка «Войти»", "button[type=submit]").click()

Нужен пакет playwright (pytest-playwright).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from playwright.sync_api import Locator, Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from qa_core.steps import step

logger = logging.getLogger(__name__)


class BaseElement:
    def __init__(self, locator: Locator, name: str, timeout: float = 20) -> None:
        self.locator = locator
        self.name = name
        self.timeout = timeout  # секунды

    def _ms(self, timeout: float | None) -> float:
        return (self.timeout if timeout is None else timeout) * 1000

    def _do(self, action: str, call: Callable[[float], Any], timeout: float | None) -> Any:
        """Ждёт элемент, выполняет действие и объясняет ошибку по-русски."""
        ms = self._ms(timeout)
        with step(f"{action} → {self.name}"):
            try:
                self.locator.wait_for(state="visible", timeout=ms)
                return call(ms)
            except (PlaywrightTimeoutError, AssertionError) as error:
                message = f"{action}: элемент '{self.name}' не готов за {ms / 1000:g} с. {error}"
                logger.error(message)
                raise AssertionError(message) from error

    def click(self, timeout: float | None = None) -> None:
        self._do("Клик", lambda ms: self.locator.click(timeout=ms), timeout)

    def fill(self, text: str, timeout: float | None = None) -> None:
        self._do("Ввод текста", lambda ms: self.locator.fill(text, timeout=ms), timeout)

    def press_key(self, key: str, timeout: float | None = None) -> None:
        """Нажимает клавишу: ``Enter``, ``Escape``, ``ArrowDown``."""
        self._do(f"Нажатие {key}", lambda ms: self.locator.press(key, timeout=ms), timeout)

    def get_text(self, timeout: float | None = None) -> str:
        return self._do("Чтение текста", lambda ms: self.locator.inner_text(timeout=ms), timeout)

    def get_attribute(self, name: str, timeout: float | None = None) -> str | None:
        return self._do(
            f"Чтение атрибута {name}",
            lambda ms: self.locator.get_attribute(name, timeout=ms),
            timeout,
        )

    def is_visible(self) -> bool:
        """Мгновенная проверка без ожидания: виден ли элемент сейчас."""
        return self.locator.is_visible()

    def expect_visible(self, timeout: float | None = None) -> None:
        """Ждёт, пока элемент станет видимым; иначе падает с понятным сообщением."""
        self._do("Проверка видимости", lambda ms: None, timeout)

    def check_have_text(self, text: str, timeout: float | None = None) -> None:
        self._do(
            f"Проверка текста «{text}»",
            lambda ms: expect(self.locator).to_have_text(text, timeout=ms),
            timeout,
        )


class BasePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def element(self, name: str, selector: str | Locator, timeout: float = 20) -> BaseElement:
        """Элемент страницы: CSS/XPath-строка или готовый локатор (``get_by_role(...)``)."""
        locator = self.page.locator(selector) if isinstance(selector, str) else selector
        return BaseElement(locator, name, timeout)

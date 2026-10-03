"""Page Object страницы «Заказы».

Всё, что связано с устройством страницы (адрес, локаторы), спрятано здесь. Если
вёрстка изменится, правится один файл, а тесты остаются прежними.

Правила:
- в классе только действия и проверки страницы, никаких данных конкретного теста;
- методы называются языком пользователя: ``open``, ``expect_order_visible``;
- ``assert`` в тестах не нужен: ``expect`` сам ждёт и показывает понятную ошибку.
"""

from playwright.sync_api import Page, expect


class OrdersPage:
    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.url = f"{base_url}/orders"
        self._heading = page.get_by_role("heading", name="Заказы")

    def open(self) -> "OrdersPage":
        """Открывает страницу и ждёт, пока она загрузится."""
        self.page.goto(self.url)
        expect(self._heading).to_be_visible()
        return self

    def expect_order_visible(self, title: str) -> None:
        expect(self.page.get_by_text(title)).to_be_visible()

    def expect_order_absent(self, title: str) -> None:
        expect(self.page.get_by_text(title)).to_have_count(0)

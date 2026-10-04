"""Page Object страницы «Заказы» поверх BasePage из ядра.

Всё, что связано с устройством страницы (адрес, локаторы), спрятано здесь. Если
вёрстка изменится, правится один файл, а тесты остаются прежними.

Правила:
- в классе только действия и проверки страницы, никаких данных конкретного теста;
- методы называются языком пользователя: ``open``, ``expect_order_visible``;
- элементы создаёт ``self.element(имя, локатор)``: он сам ждёт и пишет понятную ошибку.
"""

from qa_core.clients.browser import BasePage


class OrdersPage(BasePage):
    def __init__(self, page, base_url: str) -> None:
        super().__init__(page)
        self.url = f"{base_url}/orders"

    def open(self) -> "OrdersPage":
        """Открывает страницу и ждёт, пока она загрузится."""
        self.page.goto(self.url)
        self.element("Заголовок «Заказы»", self.page.get_by_role("heading", name="Заказы")).expect_visible()
        return self

    def expect_order_visible(self, title: str) -> None:
        self.element(f"Заказ {title}", self.page.get_by_text(title)).expect_visible()

    def expect_order_absent(self, title: str) -> None:
        assert self.page.get_by_text(title).count() == 0, f"Заказ {title} не должен быть виден"

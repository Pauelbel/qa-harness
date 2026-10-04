"""Визуальная проверка страницы: сравнение скриншота с эталоном.

    check = ScreenshotCheck("screenshots")
    check.assert_matches(page, "login_page.png")

Первый запуск создаёт эталон (``screenshots/base/``) и проходит. Дальше новый снимок
(``new/``) сравнивается с эталоном, картинка с выделенными отличиями кладётся в
``result/``. Если доля изменённых пикселей не меньше порога, проверка падает.
Чтобы обновить эталон, удалите его файл. Если установлен allure, три картинки
(expected, actual, diff) прикладываются к отчёту.

Нужны пакеты opencv-python-headless и numpy.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

HIGHLIGHT_COLOR = (204, 0, 204)  # BGR
HIGHLIGHT_ALPHA = 0.3
HIGHLIGHT_PADDING = 5


def compare_images(
    base_path: Path, new_path: Path, pixel_tolerance: int = 25
) -> tuple[float, np.ndarray]:
    """Возвращает долю изменённых пикселей и копию эталона с выделенными отличиями."""
    base = cv2.imread(str(base_path))
    new = cv2.imread(str(new_path))
    if base is None:
        raise FileNotFoundError(f"Эталон не найден: {base_path}")
    if new is None:
        raise FileNotFoundError(f"Снимок не найден: {new_path}")
    if base.shape != new.shape:
        raise AssertionError(
            f"Размеры снимков различаются: эталон {base.shape[1]}x{base.shape[0]}, "
            f"новый {new.shape[1]}x{new.shape[0]}"
        )

    gray = cv2.cvtColor(cv2.absdiff(base, new), cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, pixel_tolerance, 255, cv2.THRESH_BINARY)
    ratio = float(np.count_nonzero(mask)) / mask.size

    highlight = base.copy()
    overlay = base.copy()
    height, width = base.shape[:2]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        top_left = (max(x - HIGHLIGHT_PADDING, 0), max(y - HIGHLIGHT_PADDING, 0))
        bottom_right = (
            min(x + w + HIGHLIGHT_PADDING, width - 1),
            min(y + h + HIGHLIGHT_PADDING, height - 1),
        )
        cv2.rectangle(highlight, top_left, bottom_right, HIGHLIGHT_COLOR, 2)
        cv2.rectangle(overlay, top_left, bottom_right, HIGHLIGHT_COLOR, -1)
    cv2.addWeighted(overlay, HIGHLIGHT_ALPHA, highlight, 1 - HIGHLIGHT_ALPHA, 0, highlight)
    return ratio, highlight


class ScreenshotCheck:
    def __init__(
        self,
        directory: str | Path = "screenshots",
        threshold: float = 0.002,
        pixel_tolerance: int = 25,
    ) -> None:
        """``threshold``: допустимая доля изменённых пикселей (0.002 = 0,2 %)."""
        self.directory = Path(directory)
        self.threshold = threshold
        self.pixel_tolerance = pixel_tolerance

    def assert_matches(self, page, name: str, settle_ms: int = 0) -> float:
        """Снимает страницу и сравнивает с эталоном ``name``. Возвращает долю отличий.

        ``settle_ms``: пауза перед снимком для анимаций; лучше дождаться элемента через expect.
        """
        base_path = self.directory / "base" / name
        new_path = self.directory / "new" / name
        diff_path = self.directory / "result" / name
        for path in (base_path, new_path, diff_path):
            path.parent.mkdir(parents=True, exist_ok=True)

        if settle_ms:
            page.wait_for_timeout(settle_ms)
        page.screenshot(path=str(new_path))

        if not base_path.exists():
            shutil.copyfile(new_path, base_path)
            logger.warning("Эталон создан из первого снимка: %s", base_path)
            return 0.0

        ratio, highlight = compare_images(base_path, new_path, self.pixel_tolerance)
        cv2.imwrite(str(diff_path), highlight)
        logger.info("Визуальная разница %s: %.2f%%", name, ratio * 100)
        _attach(base_path, new_path, diff_path)

        assert ratio < self.threshold, (
            f"Слишком большая визуальная разница в {name}: {ratio:.4f}, порог {self.threshold:.4f}. "
            f"Отличия: {diff_path}"
        )
        return ratio


def _attach(base_path: Path, new_path: Path, diff_path: Path) -> None:
    try:
        import allure
    except ImportError:
        return
    for title, path in (("expected", base_path), ("actual", new_path), ("diff", diff_path)):
        allure.attach.file(str(path), name=title, attachment_type=allure.attachment_type.PNG)

from gi.repository import Nautilus, GObject, Gio
import gi
import os
from urllib.parse import unquote, urlparse

# Требуем нужные версии библиотек
# gi.require_version('Nautilus', '4.0')
# gi.require_version('Gio', '2.0')


class PompiliusIconOverlay(GObject.GObject, Nautilus.InfoProvider):
    def __init__(self):
        super().__init__()

    def is_cached(self, file_path):
        """
        Твоя логика проверки: закеширован файл или нет.
        Пока всегда возвращаем True для примера.
        """
        # Здесь в будущем будет проверка через конфиг или D-Bus
        return True

    def update_file_info(self, file_info):
        """
        Метод вызывается Nautilus для каждого отображаемого файла.
        """
        # Получаем URI и проверяем, что это локальный файл
        uri = file_info.get_uri()
        # if not uri.startswith("file://"):
        #     return

        # Декодируем путь
        file_path = unquote(urlparse(uri).path)

        # Игнорируем директории (по желанию)
        if file_info.is_directory():
            return

        # Проверяем наш статус
        cached = self.is_cached(file_path)

        # Выбираем иконку-оверлей из системной темы
        # emblem-ok-symbolic — зеленая галочка
        # emblem-important-symbolic — восклицательный знак (обычно красный/желтый)
        # emblem-synchronizing-symbolic — стрелочки (синхронизация)
        icon_name = "emblem-ok-symbolic" if cached else "emblem-important-symbolic"

        # Устанавливаем оверлей
        # В Nautilus 4 это делается через атрибут 'overlay_icons'
        file_info.add_string_attribute('overlay_icons', icon_name)

        # Сообщаем Nautilus, что информация о файле обновилась
        file_info.invalidate_extension_info()

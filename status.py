from gi.repository import Nautilus, GObject, Gio, GLib
import random
import os
from pompilius import get_existing_profiles
from urllib.parse import unquote, urlparse
import json


bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


class PompiliusIconOverlay(GObject.GObject, Nautilus.InfoProvider):
    def __init__(self):
        super().__init__()
        self.active_files = {}

        GLib.timeout_add(1000, self.refresh_all)

    def is_cached(self, profile, file_path):
        # file_path должен быть только именем файла, как в твоем примере "129155.jpg"
        # или полным путем, если так ожидает бэкенд.
        file_name = os.path.basename(file_path)

        try:
            raw_response = bus.call_sync(
                'org.zbus.pompiliusd',
                '/org/zbus/pompiliusd',
                'org.zbus.pompiliusd',
                'GetFilesStatus',
                # Сигнатура 'sas': строка (профиль) и массив строк (список файлов)
                GLib.Variant('(sas)', (profile, [file_name])),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None)

            # 1. Извлекаем строку JSON из Variant
            outer_json_str = raw_response.unpack()[0]
            outer_data = json.loads(outer_json_str)

            inner_data_str = outer_data.get('data', '{}')
            status_map = json.loads(inner_data_str)

            status = status_map.get(file_name, "NOT_CACHED")

            # 4. Мапим строковый статус в числа
            mapping = {
                "NOT_CACHED": 0,
                "CACHED": 1,
                "SYNCING": 2
            }

            return mapping.get(status, 0)

        except Exception as e:
            print(f"Ошибка при получении статуса файла: {e}")
            return 0  # По умолчанию считаем, что не закеширован

    def refresh_all(self):
        """Принудительно заставляет Nautilus переспросить статус для всех видимых файлов"""
        for uri, file_info in list(self.active_files.items()):
            try:
                file_info.invalidate_extension_info()
            except:
                self.active_files.pop(uri, None)
        return True

    def update_file_info(self, file_info):
        uri = file_info.get_uri()
        # Игнорируем виртуальные папки (Recent, Trash и т.д.)
        if not uri.startswith("file://"):
            return

        file_path = unquote(urlparse(uri).path)

        # Сохраняем ссылку на объект для refresh_all
        self.active_files[uri] = file_info

        # Если это директория, иконки статуса обычно не ставятся,
        # но мы запоминаем её как текущую
        if file_info.is_directory():
            self.current_dir = file_path
            return

        # Определяем родительскую директорию для текущего файла
        current_dir = os.path.dirname(file_path)

        # 1. Проверяем, входит ли эта директория в какой-либо профиль rclone
        profiles = get_existing_profiles()
        active_profile_title = None

        for title, mount_root in profiles.items():
            if current_dir.startswith(mount_root):
                active_profile_title = title
                break

        # Если файл не в облачной папке — ничего не делаем
        if not active_profile_title:
            return

        try:
            # 2. Получаем список ВСЕХ файлов в этой директории (абсолютные пути)
            # Это именно то, что ты просил: список абсолютных путей
            all_files_in_dir = [
                os.path.join(current_dir, f)
                for f in os.listdir(current_dir)
                if os.path.isfile(os.path.join(current_dir, f))
            ]

            # 3. Для запроса в D-Bus нам нужны только базовые имена (как в твоем примере busctl)
            file_names = [os.path.basename(f) for f in all_files_in_dir]

            # Делаем пакетный запрос к D-Bus
            raw_response = bus.call_sync(
                'org.zbus.pompiliusd',
                '/org/zbus/pompiliusd',
                'org.zbus.pompiliusd',
                'GetFilesStatus',
                GLib.Variant('(sas)', (active_profile_title, file_names)),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )

            # 4. Парсим ответ
            outer_data = json.loads(raw_response.unpack()[0])
            status_map = json.loads(outer_data.get('data', '{}'))

            # Получаем статус именно для текущего файла, который обрабатывает Nautilus
            current_file_name = os.path.basename(file_path)
            status_str = status_map.get(current_file_name, "NOT_CACHED")

            # 5. Устанавливаем эмблему
            if status_str == "CACHED":
                icon = "document-save"
            elif status_str == "SYNCING":
                icon = "network-receive"
            else:
                icon = "network-wireless"

            file_info.add_string_attribute('overlay_icons', icon)
            file_info.add_emblem(icon)

        except Exception as e:
            print(f"Ошибка InfoProvider: {e}")

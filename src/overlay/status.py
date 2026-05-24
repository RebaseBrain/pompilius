import gi
from gi.repository import Nautilus, GObject, Gio, GLib
import os
from pompilius import get_existing_profiles
from constants import DBUS_NAME, DBUS_PATH, DBUS_IFACE
from urllib.parse import unquote, urlparse
import json

gi.require_version("Gtk", "4.0")

# Кеш статусов: (profile, file_name) -> status_string
STATUS_CACHE = {}
# Множество (profile, directory_path), для которых сейчас выполняется запрос
PENDING_DIRS = set()

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


class PompiliusIconOverlay(GObject.GObject, Nautilus.InfoProvider):
    def __init__(self):
        super().__init__()
        self.active_files = {}
        # Периодически обновляем информацию, чтобы подхватывать изменения от бекенда
        GLib.timeout_add(5000, self.refresh_all)

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
            if current_dir.startswith(f"{mount_root}/{title}"):
                active_profile_title = title
                break

        # Если файл не в облачной папке — ничего не делаем
        if not active_profile_title:
            return

        file_name = os.path.basename(file_path)
        cache_key = (active_profile_title, file_name)

        # 2. Если статус есть в кэше — накладываем эмблему сразу
        if cache_key in STATUS_CACHE:
            self.apply_status_emblem(file_info, STATUS_CACHE[cache_key])

        # 3. Если для этой папки еще нет активного запроса — запускаем обновление
        if (active_profile_title, current_dir) not in PENDING_DIRS:
            self.request_status_update(active_profile_title, current_dir)

    def apply_status_emblem(self, file_info, status_str):
        mapping = {
            "CACHED": "document-save",
            "SYNCING": "network-receive",
            "NOT_CACHED": "network-wireless",
        }
        icon = mapping.get(status_str)
        if icon:
            file_info.add_string_attribute("overlay_icons", icon)
            file_info.add_emblem(icon)

    def request_status_update(self, profile, directory):
        PENDING_DIRS.add((profile, directory))

        try:
            # Получаем список файлов для запроса
            all_files_in_dir = [
                f
                for f in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, f))
            ]

            if not all_files_in_dir:
                PENDING_DIRS.discard((profile, directory))
                return

            bus.call(
                DBUS_NAME,
                DBUS_PATH,
                DBUS_IFACE,
                "GetFilesStatus",
                GLib.Variant("(sas)", (profile, all_files_in_dir)),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                self.on_status_received,
                (profile, directory),
            )
        except Exception as e:
            print(f"Ошибка при запросе статусов: {e}")
            PENDING_DIRS.discard((profile, directory))

    def on_status_received(self, connection, res, user_data):
        profile, directory = user_data
        try:
            raw_response = connection.call_finish(res)
            outer_data = json.loads(raw_response.unpack()[0])
            status_map = json.loads(outer_data.get("data", "{}"))

            for f_name, status in status_map.items():
                STATUS_CACHE[(profile, f_name)] = status

            # Инвалидируем информацию для всех файлов в этой директории, чтобы Nautilus их перерисовал
            for uri, file_info in list(self.active_files.items()):
                file_path = unquote(urlparse(uri).path)
                if os.path.dirname(file_path) == directory:
                    try:
                        file_info.invalidate_extension_info()
                    except:
                        self.active_files.pop(uri, None)

        except Exception as e:
            print(f"Ошибка в on_status_received: {e}")
        finally:
            PENDING_DIRS.discard((profile, directory))

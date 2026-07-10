from gi.repository import Nautilus, GObject, Gio, GLib
import os
import time
from urllib.parse import unquote, urlparse

from pompilius import get_existing_profiles
from constants import DBUS_NAME, DBUS_PATH, DBUS_IFACE
from errors import CloudError

REFRESH_INTERVAL_SEC = 120

# Кэш: { profile_name: timestamp последнего обновления }
LAST_REFRESH_TIME = {}
# Множество профилей, для которых сейчас летит запрос
PENDING_REFRESHES = set()

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


def get_mount_profiles():
    """
    Парсит конфиг и возвращает словарь {имя_профиля: полный_путь}.
    Полный путь формируется как base_path + profile_name.
    """

    profiles_raw = get_existing_profiles()
    profiles = {}
    for name, base_path in profiles_raw.items():
        profiles[name] = os.path.join(base_path, name)
    return profiles


class PompiliusRefreshOverlay(GObject.GObject, Nautilus.InfoProvider):
    def __init__(self):
        super().__init__()
        self.profiles = get_mount_profiles()
        # Обновляем список профилей раз в 10 секунд на случай изменения конфига
        GLib.timeout_add(10000, self.reload_config)

    def reload_config(self):
        self.profiles = get_mount_profiles()
        return True

    def update_file_info(self, file_info):
        uri = file_info.get_uri()
        if not uri.startswith("file://"):
            return

        file_path = unquote(urlparse(uri).path)

        # Определяем директорию (для папки берем ее саму, для файла - родителя)
        current_dir = (
            file_path if file_info.is_directory() else os.path.dirname(file_path)
        )

        # Проверяем, находимся ли мы внутри примонтированного хранилища
        active_profile = None
        for title, mount_full_path in self.profiles.items():
            # Если текущий путь начинается с пути маунта хранилища
            if current_dir.startswith(mount_full_path):
                active_profile = title
                break

        # Если файл/папка не в хранилище - ничего не делаем
        if not active_profile:
            return

        # Проверяем, не слишком ли часто мы дергаем рефреш
        current_time = time.time()
        last_time = LAST_REFRESH_TIME.get(active_profile, 0)
        # С прошлого рефреша еще не прошло нужное кол-во времени
        if current_time - last_time < REFRESH_INTERVAL_SEC:
            return

        # Проверяем, не запущен ли уже запрос
        if active_profile in PENDING_REFRESHES:
            return

        self.refresh(active_profile)

    def refresh(self, profile):
        PENDING_REFRESHES.add(profile)
        # Ставим timestamp сразу, чтобы другие файлы в этой же директории
        # не создавали спам вызовов
        LAST_REFRESH_TIME[profile] = time.time()

        try:
            bus.call(
                DBUS_NAME,
                DBUS_PATH,
                DBUS_IFACE,
                "IsBusy",
                None,
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                self.on_is_busy_done,
                profile,
            )
        except Exception as e:
            print(f"[Auto-Refresh] ERROR: Ошибка при запуске IsBusy для {profile}: {e}")
            PENDING_REFRESHES.discard(profile)

    def on_is_busy_done(self, connection, res, profile):
        try:
            result = connection.call_finish(res)
            is_busy = result.unpack()[0]
            if is_busy:
                print(f"[Auto-Refresh] INFO: rclone занят, пропускаем Refresh для {profile}")
                PENDING_REFRESHES.discard(profile)
                return

            # Вызываем Refresh от корня хранилища, чтобы добавить все новые
            # файлы из всех дочерних директорий
            bus.call(
                DBUS_NAME,
                DBUS_PATH,
                DBUS_IFACE,
                "Refresh",
                GLib.Variant("(ss)", (profile, ".")),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                self.on_refresh_done,
                profile,
            )
        except GLib.Error as e:
            print(f"[Auto-Refresh] ERROR: D-Bus ошибка IsBusy ({profile}): {e.message}")
            PENDING_REFRESHES.discard(profile)
        except Exception as e:
            print(f"[Auto-Refresh] ERROR: Непредвиденная ошибка IsBusy ({profile}): {e}")
            PENDING_REFRESHES.discard(profile)

    def on_refresh_done(self, connection, res, profile):
        try:
            # Не нужно парсить ответ демона, достаточно того, что ошибок нет.
            _ = connection.call_finish(res)
            print(f"[Auto-Refresh] INFO: Обновил хранилище: {profile}")
        except GLib.Error as e:
            dbus_err = Gio.dbus_error_get_remote_error(e)

            if dbus_err == CloudError.REQWEST:
                print(f"[Auto-Refresh] WARINNING: Нет связи с API rclone при обновлении {profile}.")
            elif dbus_err == CloudError.RCLONE:
                print(f"[Auto-Refresh] ERROR: Ошибка облака ({profile}): {e.message}")
            else:
                print(f"[Auto-Refresh] ERROR: D-Bus ошибка ({profile}): {e.message}")
        except Exception as e:
            print(f"[Auto-Refresh] ERROR: Непредвиденная ошибка ({profile}): {e}")
        finally:
            # Снимаем блокировку запроса
            PENDING_REFRESHES.discard(profile)

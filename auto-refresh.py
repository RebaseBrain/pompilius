from gi.repository import Nautilus, GObject, Gio, GLib
import os
import time
from urllib.parse import unquote, urlparse

from pompilius import get_existing_profiles, DBUS_NAME, DBUS_PATH, DBUS_IFACE

REFRESH_INTERVAL_SEC = 20

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

    def refresh(self, profile):
        PENDING_REFRESHES.add(profile)
        # Ставим timestamp сразу, чтобы другие файлы в этой же директории
        # не создавали спам вызовов
        LAST_REFRESH_TIME[profile] = time.time()

        try:
            # Вызываем Refresh от корня хранилища, чтобы добавить все новые
            # файлы из всех дочерних директорий
            bus.call(
                DBUS_NAME,
                DBUS_PATH,
                DBUS_IFACE,
                'Refresh',
                GLib.Variant('(ss)', (profile, ".")),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                self.on_refresh_done,
                profile
            )
        except Exception as e:
            print(f"Ошибка при вызове Refresh для {profile}: {e}")
            PENDING_REFRESHES.discard(profile)

    def on_refresh_done(self, connection, res, profile):
        try:
            # Не нужно парсить ответ демона, достаточно того, что ошибок нет.
            _ = connection.call_finish(res)
        except Exception as e:
            print(f"D-Bus Refresh вернул ошибку для {profile}: {e}")
        finally:
            # Снимаем блокировку запроса
            PENDING_REFRESHES.discard(profile)

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

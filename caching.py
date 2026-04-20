from pompilius import get_existing_profiles
import os
from gi.repository import Nautilus, GObject, Gio, GLib

from urllib.parse import unquote, urlparse


bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


class PompiliusCaching(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        GObject.Object.__init__(self)

    def get_file_items(self, files):
        profiles = get_existing_profiles()

        show_menu = False
        all_are_directories = True

        current_profile = {
            "title": "",
            "mount_root": ""
        }

        for file in files:
            if not file.is_directory():
                all_are_directories = False

            uri = file.get_uri()
            file_path = unquote(urlparse(uri).path)

            for title, p in profiles.items():
                if file_path.startswith(p):
                    current_profile["title"] = title
                    current_profile["mount_root"] = p
                    show_menu = True
                    break

            if show_menu:
                break

        if not show_menu:
            return []

        menu_items = []

        if all_are_directories:
            item_cache = Nautilus.MenuItem(
                name="Pompilius::Cache",
                label="Закешировать директорию",
                tip="Директория будет доступна офлайн"
            )
            item_cache.connect(
                "activate", self.cache_choosed_directory, files)
            menu_items.append(item_cache)

        item_remove = Nautilus.MenuItem(
            name="Pompilius::Remove",
            label="Удалить из кеша",
            tip="Удалить локальную копию, оставив файл в облаке"
        )
        item_remove.connect(
            "activate", self.delete_from_cache, files, current_profile)
        menu_items.append(item_remove)

        return menu_items

    def delete_from_cache(self, item, files, profile):
        mock_profile = profile["title"]

        for file in files:
            uri = file.get_uri()
            absolute_path = unquote(urlparse(uri).path)
            try:
                relative_path = os.path.relpath(
                    absolute_path, profile["mount_root"]).replace(mock_profile, "").lstrip(os.sep)
                
                bus.call(
                    'org.zbus.pompiliusd',
                    '/org/zbus/pompiliusd',
                    'org.zbus.pompiliusd',
                    'DeleteCachePath',
                    GLib.Variant('(ss)', (mock_profile, relative_path)),
                    None,
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None,
                    self.on_operation_finished,
                    f"Удаление из кеша: {relative_path}"
                )

            except Exception as e:
                print(f"Ошибка D-Bus: {e}")

    def cache_choosed_directory(self, item, directories):
        for file_info in directories:
            location = file_info.get_location()
            if not location:
                continue

            abs_path = location.get_path()
            if not abs_path:
                continue

            try:
                bus.call(
                    'org.zbus.pompiliusd',
                    '/org/zbus/pompiliusd',
                    'org.zbus.pompiliusd',
                    'CacheDirectory',
                    GLib.Variant('(s)', (abs_path,)),
                    None,
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None,
                    self.on_operation_finished,
                    f"Кеширование директории: {abs_path}"
                )
            except Exception as e:
                print(f"Ошибка D-Bus при кешировании {abs_path}: {e}")

    def on_operation_finished(self, connection, res, user_data):
        try:
            connection.call_finish(res)
            print(f"Операция завершена успешно: {user_data}")
        except Exception as e:
            print(f"Ошибка при выполнении операции ({user_data}): {e}")

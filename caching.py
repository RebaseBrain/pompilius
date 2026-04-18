from gi.repository import Nautilus, GObject, Gio, GLib

from urllib.parse import unquote, urlparse


bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


class PompiliusCaching(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        GObject.Object.__init__(self)

    def get_file_items(self, files):
        if not files:
            return []

        # Первая опция: Закешировать
        item_cache = Nautilus.MenuItem(
            name="Pompilius::Cache",
            label="Закешировать",
            tip="Файл будет доступен офлайн"
        )
        item_cache.connect("activate", self.cache_choosed_files, files)

        # Вторая опция: Удалить из кеша
        item_remove = Nautilus.MenuItem(
            name="Pompilius::Remove",
            label="Удалить из кеша",
            tip="Удалить локальную копию, оставив файл в облаке"
        )
        item_remove.connect("activate", self.delete_from_cache, files)

        # Просто возвращаем список — Nautilus сам добавит их в меню по порядку
        return [item_cache, item_remove]

    def delete_from_cache(self, item, files):
        mock_profile = "gohy"
        for file in files:
            mock_path = "./Мишки.jpg"

            try:
                bus.call_sync(
                    'org.zbus.pompiliusd',
                    '/org/zbus/pompiliusd',
                    'org.zbus.pompiliusd',
                    'RemoveFromCache',
                    GLib.Variant('(ss)', (mock_profile, mock_path)),
                    None,
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None)

            except Exception as e:
                print(f"Ошибка D-Bus: {e}")

    def cache_choosed_files(self, item, files):
        mock_profile = "gohy"
        for file in files:
            uri = file.get_uri()

            parsed_uri = urlparse(uri)
            absolute_path = unquote(parsed_uri.path)
            try:
                bus.call_sync(
                    'org.zbus.pompiliusd',
                    '/org/zbus/pompiliusd',
                    'org.zbus.pompiliusd',
                    'CacheDirectory',
                    GLib.Variant('(ss)', (mock_profile, absolute_path)),
                    None,
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None)
            except Exception as e:
                print(f"Ошибка D-Bus: {e}")

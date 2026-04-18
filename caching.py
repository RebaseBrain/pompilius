from gi.repository import Nautilus, GObject, Gio, GLib

from urllib.parse import unquote, urlparse


bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


class PompiliusCaching(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        GObject.Object.__init__(self)

    def get_file_items(self, files):
        """
        Этот метод срабатывает ТОЛЬКО при клике на файлы/папки.
        'files' — это список объектов Nautilus.FileInfo.
        """

        if not files:
            return []

        # Создаем пункт меню
        item = Nautilus.MenuItem(
            name="Pompilius::CacheFiles",
            label="Закешировать файл",
            tip="Файл будет доступен и в оффлайн"
        )

        # Привязываем действие к нажатию
        # Передаем список файлов в callback через аргумент
        # item.connect("activate", lambda menu, target_files: self.cache_choosed_files(
        #     menu, target_files), files)
        item.connect("activate", self.cache_choosed_files, files)

        return [item]

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

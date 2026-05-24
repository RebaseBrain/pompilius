import gi
import webbrowser
import os
import json
from gi.repository import Nautilus, GObject, Gio, GLib, Notify
from urllib.parse import unquote, urlparse
from pompilius import DBUS_IFACE, DBUS_NAME, DBUS_PATH, get_existing_profiles

gi.require_version('Gtk', '4.0')
gi.require_version('Notify', '0.7')

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


def open_link(url):
    webbrowser.open(url, new=2)


class PompiliusOpenInBrowser(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()
        # Нативная инициализация Libnotify для GNOME
        try:
            Notify.init("Pompilius")
        except Exception as e:
            print(f"Не удалось инициализировать Notify: {e}")

    def show_notification(self, title, message):
        """Функция для показа нативного уведомления GNOME"""
        try:
            # Создаем уведомление: Заголовок, Текст, Иконка
            n = Notify.Notification.new(title, message, "edit-copy-symbolic")
            # transient=True значит, что уведомление не будет висеть в истории (центре уведомлений)
            n.set_hint("transient", GLib.Variant("b", True))
            n.show()
        except Exception as e:
            print(f"Ошибка вывода уведомления GNOME: {e}")

    def get_file_items(self, files):
        """
        Этот метод срабатывает ТОЛЬКО при клике на файлы/папки.
        'files' — это список объектов Nautilus.FileInfo.
        """

        profiles = get_existing_profiles()

        show_menu = False
        profile = {
            "title": "",
            "mount_root": ""
        }
        for file in files:
            uri = file.get_uri()
            file_path = unquote(urlparse(uri).path)
            for title, p in profiles.items():
                if file_path.startswith(p):
                    profile["title"] = title
                    profile["mount_root"] = p
                    show_menu = True
                    break
                if show_menu:
                    break

        if not show_menu:
            return []

        # Создаем пункт меню
        item = Nautilus.MenuItem(
            name="Pompilius::OpenInBrowser",
            label="Открыть файл в браузере",
            tip="Можете потом его куда-то скинуть"
        )

        item.connect("activate", self.get_link, files, profile)

        return [item]

    def get_link(self, item, files, profile):
        mock_profile = profile["title"]
        for file in files:
            uri = file.get_uri()
            absolute_path = unquote(urlparse(uri).path)
            try:
                relative_path = os.path.relpath(
                    absolute_path, profile["mount_root"]).replace(mock_profile, "")
                bus.call(
                    DBUS_NAME,
                    DBUS_PATH,
                    DBUS_IFACE,
                    'Link',
                    GLib.Variant('(ss)', (mock_profile, relative_path)),
                    None,
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None,
                    self.on_link_received,
                    None
                )
            except Exception as e:
                print(f"Ошибка D-Bus: {e}")

    def on_link_received(self, connection, res, user_data):
        try:
            result = connection.call_finish(res)
            raw_data = result.unpack()[0]
            parsed_json = json.loads(raw_data)
            link = json.loads(parsed_json['data'])
            open_link(link)
        except Exception as e:
            print(f"Ошибка при открытии ссылки: {e}")

from gi.repository import Nautilus, GObject, Gio, GLib
import json
from gi.repository import Nautilus, GObject, Gio, GLib, Gdk, Notify
from urllib.parse import unquote, urlparse
import os
from pompilius import DBUS_IFACE, DBUS_NAME, DBUS_PATH, get_existing_profiles


bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


class PompiliusLinks(GObject.GObject, Nautilus.MenuProvider):
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
            # print(profiles)
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
            name="Pompilius::GetLink",
            label="Получить ссылку на файл",
            tip="Можете потом его куда-то скинуть"
        )

        item.connect("activate", self.get_link, files, profile)

        return [item]

    def get_link(self, item, files, profile):

        mock_profile = profile["title"]
        links = []
        for file in files:
            uri = file.get_uri()

            absolute_path = unquote(urlparse(uri).path)
            try:
                relative_path = os.path.relpath(
                    absolute_path, profile["mount_root"]).replace(mock_profile, "")
                result = bus.call_sync(
                    DBUS_NAME,
                    DBUS_PATH,
                    DBUS_IFACE,
                    'Link',
                    GLib.Variant('(ss)', (mock_profile, relative_path)),
                    None,
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None)
                # print(result)

                raw_data = result.unpack()[0]

                parsed_json = json.loads(raw_data)
                link = json.loads(parsed_json['data'])
                display = Gdk.Display.get_default()
                clipboard = display.get_clipboard()

                clipboard.set_content(Gdk.ContentProvider.new_for_value(link))
                GLib.idle_add(self.show_notification,
                              "Pompilius", "Ссылка скопирована!")
                # GLib.idle_add(self.show_notification,
                #               "Pompilius", "Ссылка скопирована!")
                # self.show_notification(
                #     "Pompilius", "Ссылка скопирована в буфер обмена!")
                print(link)

                links.append(link)
            except Exception as e:
                print(f"Ошибка D-Bus: {e}")

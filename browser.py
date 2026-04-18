import webbrowser
from gi.repository import Nautilus, GObject, Gio, GLib
import json
from gi.repository import Nautilus, GObject, Gio, GLib, Gdk, Notify
from urllib.parse import unquote, urlparse


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

        if not files:
            return []

        # Создаем пункт меню
        item = Nautilus.MenuItem(
            name="Pompilius::GetLink",
            label="Открыть файл в браузере",
            tip="Можете потом его куда-то скинуть"
        )

        item.connect("activate", self.get_link, files)

        return [item]

    def get_link(self, item, files):
        mock_profile = "gohy"
        mock_path = "./Мишки.jpg"
        links = []
        for file in files:
            uri = file.get_uri()

            parsed_uri = urlparse(uri)
            absolute_path = parsed_uri.path
            try:
                print(f"{mock_profile} {absolute_path}")
                result = bus.call_sync(
                    'org.zbus.pompiliusd',
                    '/org/zbus/pompiliusd',
                    'org.zbus.pompiliusd',
                    'Link',
                    GLib.Variant('(ss)', (mock_profile, mock_path)),
                    None,
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None)

                raw_data = result.unpack()[0]

                parsed_json = json.loads(raw_data)
                link = json.loads(parsed_json['data'])
                display = Gdk.Display.get_default()
                # clipboard = display.get_clipboard()
                #
                # # # В GTK4/Gdk мы просто передаем строку в метод set_content
                # clipboard.set_content(Gdk.ContentProvider.new_for_value(link))
                # GLib.idle_add(self.show_notification,
                #               "Pompilius", "Ссылка скопирована!")
                # GLib.idle_add(self.show_notification,
                #               "Pompilius", "Ссылка скопирована!")
                # self.show_notification(
                #     "Pompilius", "Ссылка скопирована в буфер обмена!")
                open_link(link)
                print(link)

                links.append(link)
            except Exception as e:
                print(f"Ошибка D-Bus: {e}")

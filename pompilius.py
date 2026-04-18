from gi.repository import Nautilus, GObject, Gtk, Pango, Gio, GLib
import os
import json
from urllib.parse import unquote, urlparse

EXTENSION_DIR = os.path.dirname(os.path.abspath(__file__))


class ProfileResponse:
    title: str
    provider: str


def get_rclone_title(title: str) -> str:
    match title:
        case "Yandex":
            return "yandex"
    return "unknown"


def get_title_from_rclone(rclone_title: str) -> str:
    match rclone_title:
        case "yandex":
            return "Yandex"
    return "unknown"


def get_logo_path_from_rclone(rclone_title: str) -> str:
    match rclone_title:
        case "yandex":
            print("adsdqdsadakjsdbkajd")
            return "./static/yandex-disk-logo.png"
    return "unknown"


class Provider:
    title: str
    logo_path: str
    rclone_title: str

    def __init__(self, rclone_title):
        self.title = get_title_from_rclone(rclone_title)
        self.logo_path = get_logo_path_from_rclone(rclone_title)

    def get_image(self) -> Gtk.Image:
        full_path = os.path.join(EXTENSION_DIR, self.logo_path)
        print(full_path)

        if os.path.exists(full_path):
            return Gtk.Image.new_from_file(full_path)

        return Gtk.Image.new_from_icon_name(self.logo_path)


def call_dbus_method(self):
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

    try:
        bus.call_sync(
            'org.zbus.cloud_api',           # Bus name
            '/org/zbus/cloud_api',          # Object path
            'org.zbus.cloud_api',           # Interface name
            'SayHello',                     # Method
            GLib.Variant('(s)', ("Egor",)),  # Аргументы (сигнатура s)
            # Ожидаемый тип ответа (None для любого)
            None,
            Gio.DBusCallFlags.NONE,
            -1,                             # Таймаут по умолчанию
            None
        )
        print("D-Bus метод вызван напрямую")
    except Exception as e:
        print(f"Ошибка D-Bus: {e}")


class Profile:
    title: str
    provider: Provider

    def __init__(self, title, provider: Provider):
        self.title = title
        self.provider = provider


class ColumnExtension(GObject.GObject, Nautilus.MenuProvider):
    current_dir: str

    def __init__(self):
        print("askdjaslkjkladjklasjdlksajdlkasjdlkasjlkdj")
        pass

    class ProfileResponse:
        title: str
        provider: str

    def get_background_items(self, folder):
        self.current_dir = absolute_path = unquote(
            urlparse(folder.get_uri()).path)
        item = Nautilus.MenuItem(
            name='ExampleMenuProvider::CreateFusionBackground',
            label='Добавить удалённое хранилище',
            tip='Добавить хранилище в текущую папку'
        )
        item.connect('activate', self.menu_activate)
        return [item]

    def menu_activate(self, menu):
        dialog = Gtk.MessageDialog(
            transient_for=None,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            text="Настройка удалённого хранилища",
            secondary_text="Укажите профиль для загрузки"
        )
        dialog.add_button("Создать профиль", 1)
        dialog.add_button("Использовать существующий профиль", 2)
        dialog.add_button("Отмена", Gtk.ResponseType.CANCEL)

        def on_response(d, response_id):
            if response_id == 1:
                self.create_new_profile()
            elif response_id == 2:
                self.show_profiles()

            d.destroy()

        # Подключаем обработчик к сигналу 'response'
        dialog.connect("response", on_response)
        dialog.show()
        print("Пункт меню нажат!")

    def on_company_clicked(self, flowbox, child):
        provider_title = child.company_id

        input_dialog = Gtk.Window(
            title=f"Настройка {provider_title}", modal=True)
        input_dialog.set_default_size(300, 100)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(15)
        vbox.set_margin_end(15)
        vbox.set_margin_top(15)
        vbox.set_margin_bottom(15)

        label = Gtk.Label(label="Назовите профиль")
        label.set_xalign(0)

        entry = Gtk.Entry()
        entry.set_placeholder_text("Введите название профиля...")
        entry.connect("activate",
                      self.create_profile, input_dialog, provider_title)
        provider_title = child.company_id

        vbox.append(label)
        vbox.append(entry)

        input_dialog.set_child(vbox)
        input_dialog.present()

    def create_profile(self, entry, input_dialog, provider_title):
        text = entry.get_text()

        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        try:
            response_raw = bus.call_sync(
                'org.zbus.pompiliusd',
                '/org/zbus/pompiliusd',
                'org.zbus.pompiliusd',
                'CreateProfile',
                GLib.Variant(
                    '(ss)', (text, provider_title)),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
        except Exception as e:
            print(f"Ошибка D-Bus: {e}")

        # print(f"Сижу жду ручку с бека: {text} {provider_title}")
        input_dialog.destroy()

    def create_company_widget(self, name, logo):
        """Создает маленькую карточку: Логотип + Название снизу"""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_bottom(10)

        logo.set_pixel_size(48)

        label = Gtk.Label(label=name)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(12)

        vbox.append(logo)
        vbox.append(label)
        return vbox

    def create_new_profile(self):
        dialog = Gtk.Window(title="Выберите провайдера",
                            modal=True, default_width=400)

        # Основной контейнер с отступами
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_box.set_margin_bottom(20)
        dialog.set_child(main_box)

        header = Gtk.Label(label="Доступные хранилища")
        header.add_css_class("title-4")  # Используем системный стиль заголовка
        main_box.append(header)

        # Создаем сетку (FlowBox)
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(4)  # По 4 логотипа в ряд
        # Нам не нужно выделение, только клик
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)

        companies = [
            Provider("drive"),
            Provider("yandex"),
            Provider("nextcloud")
        ]

        # Наполняем сетку
        for company in companies:
            child_widget = self.create_company_widget(
                company.title, company.get_image())
            flowbox.append(child_widget)

            container = child_widget.get_parent()
            container.company_id = company.title

        # Подключаем событие клика
        flowbox.connect("child-activated", self.on_company_clicked)
        # Если кликнули — закрываем окно (опционально)
        # flowbox.connect("child-activated", lambda fb, ch: dialog.destroy())

        main_box.append(flowbox)
        dialog.show()

    def create_profile_table_row(self, profile: Profile):
        """Создает одну строку таблицы с двумя колонками"""

        # Горизонтальный контейнер для всей строки

        # Делаем горизонтальный контейнер, чтобы использовать его в таблице
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        row_box.set_margin_start(10)
        row_box.set_margin_end(10)
        row_box.set_margin_top(5)
        row_box.set_margin_bottom(5)

        # Эээээ по моему это названия профилей
        label_id = Gtk.Label(label=profile.title)
        label_id.set_xalign(0)
        label_id.set_hexpand(True)

        # Провайдеры
        provider_icon = profile.provider.get_image()
        provider_icon.set_pixel_size(24)
        provider_caption = Gtk.Label(label=profile.provider.title)
        provider_caption.add_css_class("caption")

        provider_vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=2)

        provider_vbox.append(
            provider_icon)
        provider_vbox.append(provider_caption)

        # Кнопка удаления
        delete_icon = Gtk.Image.new_from_icon_name("user-trash-symbolic")
        delete_icon.set_pixel_size(24)
        delete_caption = Gtk.Label(label="Удалить")
        delete_caption.add_css_class("caption")

        delete_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        delete_vbox.append(delete_icon)
        delete_vbox.append(delete_caption)

        delete_button = Gtk.Button()
        delete_button.set_has_frame(False)
        delete_button.set_child(delete_vbox)

        icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
        icon.set_pixel_size(24)

        # Добавляем все эти приколы
        row_box.append(label_id)
        row_box.append(provider_vbox)
        row_box.append(delete_button)

        row = Gtk.ListBoxRow()
        row.set_activatable(True)
        row.set_child(row_box)

        delete_button.connect("clicked", self.delete_profile, profile.title)
        row.profile_title = profile.title

        return row

    def delete_profile(self, button, profile_title):

        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        try:
            response_raw = bus.call_sync(
                'org.zbus.pompiliusd',
                '/org/zbus/pompiliusd',
                'org.zbus.pompiliusd',
                'DeleteProfile',
                GLib.Variant(
                    '(s)', (profile_title,)),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
        except Exception as e:
            print(f"Ошибка D-Bus: {e}")
        print(f"Жду ручку с бека для удаления: {profile_title}")

    def show_profiles(self):
        # profiles =

        dialog = Gtk.Window(title="Выберите профиль",
                            modal=True, default_width=400)

        # Основной контейнер с отступами
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_box.set_margin_bottom(20)
        dialog.set_child(main_box)

        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

        profiles = []
        try:
            response_raw = bus.call_sync(
                'org.zbus.pompiliusd',
                '/org/zbus/pompiliusd',
                'org.zbus.pompiliusd',
                'ListProfiles',
                None,
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )

            raw_json = response_raw.unpack()[0]

            # 3. Парсим внешний JSON
            response = json.loads(raw_json)

            # 4. Парсим поле data (оно у тебя тоже строка с JSON-массивом)
            profiles_raw = json.loads(response['data'])

            profiles = [Profile(name, Provider(provider))
                        for name, provider in profiles_raw]
        except Exception as e:
            print(f"Ошибка D-Bus: {e}")

        print

        data = profiles
        header = Gtk.Label(label="Доступные профили")
        header.add_css_class("title-4")  # Используем системный стиль заголовка
        main_box.append(header)

        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.set_show_separators(True)  # Рисует линии между строками

        for profile in data:
            row_content = self.create_profile_table_row(profile)

            # В ListBox мы добавляем контент, и он сам оборачивает его в Gtk.ListBoxRow
            list_box.append(row_content)

            # Сохраняем данные для клика
            row_container = row_content.get_parent()
            row_container.row_id = profile.title

        list_box.connect("row-activated", self.mount_directory)

        # Чтобы таблица прокручивалась, если строк много
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(300)
        scrolled.set_child(list_box)

        dialog.set_child(scrolled)
        dialog.show()

    def mount_directory(self, list_box, row):

        # Достаем title, который ты сохранил в методе create_profile_table_row
        title = getattr(row, 'profile_title', "Неизвестно")
        print(f"Кликнули по строке: {title}")

        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        try:
            response_raw = bus.call_sync(
                'org.zbus.pompiliusd',
                '/org/zbus/pompiliusd',
                'org.zbus.pompiliusd',
                'Mount',
                GLib.Variant(
                    '(sss)', (title, 'лютейшийсукамуд', self.current_dir)),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
        except Exception as e:
            print(f"Ошибка D-Bus: {e}")

        list_box.get_root().destroy()

# def get_profiles():
#     pass
#     # bus.call_sync(
#     #     'org.zbus.cloud_api',           # Bus name
#     #     '/org/zbus/cloud_api',          # Object path
#     #     'org.zbus.cloud_api',           # Interface name
#     #     'SayHello',                     # Method
#     #     GLib.Variant('(s)', ("Egor",)), # Аргументы (сигнатура s)
#     #     None,                           # Ожидаемый тип ответа (None для любого)
#     #     Gio.DBusCallFlags.NONE,
#     #     -1,                             # Таймаут по умолчанию
#     #     None
#     # )
#     data = [
#     ("My Yandex", "Amazon",),
#     ("Ne my Yandex", "Google", ),
#     ("Google диск", "WebDAV", )
#     ]
#

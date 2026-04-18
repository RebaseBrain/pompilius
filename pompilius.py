from gi.repository import Nautilus, GObject, Gtk, Pango, Gio, GLib
import tomllib
import os
import json
from urllib.parse import unquote, urlparse

EXTENSION_DIR = os.path.dirname(os.path.abspath(__file__))
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


def get_existing_profiles():
    config_path = os.path.expanduser("~/.config/pompilius/config.toml")
    if not os.path.exists(config_path):
        return {}

    with open(config_path, "rb") as f:
        data = tomllib.load(f)
        return data.get("profiles", {})


class ProfileResponse:
    title: str
    provider: str


def get_rclone_title(title: str) -> str:
    match title:
        case "Yandex Disk":
            return "yandex"
        case "Google Drive":
            return "drive"
        case "Mail.ru Cloud":
            return "mailru"
        case "iCloud Drive":
            return "iclouddrive"
        case "Mega":
            return "mega"
        case "Mail.ru Cloud":
            return "mailru"

    return "unknown"


def get_title_from_rclone(rclone_title: str) -> str:
    match rclone_title:
        case "yandex":
            return "Yandex Disk"
        case "drive":
            return "Google Drive"
        case "mailru":
            return "Mail.ru Cloud"
        case "iclouddrive":
            return "iCloud Drive"
        case "mega":
            return "Mega"
        case "mailru":
            return "Mail.ru Cloud"

    return "unknown"


def get_logo_path_from_rclone(rclone_title: str) -> str:
    match rclone_title:
        case "yandex":
            return "./static/yandex-disk-logo.png"
        case "drive":
            return "./static/google-drive-logo.png"
        case "iclouddrive":
            return "./static/i-cloud-logo.svg"
        case "mailru":
            return "./static/mail-ru-cloud.png"
    return "unknown"


class Provider:
    title: str
    logo_path: str
    settings: str
    rclone_title: str

    def __init__(self, rclone_title):
        self.title = get_title_from_rclone(rclone_title)
        self.logo_path = get_logo_path_from_rclone(rclone_title)
        self.settings_list = []

        try:
            raw_response = bus.call_sync(
                'org.zbus.pompiliusd',           # Bus name
                '/org/zbus/pompiliusd',          # Object path
                'org.zbus.pompiliusd',           # Interface name
                'GetProviderOptions',                     # Method
                # Аргументы (сигнатура s)
                GLib.Variant('(s)', (rclone_title,)),
                # Ожидаемый тип ответа (None для любого)
                None,
                Gio.DBusCallFlags.NONE,
                -1,                             # Таймаут по умолчанию
                None
            )

            raw_json = raw_response.unpack()[0]
            response = json.loads(raw_json)

            temp_list = json.loads(response['data'])

            self.settings_list = {opt['Name']: opt for opt in temp_list}
        except Exception as e:
            print(f"Ошибка D-Bus при создании провайдера: {e}")

    def get_image(self) -> Gtk.Image:
        full_path = os.path.join(EXTENSION_DIR, self.logo_path)
        print(full_path)

        if os.path.exists(full_path):
            return Gtk.Image.new_from_file(full_path)

        return Gtk.Image.new_from_icon_name(self.logo_path)


def call_dbus_method(self):
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
    entry_size: int
    entry_time: int

    def __init__(self, title, provider: Provider):
        self.title = title
        self.provider = provider


class ColumnExtension(GObject.GObject, Nautilus.MenuProvider):
    current_dir: str

    def __init__(self):
        GObject.Object.__init__(self)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.set_show_separators(True)
        self.list_box.connect("row-activated", self.mount_directory)
        self.dialog = None

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

    def show_error_dialog(self, parent, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=parent,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title,
            secondary_text=message
        )
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.show()

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

    def on_company_clicked(self, flowbox, child, dialog):
        # child.company_id содержит читаемое название, нам нужно техническое
        # В create_new_profile мы задали container.company_id = company.title (читаемое)
        # Нам нужен объект Provider, который мы создали в списке companies
        rclone_name = get_rclone_title(child.company_id)
        provider = Provider(rclone_name)

        input_dialog = Gtk.Window(
            title=f"Настройка {provider.title}", modal=True)
        input_dialog.set_default_size(350, -1)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_end(15)

        vbox.append(Gtk.Label(label="Название профиля", xalign=0))
        entry_profile_name = Gtk.Entry()
        vbox.append(entry_profile_name)

        entries_map = {}

        for info in provider.settings_list.values():
            name = info.get('Name')

            label = Gtk.Label(label=name, xalign=0)
            vbox.append(label)

            entry = Gtk.Entry()

            clean_name = name.lower()
            if "password" in clean_name or "secret" in clean_name:
                entry.set_visibility(False)

            vbox.append(entry)

            entries_map[name] = entry

        btn_create = Gtk.Button(label="Создать и привязать")
        btn_create.add_css_class("suggested-action")

        btn_create.connect(
            "clicked",
            self.create_profile,
            input_dialog,
            rclone_name,
            entry_profile_name,
            entries_map,
            provider.settings_list
        )

        vbox.append(btn_create)
        input_dialog.set_child(vbox)
        input_dialog.present()
        dialog.destroy()

    def create_profile(self, button, input_dialog, rclone_name, entry_profile_name, entries_map, settings_map):
        # 1. Достаем имя профиля
        profile_title = entry_profile_name.get_text().strip()

        # 2. Проверка на существование (твой код)
        profiles = get_existing_profiles()
        if profile_title in profiles:
            self.show_error_dialog(
                input_dialog,
                "Профиль уже существует",
                f"Профиль '{profile_title}' уже используется в: {
                    profiles[profile_title]}"
            )
            return
        result_params = {}
        for key in settings_map.keys():
            if key in entries_map:
                result_params[key] = entries_map[key].get_text()

        try:
            params_json_string = json.dumps(result_params)

            bus.call_sync(
                'org.zbus.pompiliusd',
                '/org/zbus/pompiliusd',
                'org.zbus.pompiliusd',
                'CreateProfile',
                GLib.Variant(
                    '(sss)',
                    (profile_title, rclone_name, params_json_string)
                ),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )

        except Exception as e:
            print(f"Ошибка D-Bus: {e}")
            self.show_error_dialog(input_dialog, "Ошибка D-Bus", str(e))
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
            Provider("iclouddrive"),
            Provider("mailru")
        ]

        # Наполняем сетку
        for company in companies:
            child_widget = self.create_company_widget(
                company.title, company.get_image())
            flowbox.append(child_widget)

            container = child_widget.get_parent()
            container.company_id = company.title

        # Подключаем событие клика
        flowbox.connect("child-activated", self.on_company_clicked, dialog)
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
            self.load_profiles()
        except Exception as e:
            print(f"Ошибка D-Bus: {e}")
        print(f"Жду ручку с бека для удаления: {profile_title}")

    def show_profiles(self):
        # Создаем окно
        self.dialog = Gtk.Window(
            title="Выберите профиль", modal=True, default_width=400)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_box.set_margin_bottom(20)
        main_box.set_margin_top(10)

        header = Gtk.Label(label="Доступные профили")
        header.add_css_class("title-4")
        main_box.append(header)

        # Скролл-зона
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(300)
        # Привязываем наш "долгоживущий" ListBox
        scrolled.set_child(self.list_box)
        main_box.append(scrolled)

        # Сначала загружаем данные в ListBox
        self.load_profiles()

        self.dialog.set_child(main_box)
        self.dialog.show()

    def mount_directory(self, list_box, row):
        # 1. Получаем имя профиля из выбранной строки
        title = getattr(row, 'profile_title', "Неизвестно")

        # 2. Создаем окно для уточнения параметров перед монтированием
        mount_params_dialog = Gtk.Window(
            title=f"Параметры монтирования: {title}",
            modal=True,
            default_width=300
        )

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_end(15)
        mount_params_dialog.set_child(vbox)

        # Поле ввода Max Size
        vbox.append(Gtk.Label(label="Максимальный размер кэша (ГБ):", xalign=0))
        entry_size = Gtk.Entry()
        entry_size.set_text("10")  # Значение по умолчанию
        vbox.append(entry_size)

        # Поле ввода Max Time
        vbox.append(Gtk.Label(label="Время жизни кэша (часы):", xalign=0))
        entry_time = Gtk.Entry()
        entry_time.set_text("24")  # Значение по умолчанию
        vbox.append(entry_time)

        # Кнопка подтверждения
        btn_confirm = Gtk.Button(label="Подключить")
        btn_confirm.add_css_class("suggested-action")

        # Передаем всё необходимое в фпередаю название профиля, открывалось окошко,ункцию исполнения
        btn_confirm.connect(
            "clicked",
            self.execute_mount,
            title,
            entry_size,
            entry_time,
            mount_params_dialog
        )

        vbox.append(btn_confirm)
        mount_params_dialog.present()

    def execute_mount(self, button, title, entry_size, entry_time, current_dialog):
        # 3. Собираем данные из полей
        max_size = entry_size.get_text().strip()
        max_time = entry_time.get_text().strip()

        print(f"Выполняю монтирование: {title} в {
              self.current_dir} ({max_size}, {max_time})")

        try:
            # 4. Реальный вызов D-Bus
            bus.call_sync(
                'org.zbus.pompiliusd',
                '/org/zbus/pompiliusd',
                'org.zbus.pompiliusd',
                'Mount',
                GLib.Variant('(ssss)', (
                    title,
                    self.current_dir,
                    max_size,
                    max_time
                )),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )

            current_dialog.destroy()

            if self.dialog:
                self.dialog.destroy()
                self.dialog = None

        except Exception as e:
            self.show_error_dialog(
                current_dialog, "Ошибка монтирования", str(e))

    def load_profiles(self):
        """Очищает список и загружает данные из D-Bus заново"""
        # 1. Очистка текущих строк в ListBox
        while True:
            child = self.list_box.get_first_child()
            if not child:
                break
            self.list_box.remove(child)

        # 2. Получение данных
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
            response = json.loads(raw_json)
            profiles_raw = json.loads(response['data'])

            profiles = [Profile(name, Provider(provider))
                        for name, provider in profiles_raw]
        except Exception as e:
            print(f"Ошибка загрузки профилей: {e}")

        # 3. Наполнение ListBox новыми данными
        for profile in profiles:
            row = self.create_profile_table_row(profile)
            self.list_box.append(row)

        # Если окно уже открыто, просим его перерисоваться
        self.list_box.queue_draw()

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

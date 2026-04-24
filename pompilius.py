from gi.repository import Nautilus, GObject, Gtk, Pango, Gio, GLib
import tomllib
import os
import json
from urllib.parse import unquote, urlparse

EXTENSION_DIR = os.path.dirname(os.path.abspath(__file__))
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
MAX_TIMEOUT_MS = 2**31 - 1 # Максимально возможный таймаут (около 24 дней)


_profiles_cache = None
_profiles_cache_mtime = 0

def get_existing_profiles():
    global _profiles_cache, _profiles_cache_mtime
    config_path = os.path.expanduser("~/.config/pompilius/config.toml")
    if not os.path.exists(config_path):
        return {}

    try:
        mtime = os.path.getmtime(config_path)
        if _profiles_cache is not None and mtime <= _profiles_cache_mtime:
            return _profiles_cache

        with open(config_path, "rb") as f:
            data = tomllib.load(f)
            _profiles_cache = data.get("profiles", {})
            _profiles_cache_mtime = mtime
            return _profiles_cache
    except Exception as e:
        print(f"Ошибка при чтении конфига: {e}")
        return _profiles_cache if _profiles_cache is not None else {}


def get_rclone_title(title: str) -> str:
    match title:
        case "Яндекс.Диск":
            return "yandex"
        case "Google Drive":
            return "drive"
        case "Облако@Mail.ru":
            return "mailru"
        case "iCloud Drive":
            return "iclouddrive"
        case "MEGA":
            return "mega"
        case "WebDAV":
            return "webdav"
    return "unknown"


def get_title_from_rclone(rclone_title: str) -> str:
    match rclone_title:
        case "yandex":
            return "Яндекс.Диск"
        case "drive":
            return "Google Drive"
        case "mailru":
            return "Облако@Mail.ru"
        case "iclouddrive":
            return "iCloud Drive"
        case "mega":
            return "MEGA"
        case "webdav":
            return "WebDAV"
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
    def __init__(self, rclone_title):
        self.rclone_title = rclone_title
        self.title = get_title_from_rclone(rclone_title)
        self.logo_path = get_logo_path_from_rclone(rclone_title)
        self.settings_list = {}

    def get_image(self) -> Gtk.Image:
        full_path = os.path.join(EXTENSION_DIR, self.logo_path)
        if os.path.exists(full_path):
            return Gtk.Image.new_from_file(full_path)
        return Gtk.Image.new_from_icon_name(self.logo_path)


def set_margins(widget, value):
    widget.set_margin_top(value)
    widget.set_margin_bottom(value)
    widget.set_margin_start(value)
    widget.set_margin_end(value)


class Profile:
    def __init__(self, title, provider: Provider):
        self.title = title
        self.provider = provider


class ColumnExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        GObject.Object.__init__(self)
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.set_show_separators(True)
        self.list_box.connect("row-activated", self.mount_directory)
        self.dialog = None
        self.current_dir = None

    def get_background_items(self, folder):
        self.current_dir = unquote(urlparse(folder.get_uri()).path)
        item = Nautilus.MenuItem(
            name='Pompilius::AddRemote',
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

        dialog.connect("response", on_response)
        dialog.show()

    def create_new_profile(self):
        dialog = Gtk.Window(title="Выберите провайдера", modal=True, default_width=400)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_box.set_margin_bottom(20)
        dialog.set_child(main_box)

        header = Gtk.Label(label="Доступные хранилища")
        header.add_css_class("title-4")
        main_box.append(header)

        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(4)
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)

        providers = ["drive", "yandex", "iclouddrive", "mailru", "webdav"]
        for p_name in providers:
            provider = Provider(p_name)
            child_widget = self.create_company_widget(provider.title, provider.get_image())
            flowbox.append(child_widget)
            container = child_widget.get_parent()
            container.rclone_title = p_name

        flowbox.connect("child-activated", self.on_company_clicked, dialog)
        main_box.append(flowbox)
        dialog.show()

    def on_company_clicked(self, flowbox, child, dialog):
        rclone_name = child.rclone_title
        
        # Загружаем настройки провайдера асинхронно перед открытием диалога ввода
        bus.call(
            'org.zbus.pompiliusd',
            '/org/zbus/pompiliusd',
            'org.zbus.pompiliusd',
            'GetProviderOptions',
            GLib.Variant('(s)', (rclone_name,)),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            self.on_provider_options_received,
            (rclone_name, dialog)
        )

    def on_provider_options_received(self, connection, res, user_data):
        rclone_name, parent_dialog = user_data
        try:
            raw_response = connection.call_finish(res)
            raw_json = raw_response.unpack()[0]
            response = json.loads(raw_json)
            temp_list = json.loads(response['data'])
            settings_list = {opt['Name']: opt for opt in temp_list}
            
            provider = Provider(rclone_name)
            provider.settings_list = settings_list
            
            self.show_profile_input_dialog(provider, parent_dialog)
        except Exception as e:
            print(f"Ошибка при получении опций провайдера: {e}")

    def show_profile_input_dialog(self, provider, parent_dialog):
        input_dialog = Gtk.Window(title=f"Настройка {provider.title}", modal=True)
        input_dialog.set_default_size(350, -1)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(vbox, 15)

        vbox.append(Gtk.Label(label="Название профиля", xalign=0))
        entry_profile_name = Gtk.Entry()
        vbox.append(entry_profile_name)

        entries_map = {}
        for name, info in provider.settings_list.items():
            vbox.append(Gtk.Label(label=name, xalign=0))
            entry = Gtk.Entry()
            if "password" in name.lower() or "secret" in name.lower():
                entry.set_visibility(False)
            vbox.append(entry)
            entries_map[name] = entry

        btn_create = Gtk.Button(label="Создать и привязать")
        btn_create.add_css_class("suggested-action")
        btn_create.connect("clicked", self.create_profile_clicked, input_dialog, provider.rclone_title, entry_profile_name, entries_map, provider.settings_list)

        vbox.append(btn_create)
        input_dialog.set_child(vbox)
        input_dialog.present()
        parent_dialog.destroy()

    def create_profile_clicked(self, button, input_dialog, rclone_name, entry_profile_name, entries_map, settings_map):
        profile_title = entry_profile_name.get_text().strip()
        profiles = get_existing_profiles()
        if profile_title in profiles:
            self.show_error_dialog(input_dialog, "Профиль уже существует", f"Профиль '{profile_title}' уже используется в: {profiles[profile_title]}")
            return

        button.set_sensitive(False)
        button.set_label("Создание...")

        result_params = {key: entry.get_text() for key, entry in entries_map.items()}
        try:
            params_json_string = json.dumps(result_params)
            bus.call(
                'org.zbus.pompiliusd',
                '/org/zbus/pompiliusd',
                'org.zbus.pompiliusd',
                'CreateProfile',
                GLib.Variant('(sss)', (profile_title, rclone_name, params_json_string)),
                None,
                Gio.DBusCallFlags.NONE,
                MAX_TIMEOUT_MS,
                None,
                self.on_profile_created,
                (input_dialog, button)
            )
        except Exception as e:
            button.set_sensitive(True)
            button.set_label("Создать и привязать")
            print(f"Ошибка D-Bus: {e}")
            self.show_error_dialog(input_dialog, "Ошибка D-Bus", str(e))

    def on_profile_created(self, connection, res, user_data):
        input_dialog, button = user_data
        try:
            connection.call_finish(res)
            input_dialog.destroy()
        except Exception as e:
            button.set_sensitive(True)
            button.set_label("Создать и привязать")
            print(f"Ошибка при создании профиля: {e}")
            self.show_error_dialog(input_dialog, "Ошибка при создании", str(e))

    def create_company_widget(self, name, logo):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_bottom(10)
        logo.set_pixel_size(48)
        label = Gtk.Label(label=name)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(12)
        vbox.append(logo)
        vbox.append(label)
        return vbox

    def create_profile_table_row(self, profile: Profile):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        set_margins(row_box, 10)

        label_id = Gtk.Label(label=profile.title)
        label_id.set_xalign(0)
        label_id.set_hexpand(True)

        provider_icon = profile.provider.get_image()
        provider_icon.set_pixel_size(24)
        provider_caption = Gtk.Label(label=profile.provider.title)
        provider_caption.add_css_class("caption")

        provider_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        provider_vbox.append(provider_icon)
        provider_vbox.append(provider_caption)

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

        row_box.append(label_id)
        row_box.append(provider_vbox)
        row_box.append(delete_button)

        row = Gtk.ListBoxRow()
        row.set_activatable(True)
        row.set_child(row_box)
        row.profile_title = profile.title

        delete_button.connect("clicked", self.delete_profile, profile.title)
        return row

    def delete_profile(self, button, profile_title):
        bus.call(
            'org.zbus.pompiliusd',
            '/org/zbus/pompiliusd',
            'org.zbus.pompiliusd',
            'DeleteProfile',
            GLib.Variant('(s)', (profile_title,)),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            self.on_profile_deleted,
            None
        )

    def on_profile_deleted(self, connection, res, user_data):
        try:
            connection.call_finish(res)
            self.load_profiles()
        except Exception as e:
            print(f"Ошибка при удалении профиля: {e}")

    def show_profiles(self):
        self.dialog = Gtk.Window(title="Выберите профиль", modal=True, default_width=400)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        set_margins(main_box, 15)

        header = Gtk.Label(label="Доступные профили")
        header.add_css_class("title-4")
        main_box.append(header)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(300)
        scrolled.set_child(self.list_box)
        main_box.append(scrolled)

        self.load_profiles()
        self.dialog.set_child(main_box)
        self.dialog.show()

    def load_profiles(self):
        bus.call(
            'org.zbus.pompiliusd',
            '/org/zbus/pompiliusd',
            'org.zbus.pompiliusd',
            'ListProfiles',
            None,
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            self.on_profiles_loaded,
            None
        )

    def on_profiles_loaded(self, connection, res, user_data):
        try:
            response_raw = connection.call_finish(res)
            raw_json = response_raw.unpack()[0]
            response = json.loads(raw_json)
            profiles_raw = json.loads(response['data'])

            # Очистка
            while True:
                child = self.list_box.get_first_child()
                if not child: break
                self.list_box.remove(child)

            for name, provider_name in profiles_raw:
                profile = Profile(name, Provider(provider_name))
                row = self.create_profile_table_row(profile)
                self.list_box.append(row)
            
            self.list_box.queue_draw()
        except Exception as e:
            print(f"Ошибка при загрузке профилей: {e}")

    def mount_directory(self, list_box, row):
        title = getattr(row, 'profile_title', "Неизвестно")
        mount_params_dialog = Gtk.Window(title=f"Параметры монтирования: {title}", modal=True, default_width=300)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(vbox, 15)
        mount_params_dialog.set_child(vbox)

        vbox.append(Gtk.Label(label="Максимальный размер кеша (ГБ):", xalign=0))
        entry_size = Gtk.Entry()
        entry_size.set_text("10")
        vbox.append(entry_size)

        vbox.append(Gtk.Label(label="Время жизни кеша (часы):", xalign=0))
        entry_time = Gtk.Entry()
        entry_time.set_text("24")
        vbox.append(entry_time)

        btn_confirm = Gtk.Button(label="Подключить")
        btn_confirm.add_css_class("suggested-action")
        btn_confirm.connect("clicked", self.execute_mount, title, entry_size, entry_time, mount_params_dialog)

        vbox.append(btn_confirm)
        mount_params_dialog.present()

    def execute_mount(self, button, title, entry_size, entry_time, current_dialog):
        max_size = entry_size.get_text().strip()
        max_time = entry_time.get_text().strip()

        button.set_sensitive(False)
        button.set_label("Подключение...")

        try:
            bus.call(
                'org.zbus.pompiliusd',
                '/org/zbus/pompiliusd',
                'org.zbus.pompiliusd',
                'Mount',
                GLib.Variant('(ssss)', (title, self.current_dir, max_size, max_time)),
                None,
                Gio.DBusCallFlags.NONE,
                MAX_TIMEOUT_MS,
                None,
                self.on_mount_finished,
                (current_dialog, button)
            )
        except Exception as e:
            button.set_sensitive(True)
            button.set_label("Подключить")
            self.show_error_dialog(current_dialog, "Ошибка монтирования", str(e))

    def on_mount_finished(self, connection, res, user_data):
        current_dialog, button = user_data
        try:
            connection.call_finish(res)
            current_dialog.destroy()
            if self.dialog:
                self.dialog.destroy()
                self.dialog = None
        except Exception as e:
            button.set_sensitive(True)
            button.set_label("Подключить")
            self.show_error_dialog(current_dialog, "Ошибка монтирования", str(e))

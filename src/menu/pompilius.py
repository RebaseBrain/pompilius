import gi
from gi.repository import Nautilus, GObject, Gtk, Pango, Gio, GLib
import tomllib
import os
from urllib.parse import unquote, urlparse

from errors import CloudError
from constants import (
    DBUS_IFACE,
    DBUS_NAME,
    DBUS_PATH,
    EXTENSION_DIR,
    LOGO_MAP,
    MAX_TIMEOUT_MS,
    PROTOCOL_ICONS,
    R_MAP,
)

gi.require_version("Gtk", "4.0")
gi.require_version("Notify", "0.7")

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


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


def get_available_providers():
    """Запрашивает список поддерживаемых провайдеров у демона"""
    try:
        response_raw = bus.call_sync(
            DBUS_NAME,
            DBUS_PATH,
            DBUS_IFACE,
            "ListAvailableProviders",
            None,
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
        # Получаем список названий провайдеров от демона
        providers = response_raw.unpack()[0]
        return providers
    except GLib.Error as e:
        dbus_err = Gio.dbus_error_get_remote_error(e)
        print(
            f"[Pompilius] WARNING: D-Bus ошибка при получении провайдеров ({dbus_err}): {e.message}"
        )
        return ["drive", "yandex", "mailru", "webdav"]  # Fallback
    except Exception as e:
        print(f"[Pompilius] ERROR: Ошибка при получении списка провайдеров: {e}")
        return ["drive", "yandex", "mailru", "webdav"]  # Fallback


def get_rclone_title(title: str) -> str:
    mapping = {v: k for k, v in R_MAP.items()}
    return mapping.get(title, "unknown")


def get_title_from_rclone(rclone_title: str) -> str:
    return R_MAP.get(rclone_title, rclone_title.capitalize())


def get_logo_path_from_rclone(rclone_title: str) -> str:
    if rclone_title in LOGO_MAP:
        return f"./static/{LOGO_MAP[rclone_title]}"

    return PROTOCOL_ICONS.get(rclone_title, "folder-remote-symbolic")


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
        self.dialog = None
        self.current_dir = None

    def get_background_items(self, folder):
        self.current_dir = unquote(urlparse(folder.get_uri()).path)
        item = Nautilus.MenuItem(
            name="Pompilius::AddRemote",
            label="Добавить удалённое хранилище",
            tip="Добавить хранилище в текущую папку",
        )
        item.connect("activate", self.menu_activate)
        return [item]

    def show_error_dialog(self, parent, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=parent,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title,
            secondary_text=message,
        )
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.show()

    def menu_activate(self, menu):
        self.show_profiles()

    def create_new_profile(self, refresh_callback=None, parent_window=None):
        from add_profile_dialog import AddProfileDialog

        # Если родительское окно не передано, пытаемся найти активное
        if not parent_window:
            for window in Gtk.Window.list_toplevels():
                if window.get_visible():
                    parent_window = window
                    break

        prov_dialog = AddProfileDialog(
            self, transient_for=parent_window, refresh_callback=refresh_callback
        )
        prov_dialog.present()

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

    def create_profile_table_row(self, profile: Profile, delete_callback=None):
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

        if delete_callback:
            delete_button.connect("clicked", delete_callback, profile.title, row)
        else:
            delete_button.connect("clicked", self.delete_profile, profile.title)
        return row

    def delete_profile(self, button, profile_title):
        bus.call(
            DBUS_NAME,  # Bus name
            DBUS_PATH,  # Object path
            DBUS_IFACE,  # Interface name
            "DeleteProfile",
            GLib.Variant("(s)", (profile_title,)),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            self.on_profile_deleted,
            None,
        )

    def on_profile_deleted(self, connection, res, user_data):
        try:
            connection.call_finish(res)
            # В ColumnExtension нет self.load_profiles(), метод вызывается только если это резервный путь
            print(f"[Pompilius] INFO: Профиль удален (fallback-обработчик).")
        except GLib.Error as e:
            dbus_err = Gio.dbus_error_get_remote_error(e)
            print(
                f"[Pompilius] ERROR: Ошибка D-Bus при удалении профиля ({dbus_err}): {e.message}"
            )
        except Exception as e:
            print(f"[Pompilius] ERROR: Ошибка при удалении профиля: {e}")

    def show_profiles(self):
        from profiles_dialog import ProfilesDialog

        self.dialog = ProfilesDialog(bus, self, self.current_dir)
        self.dialog.present()

    def mount_directory(self, list_box, row):
        title = getattr(row, "profile_title", "Неизвестно")
        mount_params_dialog = Gtk.Window(
            title=f"Параметры монтирования: {title}", modal=True, default_width=300
        )
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
        btn_confirm.connect(
            "clicked",
            self.execute_mount,
            title,
            entry_size,
            entry_time,
            mount_params_dialog,
        )

        vbox.append(btn_confirm)
        mount_params_dialog.present()

    def execute_mount(self, button, title, entry_size, entry_time, current_dialog):
        max_size = entry_size.get_text().strip()
        max_time = entry_time.get_text().strip()

        button.set_sensitive(False)
        button.set_label("Подключение...")

        try:
            bus.call(
                DBUS_NAME,  # Bus name
                DBUS_PATH,  # Object path
                DBUS_IFACE,  # Interface name
                "Mount",
                GLib.Variant("(ssss)", (title, self.current_dir, max_size, max_time)),
                None,
                Gio.DBusCallFlags.NONE,
                MAX_TIMEOUT_MS,
                None,
                self.on_mount_finished,
                (current_dialog, button),
            )
        except Exception as e:
            button.set_sensitive(True)
            button.set_label("Подключить")
            self.show_error_dialog(current_dialog, "Системная ошибка D-Bus", str(e))

    def on_mount_finished(self, connection, res, user_data):
        current_dialog, button = user_data
        try:
            connection.call_finish(res)
            current_dialog.destroy()
            if self.dialog:
                self.dialog.destroy()
                self.dialog = None
        except GLib.Error as e:
            button.set_sensitive(True)
            button.set_label("Подключить")
            dbus_err = Gio.dbus_error_get_remote_error(e)

            if dbus_err == CloudError.REQWEST:
                self.show_error_dialog(
                    current_dialog, "Ошибка сети", "Нет связи с API rclone"
                )
            elif dbus_err == CloudError.CONVERT:
                self.show_error_dialog(
                    current_dialog,
                    "Ошибка параметров",
                    "Убедитесь, что размер и время жизни кеша указаны целыми числами",
                )
            elif dbus_err == CloudError.RCLONE:
                self.show_error_dialog(current_dialog, "Ошибка монтирования", e.message)
            elif dbus_err == CloudError.IO:
                self.show_error_dialog(
                    current_dialog, "Ошибка файловой системы", e.message
                )
            else:
                self.show_error_dialog(current_dialog, "Ошибка D-Bus", e.message)
        except Exception as e:
            button.set_sensitive(True)
            button.set_label("Подключить")
            self.show_error_dialog(current_dialog, "Непредвиденная ошибка", str(e))

import gi
from gi.repository import Gtk, GObject, Pango, Gio, GLib
from pompilius import (
    DBUS_IFACE,
    DBUS_NAME,
    DBUS_PATH,
    Provider,
    get_available_providers,
    set_margins,
    MAX_TIMEOUT_MS,
    bus,
    get_existing_profiles,
)
import json

gi.require_version("Gtk", "4.0")


class AddProfileDialog(Gtk.Window):
    def __init__(self, parent_extension, transient_for=None, refresh_callback=None):
        super().__init__(
            title="Добавление хранилища",
            modal=True,
            default_width=500,
            default_height=700,
            transient_for=transient_for,
        )
        self.parent_ext = parent_extension
        self.refresh_callback = refresh_callback
        self.filter_text = ""
        self.selected_provider_name = None

        self.setup_ui()

    def setup_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        set_margins(main_box, 15)
        self.set_child(main_box)

        name_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        name_section.append(Gtk.Label(label="Название профиля", xalign=0))
        self.entry_profile_name = Gtk.Entry(
            placeholder_text="Например, Мой Яндекс.Диск"
        )
        name_section.append(self.entry_profile_name)
        main_box.append(name_section)

        search_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        search_section.append(Gtk.Label(label="Провайдер", xalign=0))
        self.search_entry = Gtk.SearchEntry(placeholder_text="Поиск по наванию")
        self.search_entry.connect("search-changed", self.on_search_changed)
        search_section.append(self.search_entry)
        main_box.append(search_section)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(4)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_filter_func(self.filter_func)
        self.flowbox.connect("child-activated", self.on_provider_selected)

        self.provider_widgets = {}

        for p_name in get_available_providers():
            provider = Provider(p_name)

            toggle_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            set_margins(toggle_box, 5)

            img = provider.get_image()
            img.set_pixel_size(48)
            toggle_box.append(img)

            lbl = Gtk.Label(label=provider.title)
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            lbl.set_max_width_chars(10)
            toggle_box.append(lbl)

            self.flowbox.append(toggle_box)
            child = toggle_box.get_parent()
            child.rclone_title = p_name
            child.display_name = provider.title.lower()
            self.provider_widgets[p_name] = child

        scrolled.set_child(self.flowbox)
        main_box.append(scrolled)

        self.options_scrolled = Gtk.ScrolledWindow()
        self.options_scrolled.set_vexpand(True)
        self.options_scrolled.set_min_content_height(150)

        self.options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(self.options_box, 10)
        self.options_scrolled.set_child(self.options_box)
        main_box.append(self.options_scrolled)

        self.entries_map = {}
        self.current_settings_map = {}

        self.btn_create = Gtk.Button(label="Создать и привязать")
        self.btn_create.add_css_class("suggested-action")
        self.btn_create.set_sensitive(False)  # Ждём выбора провайдера
        self.btn_create.connect("clicked", self.on_create_clicked)
        main_box.append(self.btn_create)

    def on_search_changed(self, entry):
        self.filter_text = entry.get_text().lower()
        self.flowbox.invalidate_filter()

    def filter_func(self, child):
        if not self.filter_text:
            return True
        return (
            self.filter_text in child.display_name
            or self.filter_text in child.rclone_title
        )

    def on_provider_selected(self, flowbox, child):
        self.selected_provider_name = child.rclone_title
        self.btn_create.set_sensitive(True)

        bus.call(
            DBUS_NAME,
            DBUS_PATH,
            DBUS_IFACE,
            "GetProviderOptions",
            GLib.Variant("(s)", (self.selected_provider_name,)),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            self.on_options_received,
            None,
        )

    def on_options_received(self, connection, res, user_data):
        try:
            raw_response = connection.call_finish(res)
            raw_json = raw_response.unpack()[0]
            response = json.loads(raw_json)
            temp_list = json.loads(response["data"])

            while True:
                child = self.options_box.get_first_child()
                if not child:
                    break
                self.options_box.remove(child)

            self.entries_map = {}
            self.current_settings_map = {opt["Name"]: opt for opt in temp_list}

            for name, info in self.current_settings_map.items():
                self.options_box.append(Gtk.Label(label=name, xalign=0))
                entry = Gtk.Entry()
                if "password" in name.lower() or "secret" in name.lower():
                    entry.set_visibility(False)
                self.options_box.append(entry)
                self.entries_map[name] = entry

        except Exception as e:
            print(f"Ошибка получения опций: {e}")

    def on_create_clicked(self, button):
        profile_title = self.entry_profile_name.get_text().strip()
        if not profile_title:
            self.parent_ext.show_error_dialog(
                self, "Ошибка", "Введите название профиля"
            )
            return

        profiles = get_existing_profiles()
        if profile_title in profiles:
            self.parent_ext.show_error_dialog(
                self, "Ошибка", f"Профиль '{profile_title}' уже существует"
            )
            return

        self.btn_create.set_sensitive(False)
        self.btn_create.set_label("Создание...")

        result_params = {
            key: entry.get_text() for key, entry in self.entries_map.items()
        }
        try:
            params_json_string = json.dumps(result_params)
            bus.call(
                DBUS_NAME,
                DBUS_PATH,
                DBUS_IFACE,
                "CreateProfile",
                GLib.Variant(
                    "(sss)",
                    (profile_title, self.selected_provider_name, params_json_string),
                ),
                None,
                Gio.DBusCallFlags.NONE,
                MAX_TIMEOUT_MS,
                None,
                self.on_profile_created,
                None,
            )
        except Exception as e:
            self.btn_create.set_sensitive(True)
            self.btn_create.set_label("Создать и привязать")
            self.parent_ext.show_error_dialog(self, "Ошибка D-Bus", str(e))

    def on_profile_created(self, connection, res, user_data):
        try:
            connection.call_finish(res)
            if self.refresh_callback:
                self.refresh_callback()
            self.destroy()
        except Exception as e:
            self.btn_create.set_sensitive(True)
            self.btn_create.set_label("Создать и привязать")
            self.parent_ext.show_error_dialog(self, "Ошибка при создании", str(e))

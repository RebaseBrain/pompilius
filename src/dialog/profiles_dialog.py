import gi
from gi.repository import Gtk, Gio, GLib
import json
from constants import DBUS_NAME, DBUS_PATH, DBUS_IFACE
from pompilius import (
    Provider,
    Profile,
    set_margins,
    get_available_providers,
    get_title_from_rclone,
)

gi.require_version("Gtk", "4.0")


class ProfilesDialog(Gtk.Window):
    def __init__(self, bus, parent_extension, current_dir):
        super().__init__(
            title="Управление профилями",
            modal=True,
            default_width=500,
            default_height=600,
        )
        self.bus = bus
        self.parent_ext = parent_extension
        self.current_dir = current_dir

        self.all_profiles = []
        self.filter_text = ""
        self.filter_provider = "All"

        self.setup_ui()
        self.load_profiles()

    def setup_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        set_margins(main_box, 15)
        self.set_child(main_box)

        # Панель поиска и фильтрации
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.search_entry = Gtk.SearchEntry(placeholder_text="Поиск профиля...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        controls_box.append(self.search_entry)

        # Кнопка добавления нового профиля
        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.set_tooltip_text("Добавить новое хранилище")
        add_btn.connect("clicked", self.on_add_clicked)
        controls_box.append(add_btn)

        # Кнопка обновления
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Обновить список")
        refresh_btn.connect("clicked", lambda b: self.load_profiles())
        controls_box.append(refresh_btn)

        filter_titles = ["All"] + sorted(
            [get_title_from_rclone(p) for p in get_available_providers()]
        )
        self.provider_filter = Gtk.DropDown.new_from_strings(filter_titles)
        self.provider_filter.connect("notify::selected", self.on_filter_changed)
        controls_box.append(self.provider_filter)

        main_box.append(controls_box)

        # Сортировка
        sort_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        sort_box.append(Gtk.Label(label="Сортировать по:"))

        self.sort_type = Gtk.DropDown.new_from_strings(
            ["Имени (А-Я)", "Имени (Я-А)", "Провайдеру (А-Я)", "Провайдеру (Я-А)"]
        )
        self.sort_type.connect("notify::selected", self.on_sort_changed)
        sort_box.append(self.sort_type)
        main_box.append(sort_box)

        # Список профилей
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.set_show_separators(True)
        self.list_box.connect("row-activated", self.on_row_activated)

        # Настройка фильтрации и сортировки для ListBox
        self.list_box.set_filter_func(self.filter_func)
        self.list_box.set_sort_func(self.sort_func)

        scrolled.set_child(self.list_box)
        main_box.append(scrolled)

    def load_profiles(self):
        self.bus.call(
            DBUS_NAME,
            DBUS_PATH,
            DBUS_IFACE,
            "ListProfiles",
            None,
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            self.on_profiles_loaded,
            None,
        )

    def on_profiles_loaded(self, connection, res, user_data):
        try:
            response_raw = connection.call_finish(res)
            raw_json = response_raw.unpack()[0]
            response = json.loads(raw_json)
            profiles_raw = json.loads(response["data"])

            # Очистка
            while True:
                child = self.list_box.get_first_child()
                if not child:
                    break
                self.list_box.remove(child)

            self.all_profiles = []
            for name, provider_name in profiles_raw:
                profile = Profile(name, Provider(provider_name))
                self.all_profiles.append(profile)
                # Передаем наш обработчик удаления
                row = self.parent_ext.create_profile_table_row(
                    profile, delete_callback=self.delete_profile_handler
                )
                row._profile_data = profile
                self.list_box.append(row)

            self.list_box.invalidate_filter()
            self.list_box.invalidate_sort()
        except Exception as e:
            print(f"Ошибка при загрузке профилей: {e}")

    def delete_profile_handler(self, button, profile_title, row):
        # Сразу убираем из UI (оптимистичное удаление)
        self.list_box.remove(row)

        # Вызываем D-Bus
        self.bus.call(
            DBUS_NAME,
            DBUS_PATH,
            DBUS_IFACE,
            "DeleteProfile",
            GLib.Variant("(s)", (profile_title,)),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            self.on_profile_deleted,
            profile_title,
        )

    def on_profile_deleted(self, connection, res, profile_title):
        try:
            connection.call_finish(res)
            print(f"Профиль {profile_title} успешно удален")
        except Exception as e:
            print(f"Ошибка при удалении {profile_title}: {e}. Перезагружаем список.")
            # В случае ошибки перезагружаем список полностью
            self.load_profiles()

    def on_search_changed(self, entry):
        self.filter_text = entry.get_text().lower()
        self.list_box.invalidate_filter()

    def on_filter_changed(self, dropdown, pspec):
        self.filter_provider = dropdown.get_selected_item().get_string()
        self.list_box.invalidate_filter()

    def on_sort_changed(self, dropdown, pspec):
        self.list_box.invalidate_sort()

    def filter_func(self, row):
        profile = row._profile_data

        # Фильтр по тексту
        if self.filter_text and self.filter_text not in profile.title.lower():
            return False

        # Фильтр по провайдеру
        if (
            self.filter_provider != "All"
            and profile.provider.title != self.filter_provider
        ):
            return False

        return True

    def sort_func(self, row1, row2):
        p1 = row1._profile_data
        p2 = row2._profile_data
        sort_idx = self.sort_type.get_selected()

        if sort_idx == 0:  # Имя А-Я
            return 1 if p1.title.lower() > p2.title.lower() else -1
        elif sort_idx == 1:  # Имя Я-А
            return -1 if p1.title.lower() > p2.title.lower() else 1
        elif sort_idx == 2:  # Провайдер А-Я
            return 1 if p1.provider.title.lower() > p2.provider.title.lower() else -1
        elif sort_idx == 3:  # Провайдер Я-А
            return -1 if p1.provider.title.lower() > p2.provider.title.lower() else 1
        return 0

    def on_add_clicked(self, button):
        self.parent_ext.create_new_profile(
            refresh_callback=self.load_profiles, parent_window=self
        )
        # Не закрываем, чтобы увидеть результат обновления

    def on_row_activated(self, list_box, row):
        self.parent_ext.mount_directory(list_box, row)
        self.destroy()

from gi.repository import Nautilus, GObject, Gtk, Pango, Gio, GLib
import os

EXTENSION_DIR = os.path.dirname(os.path.abspath(__file__))


class ProfileResponse:
    title: str
    provider: str


class Provider:
    title: str
    logo_path: str

    def __init__(self, title, logo_path):
        self.title = title
        self.logo_path = logo_path

    def get_image(self) -> Gtk.Image:
        full_path = os.path.join(EXTENSION_DIR, self.logo_path)
        print(full_path)

        if os.path.exists(full_path):
            return Gtk.Image.new_from_file(full_path)

        return Gtk.Image.new_from_icon_name(self.logo_path)


google_provider = Provider(
    "Google", "./static/google-drive-logo.png")

yandex_disk_provider = Provider(
    "Yandex", "./static/yandex-disk-logo.png")

next_cloud_provider = Provider(
    "NextCloud", "./static/next-cloud-logo.png")


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

    def __init__(self, title, provider):
        self.title = title
        self.provider = provider


class ColumnExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        print("askdjaslkjkladjklasjdlksajdlkasjdlkasjlkdj")
        pass

    class ProfileResponse:
        title: str
        provider: str

    def get_file_items(self, *args):
        item = Nautilus.MenuItem(
            name='ExampleMenuProvider::CreateFusion',
            label='Добавить удалённое хранилище',
            tip='Демонстрация работы плагина'
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
        print(f"Сижу жду ручку с бека: {text} {provider_title}")
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
            google_provider,
            yandex_disk_provider,
            next_cloud_provider]

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

        delete_button.connect("clicked", self.delete_profile, profile.title)

        icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
        icon.set_pixel_size(24)

        # Добавляем все эти приколы
        row_box.append(label_id)
        row_box.append(provider_vbox)
        row_box.append(delete_button)

        return row_box

    def delete_profile(self, button, profile_title):
        print(f"Жду ручку с бека для удаления: {profile_title}")

    def show_profiles(self):
        # profiles =

        dialog = Gtk.Window(title="Выберите профиль",
                            modal=True, default_width=400)

        # Основной контейнер с отступами
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_box.set_margin_bottom(20)
        dialog.set_child(main_box)

        header = Gtk.Label(label="Доступные профили")
        header.add_css_class("title-4")  # Используем системный стиль заголовка
        main_box.append(header)

        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.set_show_separators(True)  # Рисует линии между строками

        data = [
            Profile("profile1", yandex_disk_provider),
            Profile("profile2", next_cloud_provider),
            Profile("profile3", google_provider)
        ]

        for profile in data:
            row_content = self.create_profile_table_row(profile)

            # В ListBox мы добавляем контент, и он сам оборачивает его в Gtk.ListBoxRow
            list_box.append(row_content)

            # Сохраняем данные для клика
            row_container = row_content.get_parent()
            row_container.row_id = profile.title

        # Чтобы таблица прокручивалась, если строк много
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(300)
        scrolled.set_child(list_box)

        dialog.set_child(scrolled)
        dialog.show()

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

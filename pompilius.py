from gi.repository import Nautilus, GObject, Gtk, Pango
import gi
gi.require_version('Gtk', '4.0')

class ColumnExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        print("askdjaslkjkladjklasjdlksajdlkasjdlkasjlkdj")
        pass

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
                secondary_text="Выберите тип протокола для нового хранилища:"
                )
        dialog.add_button("Создать профиль", 1)
        dialog.add_button("Использовать существующий профиль", 2)
        dialog.add_button("Отмена", Gtk.ResponseType.CANCEL)


        def on_response(d, response_id):
            if response_id == 1:
                self.create_new_profile()
            elif response_id == 2:
                print("Выбран протокол WebDAV")
            
            d.destroy()

        # Подключаем обработчик к сигналу 'response'
        dialog.connect("response", on_response)
        dialog.show()
        print("Пункт меню нажат!")

    def on_company_clicked(self, flowbox, child):
            # child — это Gtk.FlowBoxChild, внутри которого наш Box
            # Извлекаем имя компании из данных, которые мы сохранили в ребенке
            company_name = child.company_id
            print(f"Выбрана компания: {company_name}")
            # Здесь запускай логику подключения к конкретному облаку

    def create_company_widget(self, name, icon_name):
        """Создает маленькую карточку: Логотип + Название снизу"""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_bottom(10)

        # Логотип (системная иконка или путь к файлу)
        image = Gtk.Image.new_from_icon_name(icon_name)
        image.set_pixel_size(48) # Маленький размер логотипа
        
        # Название (caption)
        label = Gtk.Label(label=name)
        label.set_ellipsize(Pango.EllipsizeMode.END) # Обрезать, если слишком длинно
        label.set_max_width_chars(12)

        vbox.append(image)
        vbox.append(label)
        return vbox

    def create_new_profile(self):
        dialog = Gtk.Window(title="Выберите провайдера", modal=True, default_width=400)
        
        # Основной контейнер с отступами
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_box.set_margin_bottom(20)
        dialog.set_child(main_box)

        header = Gtk.Label(label="Доступные хранилища")
        header.add_css_class("title-4") # Используем системный стиль заголовка
        main_box.append(header)

        # Создаем сетку (FlowBox)
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(4) # По 4 логотипа в ряд
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE) # Нам не нужно выделение, только клик
        
        # Список компаний (название, иконка)
        companies = [
            ("Google", "cloud-symbolic"),
            ("Amazon", "network-server-symbolic"),
            ("Dropbox", "folder-remote-symbolic"),
            ("Yandex", "drive-harddisk-symbolic"),
            ("Mail.ru", "mail-send-receive-symbolic"),
            ("Custom", "preferences-system-symbolic")
        ]

        # Наполняем сетку
        for name, icon in companies:
            child_widget = self.create_company_widget(name, icon)
            flowbox.append(child_widget)
            
            # # Сохраняем ID в объекте FlowBoxChild, чтобы знать, на что нажали
            # child_container = flowbox.get_child_at_index(flowbox.get_n_children() - 1)
            # child_container.company_id = name

        # Подключаем событие клика
        flowbox.connect("child-activated", self.on_company_clicked)
        # Если кликнули — закрываем окно (опционально)
        flowbox.connect("child-activated", lambda fb, ch: dialog.destroy())

        main_box.append(flowbox)
        dialog.show()

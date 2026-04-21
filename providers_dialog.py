import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Pango
from pompilius import Provider, AVAILABLE_PROVIDERS, set_margins

class ProvidersDialog(Gtk.Window):
    def __init__(self, parent_extension, transient_for=None):
        super().__init__(title="Выберите провайдера", modal=True, default_width=450, default_height=500, transient_for=transient_for)
        self.parent_ext = parent_extension
        self.filter_text = ""
        
        self.setup_ui()

    def setup_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        set_margins(main_box, 15)
        self.set_child(main_box)

        header = Gtk.Label(label="Доступные хранилища")
        header.add_css_class("title-4")
        main_box.append(header)

        # Строка поиска
        self.search_entry = Gtk.SearchEntry(placeholder_text="Поиск хранилища (Yandex, Google...)...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        main_box.append(self.search_entry)

        # Скролл для сетки
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(4)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_filter_func(self.filter_func)
        
        for p_name in AVAILABLE_PROVIDERS:
            provider = Provider(p_name)
            # Используем метод родителя для создания виджета карточки
            child_widget = self.parent_ext.create_company_widget(provider.title, provider.get_image())
            self.flowbox.append(child_widget)
            
            # Сохраняем технические данные в контейнере (FlowBoxChild)
            child_container = child_widget.get_parent()
            child_container.rclone_title = p_name
            child_container.display_name = provider.title.lower()

        self.flowbox.connect("child-activated", self.on_child_activated)
        
        scrolled.set_child(self.flowbox)
        main_box.append(scrolled)

    def on_search_changed(self, entry):
        self.filter_text = entry.get_text().lower()
        self.flowbox.invalidate_filter()

    def filter_func(self, child):
        if not self.filter_text:
            return True
        return self.filter_text in child.display_name or self.filter_text in child.rclone_title

    def on_child_activated(self, flowbox, child):
        self.parent_ext.on_company_clicked(flowbox, child, self)

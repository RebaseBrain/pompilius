from gi.repository import Nautilus, GObject, Gtk
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
        dialog.add_button("S3 Storage", 1)
        dialog.add_button("WebDAV", 2)
        dialog.add_button("Отмена", Gtk.ResponseType.CANCEL)

        # Обработчик нажатия на кнопки внутри попапа
        def on_response(d, response_id):
            if response_id == 1:
                print("Выбран протокол S3")
                # Здесь вызывай свою логику для S3
            elif response_id == 2:
                print("Выбран протокол WebDAV")
                # Здесь вызывай свою логику для WebDAV
            
            # Закрываем окно
            d.destroy()

        # Подключаем обработчик к сигналу 'response'
        dialog.connect("response", on_response)
        dialog.show()
        print("Пункт меню нажат!")

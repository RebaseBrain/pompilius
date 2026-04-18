from gi.repository import Nautilus, GObject, Gio, GLib
import random
import os
from urllib.parse import unquote, urlparse


class PompiliusIconOverlay(GObject.GObject, Nautilus.InfoProvider):
    def __init__(self):
        super().__init__()
        self.active_files = {}

        GLib.timeout_add(3000, self.refresh_all)

    def is_cached(self, file_path):
        return random.randint(0, 1)

    def refresh_all(self):
        """Принудительно заставляет Nautilus переспросить статус для всех видимых файлов"""
        for uri, file_info in list(self.active_files.items()):
            try:
                file_info.invalidate_extension_info()
            except:
                self.active_files.pop(uri, None)
        return True

    def update_file_info(self, file_info):
        """Вызывается Nautilus при создании/обновлении инфо о файле"""
        uri = file_info.get_uri()

        self.active_files[uri] = file_info

        if file_info.is_directory():
            return

        file_path = unquote(urlparse(uri).path)

        if self.is_cached(file_path):
            icon_name = "document-save"
        else:
            icon_name = "network-wireless"

        file_info.add_string_attribute('overlay_icons', icon_name)
        file_info.add_emblem(icon_name)

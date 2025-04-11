import gi
import sqlite3
import os

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

DB_PATH = os.path.join(os.path.dirname(__file__), "cache", "overlay_translator_cache.sqlite")
TRANSLATOR_OPTIONS = ["Ollama", "Google"]

class TranslatorApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Overlay Translator")
        self.set_default_size(400, 220)
        self.set_border_width(10)

        self.window_id = None
        self.init_db()

        # UI Elements
        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        self.add(grid)

        self.select_window_btn = Gtk.Button(label="Выбрать окно")
        self.select_window_btn.connect("clicked", self.on_select_window)

        self.update_btn = Gtk.Button(label="Обновить перевод")
        self.update_btn.connect("clicked", self.on_manual_update)

        self.clear_cache_btn = Gtk.Button(label="Сбросить кэш")
        self.clear_cache_btn.connect("clicked", self.on_clear_cache)

        adjustment = Gtk.Adjustment(value=2, lower=1, upper=60, step_increment=1, page_increment=5, page_size=0)
        self.interval_spin = Gtk.SpinButton(adjustment=adjustment)
        self.interval_spin.set_numeric(True)

        self.translator_combo = Gtk.ComboBoxText()
        for t in TRANSLATOR_OPTIONS:
            self.translator_combo.append_text(t)
        self.translator_combo.set_active(0)

        self.status_label = Gtk.Label(label="Ожидание...")
        self.window_label = Gtk.Label(label="Окно не выбрано")

        # Layout
        grid.attach(self.select_window_btn, 0, 0, 1, 1)
        grid.attach(self.update_btn, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Интервал (сек):"), 0, 1, 1, 1)
        grid.attach(self.interval_spin, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="Переводчик:"), 0, 2, 1, 1)
        grid.attach(self.translator_combo, 1, 2, 1, 1)
        grid.attach(self.clear_cache_btn, 0, 3, 2, 1)
        grid.attach(self.window_label, 0, 4, 2, 1)
        grid.attach(self.status_label, 0, 5, 2, 1)

        # Periodic update
        GLib.timeout_add_seconds(2, self.periodic_update)

    def init_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS translations (
                           id INTEGER PRIMARY KEY,
                           source_text TEXT UNIQUE,
                           translated_text TEXT,
                           last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       )''')
        self.conn.commit()

    def on_select_window(self, button):
        self.status_label.set_text("Выбор окна: кликните на окно...")
        os.system("xdotool selectwindow > /tmp/selected_window_id")
        with open("/tmp/selected_window_id") as f:
            self.window_id = f.read().strip()
        self.status_label.set_text("Окно выбрано")
        self.window_label.set_text(f"ID окна: {self.window_id}")

    def on_manual_update(self, button):
        self.status_label.set_text("Обновление перевода...")
        # TODO: Implement full OCR + translate + overlay flow
        self.status_label.set_text("Перевод обновлён (заглушка)")

    def on_clear_cache(self, button):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM translations")
        self.conn.commit()
        self.status_label.set_text("Кэш очищен")

    def periodic_update(self):
        interval = self.interval_spin.get_value_as_int()
        GLib.timeout_add_seconds(interval, self.periodic_update)
        # TODO: Only run if a window is selected
        # self.status_label.set_text("Автообновление (заглушка)")
        return False  # Because we re-add the timeout each time

win = TranslatorApp()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()

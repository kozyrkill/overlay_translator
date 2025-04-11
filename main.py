import gi
import sqlite3
import os
import subprocess
import requests
import pytesseract
import threading
import html
from PIL import Image

# Указываем версию Gtk до импорта
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

DB_PATH = os.path.join(os.path.dirname(__file__), "cache", "overlay_translator_cache.sqlite")
TRANSLATOR_OPTIONS = ["Ollama", "Google"]

class TranslatorApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Overlay Translator")
        self.set_default_size(400, 240)
        self.set_border_width(10)

        self.window_id = None
        self.window_title = None
        self.overlay_window = None
        self.translation_enabled = True
        self.init_db()

        # UI Elements
        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        self.add(grid)

        self.select_window_btn = Gtk.Button(label="Выбрать окно")
        self.select_window_btn.connect("clicked", self.on_select_window)

        self.update_btn = Gtk.Button(label="Обновить перевод")
        self.update_btn.connect("clicked", self.on_manual_update)

        self.start_btn = Gtk.Button(label="Старт")
        self.start_btn.connect("clicked", self.on_start)

        self.stop_btn = Gtk.Button(label="Стоп")
        self.stop_btn.connect("clicked", self.on_stop)

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
        grid.attach(self.start_btn, 0, 1, 1, 1)
        grid.attach(self.stop_btn, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="Интервал (сек):"), 0, 2, 1, 1)
        grid.attach(self.interval_spin, 1, 2, 1, 1)
        grid.attach(Gtk.Label(label="Переводчик:"), 0, 3, 1, 1)
        grid.attach(self.translator_combo, 1, 3, 1, 1)
        grid.attach(self.clear_cache_btn, 0, 4, 2, 1)
        grid.attach(self.window_label, 0, 5, 2, 1)
        grid.attach(self.status_label, 0, 6, 2, 1)

        # Periodic update
        GLib.timeout_add_seconds(2, self.periodic_update)

    def init_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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

        try:
            output = subprocess.check_output(["xprop", "-id", self.window_id, "WM_NAME"], text=True)
            self.window_title = output.strip().split('=')[1].strip().strip('"')
        except Exception as e:
            self.window_title = f"Не удалось получить заголовок: {e}"

        self.status_label.set_text("Окно выбрано")
        self.window_label.set_text(f"Окно: {self.window_title}")

    def on_manual_update(self, button):
        thread = threading.Thread(target=self.perform_translation, daemon=True)
        thread.start()

    def perform_translation(self):
        GLib.idle_add(self.status_label.set_text, "Захват изображения и OCR...")
        image_path = "/tmp/window_capture.png"
        try:
            subprocess.run(["import", "-window", self.window_id, image_path], check=True)
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang='rus+eng')
            GLib.idle_add(self.status_label.set_text, "Текст распознан, перевод...")
            translated = self.translate_text(text.strip())
            short_text = translated[:60] + ("..." if len(translated) > 60 else "")
            GLib.idle_add(self.status_label.set_text, "Перевод: " + short_text)
            GLib.idle_add(self.show_overlay, translated)
        except Exception as e:
            print("[Ошибка OCR]:", e)
            GLib.idle_add(self.status_label.set_text, f"Ошибка OCR: {e}")

    def show_overlay(self, text):
        if self.overlay_window:
            self.overlay_window.destroy()

        self.overlay_window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.overlay_window.set_decorated(False)
        self.overlay_window.set_app_paintable(True)
        screen = Gdk.Screen.get_default()
        rgba = screen.get_rgba_visual()
        self.overlay_window.set_visual(rgba)

        label = Gtk.Label()
        safe_text = html.escape(text)
        label.set_markup(f'<span foreground="white" font_desc="18">{safe_text}</span>')
        self.overlay_window.add(label)

        self.overlay_window.set_default_size(800, 200)
        self.overlay_window.move(100, 100)
        self.overlay_window.show_all()

    def translate_text(self, text):
        if not text:
            return ""
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT translated_text FROM translations WHERE source_text = ?", (text,))
            row = cur.fetchone()
            if row:
                return row[0]

            translator = self.translator_combo.get_active_text()
            translated = ""
            if translator == "Ollama":
                r = requests.post("http://localhost:11434/api/generate", json={
                    "model": "llama3",
                    "prompt": f"Translate to Russian: {text}"
                })
                translated = r.json().get("response", "")
            elif translator == "Google":
                from googletrans import Translator
                tr = Translator()
                translated = tr.translate(text, dest='ru').text

            cur.execute("INSERT OR REPLACE INTO translations (source_text, translated_text) VALUES (?, ?)", (text, translated))
            self.conn.commit()
            return translated
        except Exception as e:
            print("[Ошибка перевода]:", e)
            return f"[Ошибка перевода: {e}]"

    def on_clear_cache(self, button):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM translations")
        self.conn.commit()
        self.status_label.set_text("Кэш очищен")

    def on_start(self, button):
        self.translation_enabled = True
        self.status_label.set_text("Автоперевод включен")

    def on_stop(self, button):
        self.translation_enabled = False
        self.status_label.set_text("Автоперевод остановлен")

    def periodic_update(self):
        if self.window_id and self.translation_enabled:
            thread = threading.Thread(target=self.perform_translation, daemon=True)
            thread.start()
        interval = self.interval_spin.get_value_as_int()
        GLib.timeout_add_seconds(interval, self.periodic_update)
        return False

win = TranslatorApp()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()

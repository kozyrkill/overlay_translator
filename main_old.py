"""
Overlay Translator - Утилита для автоматического перевода текста с экрана

Особенности:
- Два режима работы: компактный и расширенный
- Автоматический захват окон и OCR
- Перевод через Ollama или Google Translate
- Overlay отображение результатов
- Кэширование переводов

Автор: Объединенная версия main.py + translator_engine.py
"""

import gi
import os
import subprocess
import threading
import signal
import sys

# Указываем версию Gtk до импорта
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

# Импортируем наши модули
from ocr_engine import OCREngine
from translation_engine import TranslationEngine
from overlay_manager import OverlayManager

DB_PATH = os.path.join(os.path.dirname(__file__), "cache", "overlay_translator_cache.sqlite")
TRANSLATOR_OPTIONS = ["Ollama", "Google"]

class TranslatorApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Overlay Translator")
        self.set_default_size(450, 700)  # Увеличиваем размер для комфортного отображения
        self.set_border_width(10)
        self.set_resizable(True)  # Разрешаем изменение размера

        self.window_id = None
        self.window_title = None
        self.translation_enabled = True
        self.compact_mode = False  # Флаг для компактного режима
        
        # Инициализируем модули
        self.ocr_engine = OCREngine()
        self.translation_engine = TranslationEngine(DB_PATH)
        self.overlay_manager = OverlayManager()
        
        # Устанавливаем начальную прозрачность
        self.overlay_manager.set_opacity(80)

        # UI Elements
        grid = Gtk.Grid(column_spacing=10, row_spacing=10)

        self.select_window_btn = Gtk.Button(label="Выбрать окно")
        self.select_window_btn.connect("clicked", self.on_select_window)
        self.select_window_btn.set_size_request(150, 35)

        self.update_btn = Gtk.Button(label="Обновить перевод")
        self.update_btn.connect("clicked", self.on_manual_update)
        self.update_btn.set_size_request(150, 35)

        self.start_btn = Gtk.Button(label="Старт")
        self.start_btn.connect("clicked", self.on_start)
        self.start_btn.set_size_request(150, 35)

        self.stop_btn = Gtk.Button(label="Стоп")
        self.stop_btn.connect("clicked", self.on_stop)
        self.stop_btn.set_size_request(150, 35)

        self.clear_cache_btn = Gtk.Button(label="Сбросить кэш")
        self.clear_cache_btn.connect("clicked", self.on_clear_cache)
        self.clear_cache_btn.set_size_request(320, 35)

        # Переключатель режимов
        self.compact_checkbox = Gtk.CheckButton(label="Компактный вид")
        self.compact_checkbox.connect("toggled", self.on_toggle_compact_mode)
        
        # Настройка прозрачности overlay
        self.opacity_label = Gtk.Label(label="Прозрачность overlay:")
        opacity_adjustment = Gtk.Adjustment(value=80, lower=10, upper=100, step_increment=10, page_increment=20, page_size=0)
        self.opacity_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=opacity_adjustment)
        self.opacity_scale.set_digits(0)
        self.opacity_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self.opacity_scale.connect("value-changed", self.on_opacity_changed)

        adjustment = Gtk.Adjustment(value=2, lower=1, upper=60, step_increment=1, page_increment=5, page_size=0)
        self.interval_spin = Gtk.SpinButton(adjustment=adjustment)
        self.interval_spin.set_numeric(True)

        self.translator_combo = Gtk.ComboBoxText()
        for t in TRANSLATOR_OPTIONS:
            self.translator_combo.append_text(t)
        self.translator_combo.set_active(1)  # Google Translate по умолчанию

        self.status_label = Gtk.Label(label="Ожидание...")
        self.window_label = Gtk.Label(label="Окно не выбрано")

        # Дополнительные элементы для расширенного режима
        self.ocr_buffer = Gtk.TextBuffer()
        self.translation_buffer = Gtk.TextBuffer()

        ocr_view = Gtk.TextView(buffer=self.ocr_buffer)
        ocr_view.set_editable(False)
        ocr_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.ocr_scroll = Gtk.ScrolledWindow()
        self.ocr_scroll.set_min_content_height(150)
        self.ocr_scroll.set_min_content_width(450)
        self.ocr_scroll.add(ocr_view)

        translation_view = Gtk.TextView(buffer=self.translation_buffer)
        translation_view.set_editable(False)
        translation_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.translation_scroll = Gtk.ScrolledWindow()
        self.translation_scroll.set_min_content_height(150)
        self.translation_scroll.set_min_content_width(450)
        self.translation_scroll.add(translation_view)

        # Layout с улучшенным расположением
        grid.attach(self.select_window_btn, 0, 0, 1, 1)
        grid.attach(self.update_btn, 1, 0, 1, 1)
        grid.attach(self.start_btn, 0, 1, 1, 1)
        grid.attach(self.stop_btn, 1, 1, 1, 1)
        
        # Настройки
        grid.attach(Gtk.Label(label="Интервал (сек):"), 0, 2, 1, 1)
        grid.attach(self.interval_spin, 1, 2, 1, 1)
        grid.attach(Gtk.Label(label="Переводчик:"), 0, 3, 1, 1)
        grid.attach(self.translator_combo, 1, 3, 1, 1)
        
        # Переключатель режимов
        grid.attach(self.compact_checkbox, 0, 4, 2, 1)
        
        # Настройка прозрачности
        grid.attach(self.opacity_label, 0, 5, 2, 1)
        grid.attach(self.opacity_scale, 0, 6, 2, 1)
        
        # Кнопка очистки кэша
        grid.attach(self.clear_cache_btn, 0, 7, 2, 1)
        
        # Информация
        grid.attach(self.window_label, 0, 8, 2, 1)
        grid.attach(self.status_label, 0, 9, 2, 1)
        
        # Элементы расширенного режима (изначально скрыты)
        self.ocr_label = Gtk.Label(label="Распознанный текст:")
        self.translation_label = Gtk.Label(label="Перевод:")
        
        grid.attach(self.ocr_label, 0, 10, 2, 1)
        grid.attach(self.ocr_scroll, 0, 11, 2, 1)
        grid.attach(self.translation_label, 0, 12, 2, 1)
        grid.attach(self.translation_scroll, 0, 13, 2, 1)

        # Прокручиваемый контейнер
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.add(grid)

        # Добавляем scroller в окно
        self.add(scroller)

        # Изначально скрываем расширенные элементы
        self.toggle_advanced_elements(False)

        # Periodic update
        GLib.timeout_add_seconds(2, self.periodic_update)
        
        # Добавляем обработчик событий для лучшей отзывчивости
        self.connect("key-press-event", self.on_key_press)
        self.connect("button-press-event", self.on_button_press)

    def toggle_advanced_elements(self, show):
        """Показывает или скрывает элементы расширенного режима"""
        self.ocr_label.set_visible(show)
        self.ocr_scroll.set_visible(show)
        self.translation_label.set_visible(show)
        self.translation_scroll.set_visible(show)
        
        # Изменяем размер окна и принудительно обновляем
        if show:
            self.resize(500, 900)  # Увеличиваем размер для расширенного режима
        else:
            self.resize(500, 600)  # Увеличиваем размер для компактного режима
        
        # Принудительно обновляем layout
        self.queue_resize()
        # Обновляем все виджеты
        self.show_all()

    def on_toggle_compact_mode(self, button):
        """Обработчик переключения режима"""
        self.compact_mode = button.get_active()
        self.toggle_advanced_elements(not self.compact_mode)

    def on_opacity_changed(self, scale):
        """Обработчик изменения прозрачности overlay"""
        opacity = scale.get_value()
        self.overlay_manager.set_opacity(int(opacity))

    def init_db(self):
        """Инициализирует базу данных (устаревший метод)"""
        pass  # База данных теперь инициализируется в TranslationEngine

    def on_select_window(self, button):
        self.status_label.set_text("Выбор окна: кликните на окно...")
        try:
            # Используем subprocess вместо os.system для лучшего контроля
            result = subprocess.run(["xdotool", "selectwindow"], 
                                  capture_output=True, text=True, check=True)
            self.window_id = result.stdout.strip()
            
            if not self.window_id:
                self.status_label.set_text("Ошибка: не удалось получить ID окна")
                return

            try:
                output = subprocess.check_output(["xprop", "-id", self.window_id, "WM_NAME"], text=True)
                self.window_title = output.strip().split('=')[1].strip().strip('"')
            except Exception as e:
                self.window_title = f"Не удалось получить заголовок: {e}"

            self.status_label.set_text("Окно выбрано")
            self.window_label.set_text(f"Окно: {self.window_title}")
        except subprocess.CalledProcessError as e:
            self.status_label.set_text(f"Ошибка выбора окна: {e}")
        except Exception as e:
            self.status_label.set_text(f"Неожиданная ошибка: {e}")

    def on_manual_update(self, button):
        thread = threading.Thread(target=self.perform_translation, daemon=True)
        thread.start()

    def perform_translation(self):
        if not self.window_id:
            GLib.idle_add(self.status_label.set_text, "Окно не выбрано")
            return

        print(f"[DEBUG] Начинаем перевод для окна: {self.window_id}")
        GLib.idle_add(self.status_label.set_text, "Захват изображения и OCR...")
        
        try:
            # Захватываем изображение окна
            if not self.ocr_engine.capture_window(self.window_id):
                GLib.idle_add(self.status_label.set_text, "Ошибка захвата окна")
                return
            
            # Распознаем текст
            text = self.ocr_engine.recognize_text()
            if not text:
                GLib.idle_add(self.status_label.set_text, "Текст не распознан")
                return
                
            GLib.idle_add(self.status_label.set_text, "Текст распознан, перевод...")
            
            # Разбиваем текст на предложения для лучшего перевода
            sentences = self.translation_engine.split_into_sentences(text)
            print(f"[DEBUG] OCR распознал {len(sentences)} предложений")
            
            # Переводим каждое предложение отдельно
            translated_parts = []
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    translator = self.translator_combo.get_active_text()
                    translated_part = self.translation_engine.translate_text(sentence.strip(), translator)
                    translated_parts.append(translated_part)
                    print(f"[DEBUG] Предложение {i+1}: '{sentence}' -> '{translated_part}'")
            
            # Объединяем переводы
            translated = '\n'.join(translated_parts)
            short_text = translated[:60] + ("..." if len(translated) > 60 else "")
            GLib.idle_add(self.status_label.set_text, "Перевод: " + short_text)
            
            # Обновляем буферы только в расширенном режиме
            if not self.compact_mode:
                GLib.idle_add(self.ocr_buffer.set_text, text)
                GLib.idle_add(self.translation_buffer.set_text, translated)
            
            # Показываем overlay
            x, y, w, h = self.ocr_engine.get_window_geometry(self.window_id)
            GLib.idle_add(self.overlay_manager.show_overlay, translated, x, y, w, h, self.compact_mode)
            
            # Очищаем временные файлы
            self.ocr_engine.cleanup()
            
        except Exception as e:
            print("[Ошибка OCR]:", e)
            GLib.idle_add(self.status_label.set_text, f"Ошибка OCR: {e}")
            
            # Очищаем временный файл в случае ошибки
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
            except:
                pass

    def get_window_geometry(self):
        """
        Считываем xwininfo, чтобы узнать координаты верхнего левого угла и размер окна.
        Возвращаем (x, y, width, height). В случае ошибки — дефолтные значения.
        """
        if not self.window_id:
            return (100, 100, 800, 200)
        try:
            output = subprocess.check_output(["xwininfo", "-id", self.window_id], text=True)
            # Пример выходных данных:
            # xwininfo: Window id: 0x3c00007 "Название"
            #   Absolute upper-left X:  200
            #   Absolute upper-left Y:  300
            #   Width:  640
            #   Height: 480
            x_match = re.search(r'Absolute upper-left X:\s+(\d+)', output)
            y_match = re.search(r'Absolute upper-left Y:\s+(\d+)', output)
            w_match = re.search(r'Width:\s+(\d+)', output)
            h_match = re.search(r'Height:\s+(\d+)', output)
            x = int(x_match.group(1)) if x_match else 100
            y = int(y_match.group(1)) if y_match else 100
            w = int(w_match.group(1)) if w_match else 800
            h = int(h_match.group(1)) if h_match else 200
            
            # Добавляем небольшое смещение для лучшей видимости
            x += 10
            y += 10
            w = max(w - 20, 400)  # Минимальная ширина 400
            h = max(h - 20, 100)  # Минимальная высота 100
            
            return (x, y, w, h)
        except:
            return (100, 100, 800, 200)

    def show_overlay(self, text):
        """
        Показываем всплывающее окно (popup), позиционируем поверх исходного окна,
        делаем фон прозрачным и выводим перевод белым текстом сверху.
        """
        if self.overlay_window:
            self.overlay_window.destroy()

        if self.compact_mode:
            # Простой overlay для компактного режима
            self.overlay_window = Gtk.Window(type=Gtk.WindowType.POPUP)
            self.overlay_window.set_decorated(False)
            self.overlay_window.set_app_paintable(True)
            self.overlay_window.set_accept_focus(False)  # Не принимает фокус
            self.overlay_window.set_keep_above(True)     # Поверх всех окон
            
            # Делаем окно прозрачным для кликов
            screen = Gdk.Screen.get_default()
            rgba = screen.get_rgba_visual()
            if rgba:
                self.overlay_window.set_visual(rgba)

            # Создаем overlay для прозрачности кликов
            overlay = Gtk.Overlay()
            self.overlay_window.add(overlay)
            
            # Фон полностью прозрачный
            background = Gtk.EventBox()
            try:
                background.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
            except:
                pass
            overlay.add(background)

            label = Gtk.Label()
            safe_text = html.escape(text)
            label.set_markup(f'<span foreground="white" font_desc="18" background="rgba(0,0,0,0.7)">{safe_text}</span>')
            overlay.add_overlay(label)
            
            # Клики проходят сквозь overlay
            overlay.set_overlay_pass_through(label, True)
            overlay.set_overlay_pass_through(background, True)

            # Устанавливаем прозрачность всего окна
            self.overlay_window.set_opacity(self.overlay_opacity)

            # ВАЖНО: Делаем окно полностью прозрачным для событий
            self.overlay_window.set_events(Gdk.EventMask(0))  # Отключаем все события

            self.overlay_window.set_default_size(800, 200)
            self.overlay_window.move(100, 100)
        else:
            # Улучшенный overlay для расширенного режима
            x, y, width, height = self.get_window_geometry()

            # Создаём popup-окно без декораций
            self.overlay_window = Gtk.Window(type=Gtk.WindowType.POPUP)
            self.overlay_window.set_decorated(False)
            self.overlay_window.set_accept_focus(False)
            self.overlay_window.set_keep_above(True)
            self.overlay_window.set_app_paintable(True)

            screen = Gdk.Screen.get_default()
            rgba_visual = screen.get_rgba_visual()
            if rgba_visual:
                self.overlay_window.set_visual(rgba_visual)

            # Устанавливаем координаты и размер, совпадающие с исходным окном
            self.overlay_window.set_default_size(width, height)
            self.overlay_window.move(x, y)

            # Используем Gtk.Overlay для накладки текста
            overlay = Gtk.Overlay()
            self.overlay_window.add(overlay)

            # Фон делаем прозрачным
            background = Gtk.EventBox()
            # Используем современный способ установки прозрачности
            try:
                # Для старых версий GTK
                background.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
            except:
                # Для новых версий GTK - используем CSS
                try:
                    css_provider = Gtk.CssProvider()
                    css_provider.load_from_data(b"* { background-color: transparent; }")
                    screen = Gdk.Screen.get_default()
                    style_context = background.get_style_context()
                    style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                except:
                    pass
            overlay.add(background)

            # Добавляем лейбл поверх
            label = Gtk.Label()
            safe_text = html.escape(text)
            label.set_markup(f'<span foreground="white" font_desc="18">{safe_text}</span>')
            overlay.add_overlay(label)

            # Чтобы клики проходили сквозь лейбл и фон
            overlay.set_overlay_pass_through(label, True)
            overlay.set_overlay_pass_through(background, True)
            
            # Устанавливаем прозрачность всего окна
            self.overlay_window.set_opacity(self.overlay_opacity)
            
            # ВАЖНО: Делаем окно полностью прозрачным для событий
            self.overlay_window.set_events(Gdk.EventMask(0))  # Отключаем все события

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
                try:
                    r = requests.post("http://localhost:11434/api/generate", 
                                    json={"model": "llama3", "prompt": f"Translate to Russian: {text}"},
                                    timeout=5)
                    translated = r.json().get("response", "")
                except requests.exceptions.ConnectionError:
                    translated = "[Ошибка: Ollama сервер недоступен. Запустите 'ollama serve' или выберите Google Translate]"
                except Exception as e:
                    translated = f"[Ошибка Ollama: {e}]"
            elif translator == "Google":
                try:
                    # Используем более надежную библиотеку для Google Translate
                    import requests
                    url = "https://translate.googleapis.com/translate_a/single"
                    params = {
                        'client': 'gtx',
                        'sl': 'auto',
                        'tl': 'ru',
                        'dt': 't',
                        'q': text
                    }
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        translated = ''.join([part[0] for part in data[0] if part[0]])
                        print(f"[DEBUG] Google Translate: '{text}' -> '{translated}'")
                    else:
                        translated = f"[Ошибка Google Translate: HTTP {response.status_code}]"
                        print(f"[DEBUG] Google Translate error: {response.status_code}")
                except Exception as e:
                    translated = f"[Ошибка Google Translate: {e}]"
                    print(f"[DEBUG] Google Translate exception: {e}")

            cur.execute("INSERT OR REPLACE INTO translations (source_text, translated_text) VALUES (?, ?)", (text, translated))
            self.conn.commit()
            return translated
        except Exception as e:
            print("[Ошибка перевода]:", e)
            return f"[Ошибка перевода: {e}]"

    def on_clear_cache(self, button):
        self.translation_engine.clear_cache()
        self.status_label.set_text("Кэш очищен")

    def on_start(self, button):
        self.translation_enabled = True
        self.status_label.set_text("Автоперевод включен")

    def on_stop(self, button):
        self.translation_enabled = False
        self.status_label.set_text("Автоперевод остановлен")

    def periodic_update(self):
        if self.window_id and self.translation_enabled:
            # Проверяем, что окно все еще существует
            try:
                subprocess.run(["xprop", "-id", self.window_id, "WM_NAME"], 
                             capture_output=True, check=True, timeout=2)
                # Используем GLib.idle_add для безопасного запуска в главном потоке
                GLib.idle_add(self.safe_perform_translation)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                # Окно больше не существует или недоступно
                self.window_id = None
                self.window_title = None
                GLib.idle_add(self.window_label.set_text, "Окно не выбрано")
                GLib.idle_add(self.status_label.set_text, "Выбранное окно закрыто")
        
        interval = self.interval_spin.get_value_as_int()
        GLib.timeout_add_seconds(interval, self.periodic_update)
        return False

    def safe_perform_translation(self):
        """Безопасный запуск перевода в отдельном потоке"""
        thread = threading.Thread(target=self.perform_translation, daemon=True)
        thread.start()
        return False



    def on_key_press(self, widget, event):
        """Обработчик нажатий клавиш"""
        # Ctrl+Q для выхода
        if event.state & Gdk.ModifierType.CONTROL_MASK and event.keyval == ord('q'):
            Gtk.main_quit()
            return True
        # Escape для выхода
        elif event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
            return True
        return False

    def on_button_press(self, widget, event):
        """Обработчик кликов мыши"""
        # Обрабатываем клики для лучшей отзывчивости
        return False

def signal_handler(sig, frame):
    """Обработчик сигналов для корректного завершения"""
    print("\nПолучен сигнал завершения, закрываю приложение...")
    Gtk.main_quit()
    sys.exit(0)

# Устанавливаем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

win = TranslatorApp()
win.connect("destroy", Gtk.main_quit)
win.connect("delete-event", Gtk.main_quit)  # Обработка закрытия окна
win.connect("window-state-event", lambda w, e: None)  # Обработка изменения состояния окна
win.show_all()
Gtk.main()

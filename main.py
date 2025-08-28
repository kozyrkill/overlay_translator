#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Overlay Translator - Утилита для автоматического перевода текста с экрана

Особенности:
- Два режима работы: компактный и расширенный
- Автоматический захват окон и OCR
- Перевод через Ollama или Google Translate
- Overlay отображение результатов
- Кэширование переводов

Автор: Модульная версия с разделением на классы
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
        self.set_default_size(500, 800)  # Увеличиваем размер для комфортного отображения
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

        # Кнопки управления overlay для скриншотов
        self.hide_overlay_btn = Gtk.Button(label="Скрыть overlay")
        self.hide_overlay_btn.connect("clicked", self.on_hide_overlay)
        self.hide_overlay_btn.set_size_request(150, 35)
        
        self.show_overlay_btn = Gtk.Button(label="Показать overlay")
        self.show_overlay_btn.connect("clicked", self.on_show_overlay)
        self.show_overlay_btn.set_size_request(150, 35)

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

        # Создаем текстовые виджеты с прокруткой
        self.ocr_scroll = Gtk.ScrolledWindow()
        self.ocr_scroll.set_size_request(450, 150)
        self.ocr_scroll.set_min_content_width(450)
        self.ocr_scroll.set_min_content_height(150)

        self.translation_scroll = Gtk.ScrolledWindow()
        self.translation_scroll.set_size_request(450, 150)
        self.translation_scroll.set_min_content_width(450)
        self.translation_scroll.set_min_content_height(150)

        # Создаем текстовые виджеты
        ocr_text_view = Gtk.TextView(buffer=self.ocr_buffer)
        ocr_text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        ocr_text_view.set_editable(False)
        self.ocr_scroll.add(ocr_text_view)

        translation_text_view = Gtk.TextView(buffer=self.translation_buffer)
        translation_text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        translation_text_view.set_editable(False)
        self.translation_scroll.add(translation_text_view)

        # Размещаем элементы в сетке
        grid.attach(self.select_window_btn, 0, 0, 1, 1)
        grid.attach(self.update_btn, 1, 0, 1, 1)
        grid.attach(self.start_btn, 0, 1, 1, 1)
        grid.attach(self.stop_btn, 1, 1, 1, 1)

        # Интервал
        interval_label = Gtk.Label(label="Интервал (сек):")
        grid.attach(interval_label, 0, 2, 1, 1)
        grid.attach(self.interval_spin, 1, 2, 1, 1)

        # Переводчик
        translator_label = Gtk.Label(label="Переводчик:")
        grid.attach(translator_label, 0, 3, 1, 1)
        grid.attach(self.translator_combo, 1, 3, 1, 1)

        # Компактный вид
        grid.attach(self.compact_checkbox, 0, 4, 2, 1)

        # Прозрачность
        grid.attach(self.opacity_label, 0, 5, 1, 1)
        grid.attach(self.opacity_scale, 1, 5, 1, 1)

        # Кнопка очистки кэша
        grid.attach(self.clear_cache_btn, 0, 6, 2, 1)

        # Кнопки управления overlay
        grid.attach(self.hide_overlay_btn, 0, 7, 1, 1)
        grid.attach(self.show_overlay_btn, 1, 7, 1, 1)
        
        # Кнопка автоматического скриншота
        self.screenshot_btn = Gtk.Button(label="Скриншот без overlay")
        self.screenshot_btn.connect("clicked", self.on_screenshot)
        self.screenshot_btn.set_size_request(320, 35)
        grid.attach(self.screenshot_btn, 0, 8, 2, 1)

        # Информация об окне
        grid.attach(self.window_label, 0, 9, 2, 1)
        grid.attach(self.status_label, 0, 10, 2, 1)

        # Элементы расширенного режима
        ocr_label = Gtk.Label(label="Распознанный текст:")
        grid.attach(ocr_label, 0, 11, 2, 1)
        grid.attach(self.ocr_scroll, 0, 12, 2, 1)

        translation_label = Gtk.Label(label="Перевод:")
        grid.attach(translation_label, 0, 13, 2, 1)
        grid.attach(self.translation_scroll, 0, 14, 2, 1)

        self.add(grid)

        # Обработчики событий
        self.connect("delete-event", Gtk.main_quit)
        self.connect("key-press-event", self.on_key_press)
        self.connect("button-press-event", self.on_button_press)

        # Обработчики сигналов для корректного завершения
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Запускаем периодическое обновление
        self.periodic_update()

        # Показываем все элементы
        self.show_all()
        
        # Инициализируем состояние кнопок overlay
        self.show_overlay_btn.set_sensitive(False)  # Изначально overlay видны

    def on_toggle_compact_mode(self, checkbox):
        """Обработчик переключения компактного режима"""
        self.compact_mode = checkbox.get_active()
        self.toggle_advanced_elements(not self.compact_mode)

    def toggle_advanced_elements(self, show):
        """Показывает/скрывает элементы расширенного режима"""
        self.ocr_scroll.set_visible(show)
        self.translation_scroll.set_visible(show)
        
        # Изменяем размер окна
        if show:
            self.resize(500, 900)
        else:
            self.resize(500, 600)
        
        self.queue_resize()
        self.show_all()

    def on_opacity_changed(self, scale):
        """Обработчик изменения прозрачности overlay"""
        opacity = scale.get_value()
        self.overlay_manager.set_opacity(int(opacity))

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
        # Принудительно очищаем кэш при ручном обновлении
        self.ocr_engine.clear_cache()
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
            
            # Проверяем, изменилось ли изображение (порог 5% изменений)
            cached_translated_blocks = self.ocr_engine.get_cached_translated_blocks()
            
            if cached_translated_blocks:
                # Используем кэшированные переводы
                print("[DEBUG] Используем кэшированные переводы")
                translated_blocks = cached_translated_blocks
                text_blocks = self.ocr_engine.last_ocr_result
                GLib.idle_add(self.status_label.set_text, f"Используем кэш: {len(translated_blocks)} блоков")
            else:
                # Распознаем текст с координатами
                text_blocks = self.ocr_engine.recognize_text_with_positions()
                if not text_blocks:
                    GLib.idle_add(self.status_label.set_text, "Текст не распознан")
                    return
                    
                GLib.idle_add(self.status_label.set_text, f"Распознано {len(text_blocks)} блоков, перевод...")
                
                # Переводим каждый текстовый блок
                translator = self.translator_combo.get_active_text()
                translated_blocks = self.translation_engine.translate_text_blocks(text_blocks, translator)
                
                if not translated_blocks:
                    GLib.idle_add(self.status_label.set_text, "Ошибка перевода")
                    return
                
                # Кэшируем результат
                self.ocr_engine.cache_translated_blocks(translated_blocks)
                
                # Обновляем статус
                short_text = f"Переведено {len(translated_blocks)} блоков"
                GLib.idle_add(self.status_label.set_text, short_text)
                
                # Обновляем буферы только в расширенном режиме
                if not self.compact_mode:
                    # Показываем оригинальный текст
                    original_text = '\n'.join([block['text'] for block in text_blocks])
                    translated_text = '\n'.join([block.get('translated_text', '') for block in translated_blocks])
                    GLib.idle_add(self.ocr_buffer.set_text, original_text)
                    GLib.idle_add(self.translation_buffer.set_text, translated_text)
            
            # Показываем множественные overlay (в любом случае)
            x, y, w, h = self.ocr_engine.get_window_geometry(self.window_id)
            GLib.idle_add(self.overlay_manager.show_multiple_overlays, translated_blocks, x, y, self.compact_mode)
            
            # Очищаем временные файлы
            self.ocr_engine.cleanup()
            
        except Exception as e:
            print("[Ошибка OCR]:", e)
            GLib.idle_add(self.status_label.set_text, f"Ошибка OCR: {e}")

    def on_clear_cache(self, button):
        self.translation_engine.clear_cache()
        self.status_label.set_text("Кэш очищен")

    def on_hide_overlay(self, button):
        """Скрывает overlay окна для создания скриншота"""
        self.overlay_manager.hide_for_screenshot()
        self.status_label.set_text("Overlay скрыты для скриншота")
        self.hide_overlay_btn.set_sensitive(False)
        self.show_overlay_btn.set_sensitive(True)

    def on_show_overlay(self, button):
        """Восстанавливает overlay окна после создания скриншота"""
        self.overlay_manager.restore_after_screenshot()
        self.status_label.set_text("Overlay восстановлены")
        self.hide_overlay_btn.set_sensitive(True)
        self.show_overlay_btn.set_sensitive(False)

    def on_screenshot(self, button):
        """Создает скриншот без overlay надписей"""
        self.status_label.set_text("Создание скриншота без overlay...")
        
        # Скрываем overlay с автоматическим восстановлением через 5 секунд
        self.overlay_manager.hide_for_screenshot_with_delay(5)
        
        # Временно блокируем кнопку
        self.screenshot_btn.set_sensitive(False)
        
        # Восстанавливаем кнопку через 6 секунд
        GLib.timeout_add_seconds(6, self._restore_screenshot_button)
        
        print("Overlay скрыты для создания скриншота. Восстановятся через 5 секунд.")

    def _restore_screenshot_button(self):
        """Восстанавливает кнопку скриншота"""
        self.screenshot_btn.set_sensitive(True)
        self.status_label.set_text("Overlay восстановлены")
        return False  # Не повторяем таймер

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

    def signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения"""
        print(f"\nПолучен сигнал {signum}, завершаем работу...")
        self.overlay_manager.destroy()
        self.translation_engine.close()
        Gtk.main_quit()

def main():
    app = TranslatorApp()
    Gtk.main()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import html

class OverlayManager:
    """Менеджер для управления overlay окнами"""

    def __init__(self):
        self.overlay_windows = []  # Список всех overlay окон
        self.overlay_opacity = 0.8
        self._hidden_overlays = []  # Список временно скрытых overlay для восстановления
        self._is_hidden = False  # Флаг состояния скрытия
        self._screenshot_invisible = False  # Флаг невидимости для скриншотов
    
    def set_opacity(self, opacity):
        """Устанавливает прозрачность overlay"""
        self.overlay_opacity = opacity / 100.0
        # Применяем прозрачность ко всем overlay окнам
        for overlay in self.overlay_windows:
            try:
                overlay.set_opacity(self.overlay_opacity)
            except:
                pass  # Игнорируем deprecated warning
    
    def set_screenshot_invisible(self, invisible=True):
        """Настраивает overlay так, чтобы они были невидимы для программ захвата экрана"""
        self._screenshot_invisible = invisible
        
        for overlay in self.overlay_windows:
            try:
                if invisible:
                    # Делаем окно невидимым для программ захвата экрана
                    overlay.set_skip_taskbar_hint(True)
                    overlay.set_skip_pager_hint(True)
                    # Устанавливаем специальный тип окна
                    overlay.set_type_hint(Gdk.WindowTypeHint.UTILITY)
                    # Делаем окно "невидимым" для скриншотов
                    overlay.set_accept_focus(False)
                    overlay.set_focus_on_map(False)
                    # Устанавливаем специальные атрибуты окна
                    overlay.set_keep_below(False)
                    overlay.set_keep_above(True)
                else:
                    # Возвращаем нормальное поведение
                    overlay.set_skip_taskbar_hint(False)
                    overlay.set_skip_pager_hint(False)
                    overlay.set_type_hint(Gdk.WindowTypeHint.NORMAL)
                    overlay.set_accept_focus(True)
                    overlay.set_focus_on_map(True)
                    overlay.set_keep_below(False)
                    overlay.set_keep_above(True)
            except Exception as e:
                print(f"[DEBUG] Ошибка настройки невидимости: {e}")
        
        status = "включена" if invisible else "отключена"
        print(f"[DEBUG] Невидимость для скриншотов {status}")
    
    def toggle_screenshot_invisibility(self):
        """Переключает режим невидимости для скриншотов"""
        self.set_screenshot_invisible(not self._screenshot_invisible)
        return self._screenshot_invisible
    
    def show_overlay(self, text, x, y, w, h, compact_mode=True):
        """Показывает overlay окно с переведенным текстом (устаревший метод)"""
        # Закрываем предыдущий overlay
        self.hide_overlay()

        if compact_mode:
            self._create_compact_overlay(text, x, y, w, h)
        else:
            self._create_extended_overlay(text, x, y, w, h)

        if self.overlay_window:
            self.overlay_window.show_all()
            print(f"[DEBUG] Overlay показан: x={x}, y={y}, w={w}, h={h}")

    def show_multiple_overlays(self, text_blocks, window_x, window_y, compact_mode=True):
        """Показывает множество overlay окон для каждого текстового блока"""
        # Создаем новые overlay без скрытия старых
        new_overlays = []
        print(f"[DEBUG] Создаем overlay для {len(text_blocks)} блоков")
        print(f"[DEBUG] Позиция окна: x={window_x}, y={window_y}")
        
        for i, block in enumerate(text_blocks):
            if block.get('translated_text'):
                # Вычисляем абсолютные координаты
                abs_x = window_x + block['x']
                abs_y = window_y + block['y']
                
                print(f"[DEBUG] Блок {i+1}: '{block['text']}' -> '{block['translated_text']}'")
                print(f"[DEBUG] Координаты блока: x={block['x']}, y={block['y']}, w={block['width']}, h={block['height']}")
                print(f"[DEBUG] Абсолютные координаты: x={abs_x}, y={abs_y}")
                
                # Создаем overlay для каждого переведенного блока
                overlay = self._create_positioned_overlay(
                    block['translated_text'],
                    abs_x,
                    abs_y,
                    block['width'],
                    block['height'],
                    compact_mode
                )
                if overlay:
                    new_overlays.append(overlay)
                    overlay.show_all()
                    print(f"[DEBUG] Overlay {i+1} создан и показан")
                else:
                    print(f"[DEBUG] Не удалось создать overlay {i+1}")
        
        # Плавно заменяем старые overlay новыми
        if new_overlays:
            # Скрываем старые overlay
            self.hide_all_overlays()
            # Показываем новые
            self.overlay_windows = new_overlays
            print(f"[DEBUG] Показано {len(self.overlay_windows)} overlay окон")
        else:
            print("[DEBUG] Нет новых overlay для показа")

    def _create_positioned_overlay(self, text, x, y, w, h, compact_mode=True):
        """Создает overlay окно в указанной позиции"""
        try:
            overlay = Gtk.Window(type=Gtk.WindowType.POPUP)
            overlay.set_decorated(False)
            overlay.set_app_paintable(True)
            overlay.set_accept_focus(False)
            overlay.set_keep_above(True)

            # Делаем окно прозрачным для кликов
            screen = Gdk.Screen.get_default()
            rgba = screen.get_rgba_visual()
            if rgba:
                overlay.set_visual(rgba)

            # Создаем overlay для прозрачности кликов
            overlay_container = Gtk.Overlay()
            overlay.add(overlay_container)

            # Фон полностью прозрачный
            background = Gtk.EventBox()
            try:
                background.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
            except:
                pass
            overlay_container.add(background)

            # Создаем лейбл с текстом
            label = Gtk.Label()
            safe_text = html.escape(text)
            label.set_markup(f'<span foreground="white" font_desc="12" background="black">{safe_text}</span>')
            overlay_container.add_overlay(label)

            # Клики проходят сквозь overlay
            overlay_container.set_overlay_pass_through(label, True)
            overlay_container.set_overlay_pass_through(background, True)

            # Устанавливаем прозрачность
            try:
                overlay.set_opacity(self.overlay_opacity)
            except:
                pass

            # Делаем окно полностью прозрачным для событий
            overlay.set_events(Gdk.EventMask(0))

            # Устанавливаем размер и позицию
            overlay.set_default_size(w + 20, h + 10)  # Немного больше для читаемости
            
            # Позиционирование overlay по левому верхнему углу текста
            overlay_x = x  # Левый край overlay = левый край текста
            
            # Вертикальное позиционирование: overlay над текстом
            overlay_y = y - h - 8  # 8 пикселей отступ над текстом для лучшей читаемости
            
            # Защита от выхода за границы экрана
            if overlay_y < 0:
                overlay_y = y + h + 8  # Если не помещается сверху, размещаем снизу
            
            # Дополнительная защита от выхода за правый край экрана
            screen_width = Gdk.Screen.get_default().get_width()
            if overlay_x + w + 20 > screen_width:
                overlay_x = screen_width - w - 20 - 10  # 10px отступ от правого края
            
            overlay.move(overlay_x, overlay_y)
            
            # Принудительно показываем окно поверх всех
            overlay.set_keep_above(True)
            overlay.set_accept_focus(False)
            
            # Применяем настройки невидимости для скриншотов
            if self._screenshot_invisible:
                try:
                    overlay.set_skip_taskbar_hint(True)
                    overlay.set_skip_pager_hint(True)
                    overlay.set_type_hint(Gdk.WindowTypeHint.UTILITY)
                    overlay.set_focus_on_map(False)
                except:
                    pass
            
            print(f"[DEBUG] Overlay позиционирован: x={overlay_x}, y={overlay_y}, размер={w + 20}x{h + 10}")
            print(f"[DEBUG] Оригинальный текст: x={x}, y={y}, размер={w}x{h}")
            print(f"[DEBUG] Позиционирование: {'под текстом' if y - h - 5 < 0 else 'над текстом'}")

            return overlay

        except Exception as e:
            print(f"[Ошибка создания positioned overlay]: {e}")
            return None
    
    def _create_compact_overlay(self, text, x, y, w, h):
        """Создает компактный overlay"""
        self.overlay_window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.overlay_window.set_decorated(False)
        self.overlay_window.set_app_paintable(True)
        self.overlay_window.set_accept_focus(False)
        self.overlay_window.set_keep_above(True)
        
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
        try:
            self.overlay_window.set_opacity(self.overlay_opacity)
        except:
            pass

        # ВАЖНО: Делаем окно полностью прозрачным для событий
        self.overlay_window.set_events(Gdk.EventMask(0))

        # Применяем настройки невидимости для скриншотов
        if self._screenshot_invisible:
            try:
                self.overlay_window.set_skip_taskbar_hint(True)
                self.overlay_window.set_skip_pager_hint(True)
                self.overlay_window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
                self.overlay_window.set_focus_on_map(False)
            except:
                pass

        # Устанавливаем размер и позицию
        self.overlay_window.set_default_size(w, h)
        self.overlay_window.move(x, y)
    
    def _create_extended_overlay(self, text, x, y, w, h):
        """Создает расширенный overlay с прокруткой"""
        self.overlay_window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.overlay_window.set_decorated(False)
        self.overlay_window.set_app_paintable(True)
        self.overlay_window.set_accept_focus(False)
        self.overlay_window.set_keep_above(True)
        
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

        # Создаем текстовый вид с прокруткой
        text_view = Gtk.TextView()
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        
        # Устанавливаем текст
        buffer = text_view.get_buffer()
        buffer.set_text(text)
        
        # Создаем прокручиваемое окно
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(text_view)
        scrolled_window.set_size_request(400, 300)
        
        # Добавляем в overlay
        overlay.add_overlay(scrolled_window)
        
        # Клики проходят сквозь overlay
        overlay.set_overlay_pass_through(scrolled_window, True)
        overlay.set_overlay_pass_through(background, True)
        
        # Устанавливаем прозрачность всего окна
        try:
            self.overlay_window.set_opacity(self.overlay_opacity)
        except:
            pass
            
        # ВАЖНО: Делаем окно полностью прозрачным для событий
        self.overlay_window.set_events(Gdk.EventMask(0))

        # Применяем настройки невидимости для скриншотов
        if self._screenshot_invisible:
            try:
                self.overlay_window.set_skip_taskbar_hint(True)
                self.overlay_window.set_skip_pager_hint(True)
                self.overlay_window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
                self.overlay_window.set_focus_on_map(False)
            except:
                pass

        # Устанавливаем размер и позицию
        self.overlay_window.set_default_size(w, h)
        self.overlay_window.move(x, y)
    
    def hide_overlay(self):
        """Скрывает overlay окно (устаревший метод)"""
        if self.overlay_window:
            self.overlay_window.destroy()
            self.overlay_window = None
            print("[DEBUG] Overlay скрыт")

    def hide_all_overlays(self):
        """Скрывает все overlay окна"""
        for overlay in self.overlay_windows:
            try:
                overlay.destroy()
            except:
                pass
        self.overlay_windows.clear()
        print(f"[DEBUG] Все overlay окна скрыты")
    
    def is_visible(self):
        """Проверяет, видимо ли overlay окно"""
        return self.overlay_window is not None and self.overlay_window.get_visible()
    
    def update_position(self, x, y):
        """Обновляет позицию overlay окна"""
        if self.overlay_window:
            self.overlay_window.move(x, y)
            print(f"[DEBUG] Позиция overlay обновлена: x={x}, y={y}")
    
    def update_size(self, w, h):
        """Обновляет размер overlay окна"""
        if self.overlay_window:
            self.overlay_window.resize(w, h)
            print(f"[DEBUG] Размер overlay обновлен: w={w}, h={h}")
    
    def destroy(self):
        """Уничтожает overlay окно"""
        self.hide_overlay()
    
    def hide_for_screenshot(self):
        """Временно скрывает все overlay окна для создания скриншота"""
        if self._is_hidden:
            return  # Уже скрыты
            
        self._hidden_overlays = self.overlay_windows.copy()
        self.hide_all_overlays()
        self._is_hidden = True
        print("[DEBUG] Overlay временно скрыты для скриншота")
    
    def hide_for_screenshot_with_delay(self, delay_seconds=3):
        """Скрывает overlay с автоматическим восстановлением через указанное время"""
        if self._is_hidden:
            return  # Уже скрыты
            
        self.hide_for_screenshot()
        
        # Автоматически восстанавливаем через указанное время
        GLib.timeout_add_seconds(delay_seconds, self._auto_restore_after_screenshot)
        print(f"[DEBUG] Overlay будут автоматически восстановлены через {delay_seconds} секунд")
    
    def _auto_restore_after_screenshot(self):
        """Автоматическое восстановление overlay после скриншота"""
        self.restore_after_screenshot()
        return False  # Не повторяем таймер
    
    def restore_after_screenshot(self):
        """Восстанавливает все overlay окна после создания скриншота"""
        if not self._is_hidden:
            return  # Не были скрыты
            
        # Восстанавливаем все скрытые overlay
        for overlay in self._hidden_overlays:
            try:
                if overlay and not overlay.is_destroyed():
                    overlay.show_all()
                    self.overlay_windows.append(overlay)
            except:
                pass  # Игнорируем ошибки
        
        self._hidden_overlays.clear()
        self._is_hidden = False
        print(f"[DEBUG] Восстановлено {len(self.overlay_windows)} overlay окон")
    
    def is_hidden_for_screenshot(self):
        """Проверяет, скрыты ли overlay для скриншота"""
        return self._is_hidden

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для проверки X11 атрибутов и невидимости overlay на скриншотах
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import os
import subprocess
import time

def check_x11_session():
    """Проверяет тип сессии и доступность X11"""
    print("=== Проверка X11 сессии ===")
    
    session_type = os.environ.get('XDG_SESSION_TYPE', 'unknown')
    display = os.environ.get('DISPLAY', 'unknown')
    
    print(f"Тип сессии: {session_type}")
    print(f"DISPLAY: {display}")
    
    if session_type.lower() == 'x11':
        print("✅ X11 сессия обнаружена")
        return True
    elif session_type.lower() == 'wayland':
        print("⚠️  Wayland сессия - невидимость может не работать")
        return False
    else:
        print("❓ Неизвестный тип сессии")
        return False

def check_x11_tools():
    """Проверяет доступность X11 инструментов"""
    print("\n=== Проверка X11 инструментов ===")
    
    tools = [
        ("xprop", ["xprop", "-version"]),
        ("xwininfo", ["xwininfo", "-version"]),
        ("xrandr", ["xrandr", "--version"]),
        ("xset", ["xset", "-version"])
    ]
    
    available_tools = []
    for tool_name, cmd in tools:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ {tool_name} - доступен")
                available_tools.append(tool_name)
            else:
                print(f"❌ {tool_name} - ошибка: {result.stderr}")
        except FileNotFoundError:
            print(f"❌ {tool_name} - не установлен")
        except subprocess.TimeoutExpired:
            print(f"⏰ {tool_name} - таймаут")
        except Exception as e:
            print(f"❌ {tool_name} - ошибка: {e}")
    
    return available_tools

def test_window_attributes():
    """Тестирует создание окна с X11 атрибутами"""
    print("\n=== Тест X11 атрибутов окна ===")
    
    # Создаем тестовое окно
    window = Gtk.Window(type=Gtk.WindowType.POPUP)
    window.set_decorated(False)
    window.set_app_paintable(True)
    window.set_accept_focus(False)
    window.set_keep_above(True)
    
    # Устанавливаем X11 атрибуты
    window.set_skip_taskbar_hint(True)
    window.set_skip_pager_hint(True)
    window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
    
    # Создаем лейбл
    label = Gtk.Label(label="Тестовое окно с X11 атрибутами")
    label.set_markup('<span foreground="white" background="black" font_desc="16">Тестовое окно с X11 атрибутами</span>')
    window.add(label)
    
    # Устанавливаем размер и позицию
    window.set_default_size(300, 100)
    window.move(100, 100)
    
    # Показываем окно
    window.show_all()
    
    print("✅ Тестовое окно создано с X11 атрибутами")
    print("Проверьте, что окно видно на экране, но не в списке окон")
    print("Нажмите Enter для продолжения...")
    
    input()
    
    # Проверяем атрибуты
    print(f"Skip taskbar: {window.get_skip_taskbar_hint()}")
    print(f"Skip pager: {window.get_skip_pager_hint()}")
    print(f"Type hint: {window.get_type_hint()}")
    print(f"Accept focus: {window.get_accept_focus()}")
    print(f"Keep above: {window.get_keep_above()}")
    
    # Закрываем окно
    window.destroy()
    print("✅ Тестовое окно закрыто")

def test_screenshot_tools():
    """Тестирует различные инструменты для скриншотов"""
    print("\n=== Тест инструментов для скриншотов ===")
    
    tools = [
        ("gnome-screenshot", ["gnome-screenshot", "--version"]),
        ("scrot", ["scrot", "--version"]),
        ("import (ImageMagick)", ["import", "-version"]),
        ("xwd", ["xwd", "-help"]),
        ("xwd", ["xwd", "-version"])
    ]
    
    print("Доступные инструменты для скриншотов:")
    available_tools = []
    for tool_name, cmd in tools:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ {tool_name} - доступен")
                available_tools.append(tool_name)
            else:
                print(f"❌ {tool_name} - ошибка: {result.stderr}")
        except FileNotFoundError:
            print(f"❌ {tool_name} - не установлен")
        except subprocess.TimeoutExpired:
            print(f"⏰ {tool_name} - таймаут")
        except Exception as e:
            print(f"❌ {tool_name} - ошибка: {e}")
    
    return available_tools

def test_x11_properties():
    """Тестирует X11 свойства окна"""
    print("\n=== Тест X11 свойств ===")
    
    try:
        # Создаем тестовое окно
        window = Gtk.Window(type=Gtk.WindowType.POPUP)
        window.set_decorated(False)
        window.set_app_paintable(True)
        window.set_accept_focus(False)
        window.set_keep_above(True)
        
        # Устанавливаем X11 атрибуты
        window.set_skip_taskbar_hint(True)
        window.set_skip_pager_hint(True)
        window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        
        # Создаем лейбл
        label = Gtk.Label(label="Тест X11 свойств")
        label.set_markup('<span foreground="white" background="red" font_desc="14">Тест X11 свойств</span>')
        window.add(label)
        
        # Устанавливаем размер и позицию
        window.set_default_size(250, 80)
        window.move(150, 150)
        
        # Показываем окно
        window.show_all()
        
        print("✅ Окно с X11 свойствами создано")
        print("Попробуйте создать скриншот - это окно не должно попасть на него")
        print("Нажмите Enter для продолжения...")
        
        input()
        
        # Получаем Gdk.Window для проверки низкоуровневых свойств
        gdk_window = window.get_window()
        if gdk_window:
            print("✅ Gdk.Window получен")
            print(f"Skip taskbar: {gdk_window.get_skip_taskbar_hint()}")
            print(f"Skip pager: {gdk_window.get_skip_pager_hint()}")
            # get_keep_above может быть недоступен в некоторых версиях GTK
            try:
                print(f"Keep above: {gdk_window.get_keep_above()}")
            except AttributeError:
                print("Keep above: метод недоступен в данной версии GTK")
        else:
            print("❌ Не удалось получить Gdk.Window")
        
        # Закрываем окно
        window.destroy()
        print("✅ Тестовое окно закрыто")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования X11 свойств: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Основная функция тестирования"""
    print("🧪 Тест X11 атрибутов и невидимости overlay для скриншотов")
    print("=" * 60)
    
    try:
        # Проверяем X11 сессию
        is_x11 = check_x11_session()
        
        # Проверяем X11 инструменты
        x11_tools = check_x11_tools()
        
        # Тестируем атрибуты окна
        test_window_attributes()
        
        # Тестируем X11 свойства
        test_x11_properties()
        
        # Тестируем инструменты для скриншотов
        screenshot_tools = test_screenshot_tools()
        
        print("\n" + "=" * 60)
        print("🎉 Тестирование завершено!")
        print(f"X11 сессия: {'✅ Да' if is_x11 else '❌ Нет'}")
        print(f"Доступных X11 инструментов: {len(x11_tools)}")
        print(f"Доступных инструментов скриншотов: {len(screenshot_tools)}")
        
        if is_x11:
            print("\n✅ Рекомендации:")
            print("- X11 сессия обнаружена - невидимость должна работать")
            print("- Используйте режим невидимости в основном приложении")
            print("- Создавайте скриншоты любым доступным инструментом")
        else:
            print("\n⚠️  Рекомендации:")
            print("- Wayland сессия - невидимость может не работать")
            print("- Попробуйте переключиться на X11")
            print("- Или используйте ручное скрытие overlay")
        
    except KeyboardInterrupt:
        print("\n\nТест прерван пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка во время тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

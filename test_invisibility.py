#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для демонстрации невидимости overlay для скриншотов
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import time
import subprocess

from overlay_manager import OverlayManager

def test_overlay_invisibility():
    """Тестирует функциональность невидимости overlay для скриншотов"""
    
    print("=== Тест невидимости overlay для скриншотов ===")
    
    # Создаем менеджер overlay
    overlay_manager = OverlayManager()
    
    # Показываем тестовые overlay
    print("Создаем тестовые overlay...")
    overlay_manager.show_multiple_overlays([
        {
            'text': 'Тестовый текст 1',
            'translated_text': 'Test text 1',
            'x': 100, 'y': 100, 'width': 150, 'height': 30
        },
        {
            'text': 'Тестовый текст 2', 
            'translated_text': 'Test text 2',
            'x': 100, 'y': 150, 'width': 150, 'height': 30
        }
    ], 0, 0, True)
    
    print("Overlay созданы и видны на экране")
    print("Нажмите Enter для продолжения...")
    input()
    
    # Тестируем режим невидимости
    print("\nВключаем режим невидимости для скриншотов...")
    overlay_manager.set_screenshot_invisible(True)
    
    print("Теперь overlay должны быть невидимы для программ захвата экрана")
    print("Но они все еще видны на экране!")
    print("Попробуйте создать скриншот - overlay не должны попасть на него")
    print("Нажмите Enter для продолжения...")
    input()
    
    # Выключаем режим невидимости
    print("\nВыключаем режим невидимости для скриншотов...")
    overlay_manager.set_screenshot_invisible(False)
    
    print("Теперь overlay снова видны для программ захвата экрана")
    print("Нажмите Enter для продолжения...")
    input()
    
    # Тестируем переключение
    print("\nТестируем переключение режима...")
    for i in range(3):
        is_invisible = overlay_manager.toggle_screenshot_invisibility()
        status = "ВКЛ" if is_invisible else "ВЫКЛ"
        print(f"Итерация {i+1}: Режим невидимости {status}")
        time.sleep(1)
    
    # Очищаем
    print("\nОчищаем overlay...")
    overlay_manager.hide_all_overlays()
    
    print("Тест завершен!")

def test_screenshot_tools():
    """Тестирует различные инструменты для создания скриншотов"""
    
    print("\n=== Тест инструментов для скриншотов ===")
    
    tools = [
        ("gnome-screenshot", ["gnome-screenshot", "--version"]),
        ("scrot", ["scrot", "--version"]),
        ("import (ImageMagick)", ["import", "-version"]),
        ("xwd", ["xwd", "-help"])
    ]
    
    print("Доступные инструменты для скриншотов:")
    for tool_name, cmd in tools:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ {tool_name} - доступен")
            else:
                print(f"❌ {tool_name} - ошибка: {result.stderr}")
        except FileNotFoundError:
            print(f"❌ {tool_name} - не установлен")
        except subprocess.TimeoutExpired:
            print(f"⏰ {tool_name} - таймаут")
        except Exception as e:
            print(f"❌ {tool_name} - ошибка: {e}")

if __name__ == "__main__":
    print("Демонстрация невидимости overlay для скриншотов")
    print("=" * 50)
    
    try:
        test_overlay_invisibility()
        test_screenshot_tools()
        
        print("\n🎉 Все тесты завершены успешно!")
        print("\nИнструкция по использованию:")
        print("1. Запустите основное приложение: python3 main.py")
        print("2. Включите режим невидимости для скриншотов")
        print("3. Создавайте скриншоты - overlay не будут видны!")
        
    except KeyboardInterrupt:
        print("\n\nТест прерван пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка во время теста: {e}")
        import traceback
        traceback.print_exc()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Вспомогательный скрипт для создания скриншотов без overlay надписей
"""

import subprocess
import time
import sys
import os

def take_screenshot_without_overlay(overlay_manager, delay_seconds=3):
    """
    Создает скриншот, временно скрывая overlay надписи
    
    Args:
        overlay_manager: Экземпляр OverlayManager
        delay_seconds: Время в секундах, на которое скрываются overlay
    """
    print(f"Скрываем overlay на {delay_seconds} секунд для создания скриншота...")
    
    # Скрываем overlay
    overlay_manager.hide_for_screenshot_with_delay(delay_seconds)
    
    # Ждем немного, чтобы overlay успели скрыться
    time.sleep(0.5)
    
    # Создаем скриншот
    print("Создаем скриншот...")
    try:
        # Используем gnome-screenshot для создания скриншота
        result = subprocess.run([
            "gnome-screenshot", 
            "--interactive",  # Интерактивный режим выбора области
            "--delay=1"       # Задержка 1 секунда
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Скриншот создан успешно!")
        else:
            print(f"Ошибка создания скриншота: {result.stderr}")
            
    except FileNotFoundError:
        print("gnome-screenshot не найден. Попробуйте установить gnome-screenshot")
        print("Или используйте другой инструмент для создания скриншотов")
    except Exception as e:
        print(f"Ошибка при создании скриншота: {e}")
    
    print("Overlay будут автоматически восстановлены...")

def take_screenshot_manual(overlay_manager):
    """
    Ручное управление overlay для создания скриншота
    """
    print("Скрываем overlay для создания скриншота...")
    overlay_manager.hide_for_screenshot()
    
    print("Теперь вы можете создать скриншот вручную.")
    print("После создания скриншота нажмите Enter для восстановления overlay...")
    
    input()
    
    print("Восстанавливаем overlay...")
    overlay_manager.restore_after_screenshot()
    print("Overlay восстановлены!")

if __name__ == "__main__":
    print("Вспомогательный скрипт для создания скриншотов без overlay")
    print("Этот скрипт должен использоваться вместе с основным приложением")
    print("Для использования импортируйте функции в основной код")

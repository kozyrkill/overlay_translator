#!/bin/bash

# Скрипт запуска Overlay Translator
# Использует системный Python для GTK и виртуальное окружение для остальных пакетов

cd "$(dirname "$0")"

# Временно отключаем pyenv для этого скрипта
if [ -n "$PYENV_VERSION" ]; then
    echo "⚠️  pyenv активен, временно отключаем для запуска..."
    unset PYENV_VERSION
    unset PYENV_ROOT
    export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
fi

if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Запустите setup.sh для установки"
    exit 1
fi

echo "🚀 Запуск Overlay Translator..."
echo "📝 Настройка окружения..."

# Проверяем, есть ли системный gi
if ! /usr/bin/python3 -c "import gi" 2>/dev/null; then
    echo "❌ Модуль gi не найден в системном Python!"
    echo "Установите PyGObject: sudo apt install python3-gi python3-gi-cairo"
    exit 1
fi

# Запускаем с системным Python (для GTK) + виртуальное окружение (для пакетов)
echo "🔧 Используется системный Python для GTK + venv для пакетов"
echo ""

# Устанавливаем PYTHONPATH для доступа к пакетам из venv
export PYTHONPATH="$PWD/venv/lib/python3.13/site-packages:$PYTHONPATH"

# Используем системный Python, но с доступом к venv пакетам
/usr/bin/python3 main.py

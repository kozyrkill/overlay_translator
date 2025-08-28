#!/bin/bash

# Скрипт запуска Overlay Translator
# ВАЖНО: Запускайте через source run.sh (не ./run.sh)

# Путь к проекту
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Запустите setup.sh для установки"
    return 1
fi

# Активируем виртуальное окружение
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Проверяем наличие основных Python пакетов
echo "🔍 Проверка Python пакетов..."
python3 -c "import pytesseract, PIL, googletrans, requests" 2>/dev/null || {
    echo "❌ Не все Python пакеты установлены"
    echo "Запустите: source venv/bin/activate && pip install -r requirements.txt"
    return 1
}

echo "✅ Все Python пакеты найдены"

# Запускаем приложение
echo "🚀 Запуск Overlay Translator..."
echo "📝 Используется виртуальное окружение: $(which python3)"
echo "📦 Python пакеты из: venv/lib/python*/site-packages"
echo ""

# Запускаем приложение
python3 main.py

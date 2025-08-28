#!/bin/bash
set -e

echo "[1/4] Проверка и установка системных пакетов..."

declare -a DEPS=(
  "tesseract-ocr"
  "tesseract-ocr-rus"
  "tesseract-ocr-eng"
  "imagemagick"
  "xdotool"
  "x11-utils"
  "scrot"
  "python3-gi"
  "gir1.2-gtk-3.0"
  "libgirepository1.0-dev"
  "libcairo2-dev"
  "gir1.2-glib-2.0"
  "libglib2.0-dev"
)

for pkg in "${DEPS[@]}"; do
    if ! dpkg -s "$pkg" &>/dev/null; then
        echo "  -> Установка $pkg..."
        sudo apt install -y "$pkg"
    else
        echo "  -> $pkg уже установлен"
    fi
done

echo "[2/4] Создание виртуального окружения и установка Python-зависимостей..."
# Создаем виртуальное окружение
if [ ! -d "venv" ]; then
    echo "  -> Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение и устанавливаем зависимости
echo "  -> Активация виртуального окружения..."
source venv/bin/activate
echo "  -> Установка Python пакетов..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/4] Создание локальной папки для кэша..."
mkdir -p cache

echo "[3.5/4] Проверка языков Tesseract..."
# Проверяем наличие русского и английского языков
if ! tesseract --list-langs 2>/dev/null | grep -q "rus"; then
    echo "  -> Устанавливаем русский язык для Tesseract..."
    sudo apt install -y tesseract-ocr-rus
fi

if ! tesseract --list-langs 2>/dev/null | grep -q "eng"; then
    echo "  -> Устанавливаем английский язык для Tesseract..."
    sudo apt install -y tesseract-ocr-eng
fi

echo "[4/4] Установка завершена!"
echo "  -> Приложение поддерживает два режима:"
echo "     - Компактный вид (по умолчанию) - простой интерфейс"
echo "     - Расширенный вид - с отображением OCR и перевода"
echo "  -> Используйте галочку 'Компактный вид' для переключения режимов"
echo ""
echo "🚀 Для запуска используйте:"
echo "   ./start.sh"
echo ""
echo "📝 Или вручную:"
echo "   export PYTHONPATH=\"\$PWD/venv/lib/python3.13/site-packages:\$PYTHONPATH\" && python3 main.py"

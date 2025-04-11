#!/bin/bash
set -e

echo "[1/4] Проверка и установка системных пакетов..."

declare -a DEPS=(
  "tesseract-ocr"
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

echo "[2/4] Установка Python-зависимостей через pip..."
pip3 install --break-system-packages -r requirements.txt

echo "[3/4] Создание локальной папки для кэша..."
mkdir -p cache

echo "[4/4] Запуск приложения..."
python3 main.py

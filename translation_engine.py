#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import requests
import html
import re

class TranslationEngine:
    """Движок для перевода текста"""
    
    def __init__(self, db_path="cache/overlay_translator_cache.sqlite"):
        self.db_path = db_path
        self.conn = None
        self.connect_db()
    
    def connect_db(self):
        """Подключается к базе данных кэша"""
        try:
            # Используем check_same_thread=False для работы из разных потоков
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.create_tables()
            print(f"[DEBUG] Подключение к БД: {self.db_path}")
        except Exception as e:
            print(f"[Ошибка БД]: {e}")
    
    def create_tables(self):
        """Создает таблицы в базе данных"""
        try:
            cur = self.conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    source_text TEXT PRIMARY KEY,
                    translated_text TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
        except Exception as e:
            print(f"[Ошибка создания таблиц]: {e}")
    
    def translate_text(self, text, translator="Google"):
        """Переводит текст используя указанный переводчик"""
        if not text:
            return ""
            
        try:
            # Проверяем кэш
            cur = self.conn.cursor()
            cur.execute("SELECT translated_text FROM translations WHERE source_text = ?", (text,))
            row = cur.fetchone()
            if row:
                print(f"[DEBUG] Перевод из кэша: '{text[:50]}...'")
                return row[0]

            # Выполняем перевод
            translated = ""
            if translator == "Ollama":
                translated = self._translate_with_ollama(text)
            elif translator == "Google":
                translated = self._translate_with_google(text)
            else:
                translated = f"[Ошибка: Неизвестный переводчик '{translator}']"

            # Сохраняем в кэш
            if translated and not translated.startswith("[Ошибка"):
                cur.execute("INSERT OR REPLACE INTO translations (source_text, translated_text) VALUES (?, ?)", 
                          (text, translated))
                self.conn.commit()
                
            return translated
            
        except Exception as e:
            print(f"[Ошибка перевода]: {e}")
            return f"[Ошибка перевода: {e}]"
    
    def _translate_with_ollama(self, text):
        """Переводит текст используя Ollama"""
        try:
            r = requests.post("http://localhost:11434/api/generate", 
                            json={"model": "llama3", "prompt": f"Translate to Russian: {text}"},
                            timeout=5)
            translated = r.json().get("response", "")
            print(f"[DEBUG] Ollama: '{text[:50]}...' -> '{translated[:50]}...'")
            return translated
            
        except requests.exceptions.ConnectionError:
            return "[Ошибка: Ollama сервер недоступен. Запустите 'ollama serve' или выберите Google Translate]"
        except Exception as e:
            return f"[Ошибка Ollama: {e}]"
    
    def _translate_with_google(self, text):
        """Переводит текст используя Google Translate API"""
        try:
            # Ограничиваем длину текста для Google Translate
            if len(text) > 5000:
                text = text[:5000]
            
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                'client': 'gtx',
                'sl': 'auto',
                'tl': 'ru',
                'dt': 't',
                'q': text
            }
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and data[0]:
                    translated = ''.join([part[0] for part in data[0] if part[0]])
                    print(f"[DEBUG] Google Translate: '{text[:50]}...' -> '{translated[:50]}...'")
                    return translated
                else:
                    return f"[Ошибка Google Translate: Неверный ответ API]"
            else:
                return f"[Ошибка Google Translate: HTTP {response.status_code}]"
                
        except Exception as e:
            return f"[Ошибка Google Translate: {e}]"
    
    def split_into_sentences(self, text):
        """Разбивает текст на предложения для лучшего перевода"""
        if not text:
            return []

        # Фильтруем текст - убираем элементы интерфейса
        filtered_text = self._filter_ui_elements(text)

        # Разбиваем по строкам (более эффективно для UI)
        lines = [line.strip() for line in filtered_text.split('\n') if line.strip()]

        # Фильтруем слишком короткие или технические строки
        meaningful_lines = []
        for line in lines:
            # Пропускаем технические элементы
            if any(skip in line.lower() for skip in ['debug', 'error', 'http', 'api', 'overlay', 'translator']):
                continue
            # Пропускаем слишком короткие строки
            if len(line.strip()) < 3:
                continue
            # Пропускаем строки только с символами
            if not any(c.isalpha() for c in line):
                continue
            meaningful_lines.append(line)

        # Если фильтр слишком агрессивный, возвращаем исходный текст
        if len(meaningful_lines) < 2:
            print(f"[DEBUG] Фильтр слишком агрессивный, возвращаем исходный текст")
            return [text]

        return meaningful_lines

    def translate_text_blocks(self, text_blocks, translator="Google"):
        """Переводит множество текстовых блоков"""
        if not text_blocks:
            return []

        translated_blocks = []
        
        for block in text_blocks:
            if block.get('text'):
                translated_text = self.translate_text(block['text'], translator)
                # Создаем новый блок с переводом
                translated_block = block.copy()
                translated_block['translated_text'] = translated_text
                translated_blocks.append(translated_block)
        
        print(f"[DEBUG] Переведено {len(translated_blocks)} текстовых блоков")
        return translated_blocks
    
    def _filter_ui_elements(self, text):
        """Фильтрует элементы интерфейса из текста"""
        # Убираем элементы интерфейса Overlay Translator
        ui_patterns = [
            'выбрать окно', 'обновить перевод', 'старт', 'стоп',
            'интервал', 'переводчик', 'компактный вид', 'прозрачность',
            'сбросить кэш', 'окно:', 'перевод:', 'распознанный текст:',
            'overlay translator', 'select window', 'update translation',
            'start', 'stop', 'interval', 'translator', 'compact view',
            'transparency', 'clear cache', 'window:', 'translation:',
            'recognized text:'
        ]
        
        # Разбиваем на строки
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Проверяем, содержит ли строка элементы интерфейса
            should_skip = False
            for pattern in ui_patterns:
                if pattern.lower() in line.lower():
                    should_skip = True
                    break
            
            # Пропускаем строки с элементами интерфейса
            if should_skip:
                continue
                
            # Пропускаем слишком короткие строки
            if len(line) < 3:
                continue
                
            # Пропускаем строки только с символами
            if not any(c.isalpha() for c in line):
                continue
                
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def clear_cache(self):
        """Очищает кэш переводов"""
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM translations")
            self.conn.commit()
            print("[DEBUG] Кэш переводов очищен")
        except Exception as e:
            print(f"[Ошибка очистки кэша]: {e}")
    
    def close(self):
        """Закрывает соединение с базой данных"""
        if self.conn:
            self.conn.close()
            print("[DEBUG] Соединение с БД закрыто")

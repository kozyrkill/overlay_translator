#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import pytesseract
from PIL import Image
import numpy as np
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib

class OCREngine:
    """Движок для оптического распознавания текста"""
    
    def __init__(self):
        self.image_path = "/tmp/window_capture.png"
        self.last_image_hash = None
        self.last_ocr_result = None
    
    def capture_window(self, window_id):
        """Захватывает изображение окна"""
        try:
            # Пробуем несколько методов захвата
            methods = [
                ["scrot", "-u", "-o", self.image_path],  # Захват активного окна
                ["scrot", "-o", self.image_path],        # Захват всего экрана
                ["import", "-window", window_id, self.image_path]  # ImageMagick (если установлен)
            ]
            
            success = False
            for method in methods:
                try:
                    print(f"[DEBUG] Пробуем метод захвата: {' '.join(method)}")
                    subprocess.run(method, capture_output=True, text=True, check=True, timeout=5)
                    
                    # Ждем создания файла
                    time.sleep(0.3)
                    
                    # Проверяем, что файл создан и не пустой
                    if os.path.exists(self.image_path) and os.path.getsize(self.image_path) > 1000:
                        print(f"[DEBUG] Успешный захват методом: {' '.join(method)}")
                        success = True
                        break
                    else:
                        print(f"[DEBUG] Метод {' '.join(method)} не создал файл")
                        
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    print(f"[DEBUG] Метод {' '.join(method)} не сработал: {e}")
                    continue
            
            if not success:
                raise FileNotFoundError("Ни один метод захвата не сработал")
                
            print(f"[DEBUG] Изображение окна {window_id} захвачено: {self.image_path}")
            
            # Обновляем время и размер файла для сравнения
            self.last_capture_time = time.time()
            if os.path.exists(self.image_path):
                self.last_file_size = os.path.getsize(self.image_path)
            
            return True
            
        except Exception as e:
            print(f"[Ошибка OCR]: {e}")
            return False
    
    def recognize_text(self, lang='rus+eng'):
        """Распознает текст на изображении"""
        try:
            if not os.path.exists(self.image_path):
                return ""
                
            image = Image.open(self.image_path)
            text = pytesseract.image_to_string(image, lang=lang).strip()
            
            print(f"[DEBUG] OCR распознал текст длиной: {len(text)} символов")
            return text
            
        except Exception as e:
            print(f"[Ошибка OCR]: {e}")
            return ""

    def recognize_text_with_positions(self, lang='rus+eng'):
        """Распознает текст с координатами каждого блока"""
        try:
            if not os.path.exists(self.image_path):
                print(f"[DEBUG] Файл изображения не найден: {self.image_path}")
                return []
            
            # Проверяем размер файла
            file_size = os.path.getsize(self.image_path)
            print(f"[DEBUG] Размер файла изображения: {file_size} байт")
            
            if file_size < 1000:
                print(f"[DEBUG] Файл слишком маленький, возможно поврежден")
                return []
            
            image = Image.open(self.image_path)
            print(f"[DEBUG] Размер изображения: {image.size}")
            
            # Получаем данные с координатами
            data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
            
            text_blocks = []
            n_boxes = len(data['text'])
            print(f"[DEBUG] Tesseract нашел {n_boxes} блоков")
            
            for i in range(n_boxes):
                confidence = int(data['conf'][i])
                text = data['text'][i].strip()
                
                # Выводим информацию о каждом блоке
                if text:
                    print(f"[DEBUG] Блок {i}: '{text}' (уверенность: {confidence}%)")
                
                # Фильтруем пустые блоки и блоки с низкой уверенностью
                if confidence > 30 and text:
                    # Получаем координаты
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    # Фильтруем слишком короткий текст
                    if len(text) > 2:
                        text_blocks.append({
                            'text': text,
                            'x': x,
                            'y': y,
                            'width': w,
                            'height': h,
                            'confidence': confidence
                        })
                        print(f"[DEBUG] Добавлен блок: '{text}' на позиции ({x}, {y}) размером {w}x{h}")
            
            print(f"[DEBUG] OCR распознал {len(text_blocks)} текстовых блоков с координатами")
            
            # Объединяем близкие блоки в целые предложения
            merged_blocks = self._merge_nearby_blocks(text_blocks)
            print(f"[DEBUG] После объединения: {len(merged_blocks)} блоков")
            
            # Сохраняем результат для кэширования
            self.last_ocr_result = merged_blocks
            
            return merged_blocks
            
        except Exception as e:
            print(f"[Ошибка OCR с координатами]: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def cleanup(self):
        """Очищает временные файлы"""
        try:
            if os.path.exists(self.image_path):
                os.remove(self.image_path)
                print(f"[DEBUG] Временный файл удален: {self.image_path}")
        except Exception as e:
            print(f"[Ошибка очистки]: {e}")
    
    def get_window_geometry(self, window_id):
        """Получает геометрию окна"""
        try:
            result = subprocess.run(
                ["xdotool", "getwindowgeometry", window_id],
                capture_output=True, text=True, check=True, timeout=2
            )
            
            # Парсим вывод xdotool
            output = result.stdout.strip()
            if "Position:" in output and "Geometry:" in output:
                # Извлекаем позицию и размер
                lines = output.split('\n')
                pos_line = [l for l in lines if "Position:" in l][0]
                geom_line = [l for l in lines if "Geometry:" in l][0]
                
                            # Парсим позицию
            pos_parts = pos_line.split("Position:")[1].strip().split(',')
            x_str = pos_parts[0].strip()
            y_str = pos_parts[1].strip()
            
            # Убираем возможные скобки и текст
            x_str = x_str.split('(')[0].strip()
            y_str = y_str.split('(')[0].strip()
            
            try:
                x, y = int(x_str), int(y_str)
            except ValueError:
                x, y = 100, 100
            
            # Парсим размер
            geom_parts = geom_line.split("Geometry:")[1].strip().split('x')
            w_str = geom_parts[0].strip()
            h_str = geom_parts[1].strip()
            
            # Убираем возможные скобки и текст
            w_str = w_str.split('(')[0].strip()
            h_str = h_str.split('(')[0].strip()
            
            try:
                w, h = int(w_str), int(h_str)
            except ValueError:
                w, h = 800, 200
                
                # Добавляем небольшое смещение для лучшей видимости
                x += 10
                y += 10
                w = max(w - 20, 400)  # Минимальная ширина
                h = max(h - 20, 100)  # Минимальная высота
                
                print(f"[DEBUG] Геометрия окна: x={x}, y={y}, w={w}, h={h}")
                return x, y, w, h
                
        except subprocess.CalledProcessError as e:
            print(f"[Ошибка геометрии]: {e}")
        except subprocess.TimeoutExpired:
            print(f"[Ошибка геометрии]: Таймаут")
        except Exception as e:
            print(f"[Ошибка геометрии]: {e}")
        
        # Возвращаем значения по умолчанию
        return 100, 100, 800, 200

    def _update_image_hash(self):
        """Обновляет текущее изображение для сравнения"""
        try:
            if os.path.exists(self.image_path):
                self.last_image = Image.open(self.image_path).convert('L')  # Конвертируем в grayscale
                print(f"[DEBUG] Изображение сохранено для сравнения: {self.image_path}")
        except Exception as e:
            print(f"[Ошибка сохранения изображения]: {e}")

    def has_image_changed(self, threshold=0.01):
        """Проверяет, изменилось ли изображение по времени и размеру"""
        if not hasattr(self, 'last_capture_time') or self.last_capture_time is None:
            print("[DEBUG] Первый захват изображения")
            return True
        
        try:
            if os.path.exists(self.image_path):
                # Проверяем время последнего захвата
                current_time = time.time()
                time_diff = current_time - self.last_capture_time
                
                # Если прошло больше 2 секунд, считаем что изображение изменилось
                if time_diff > 2.0:
                    print(f"[DEBUG] Прошло {time_diff:.1f} секунд, считаем изображение измененным")
                    return True
                
                # Проверяем размер файла
                current_size = os.path.getsize(self.image_path)
                if not hasattr(self, 'last_file_size') or self.last_file_size != current_size:
                    print(f"[DEBUG] Размер файла изменился: {getattr(self, 'last_file_size', 'None')} -> {current_size}")
                    return True
                
                # Если все проверки пройдены, изображение не изменилось
                print(f"[DEBUG] Изображение не изменилось (прошло {time_diff:.1f}с, размер: {current_size})")
                return False
            else:
                print("[DEBUG] Файл изображения не найден")
                return True
        except Exception as e:
            print(f"[Ошибка проверки изображения]: {e}")
            return True

    def get_cached_ocr_result(self):
        """Возвращает кэшированный результат OCR, если изображение не изменилось"""
        if not self.has_image_changed():
            print("[DEBUG] Изображение не изменилось, используем кэш")
            return self.last_ocr_result
        else:
            print("[DEBUG] Изображение изменилось, нужен новый OCR")
            return None

    def get_cached_translated_blocks(self):
        """Возвращает кэшированные переведенные блоки, если изображение не изменилось"""
        if not self.has_image_changed():
            print("[DEBUG] Изображение не изменилось, используем кэш переводов")
            return getattr(self, 'last_translated_blocks', None)
        else:
            print("[DEBUG] Изображение изменилось, нужны новые переводы")
            return None

    def cache_translated_blocks(self, translated_blocks):
        """Кэширует переведенные блоки"""
        self.last_translated_blocks = translated_blocks
        print(f"[DEBUG] Кэшировано {len(translated_blocks)} переведенных блоков")

    def clear_cache(self):
        """Очищает весь кэш"""
        self.last_image = None
        self.last_ocr_result = None
        self.last_translated_blocks = None
        self.last_capture_time = None
        self.last_file_size = None
        print("[DEBUG] Кэш полностью очищен")

    def _merge_nearby_blocks(self, text_blocks):
        """Объединяет близкие текстовые блоки в целые предложения"""
        if not text_blocks:
            return []
        
        # Сортируем блоки по координатам (сверху вниз, слева направо)
        sorted_blocks = sorted(text_blocks, key=lambda b: (b['y'], b['x']))
        
        merged_blocks = []
        current_group = []
        
        for block in sorted_blocks:
            if not current_group:
                current_group = [block]
                continue
            
            last_block = current_group[-1]
            
            # Проверяем, можно ли объединить блоки
            if self._can_merge_blocks(last_block, block):
                current_group.append(block)
            else:
                # Объединяем текущую группу
                if current_group:
                    merged_block = self._merge_block_group(current_group)
                    merged_blocks.append(merged_block)
                current_group = [block]
        
        # Добавляем последнюю группу
        if current_group:
            merged_block = self._merge_block_group(current_group)
            merged_blocks.append(merged_block)
        
        # Фильтруем слишком длинные блоки (возможно, неправильно объединенные)
        filtered_blocks = []
        for block in merged_blocks:
            # Если блок слишком длинный (>200 символов), разбиваем его
            if len(block['text']) > 200:
                print(f"[DEBUG] Блок слишком длинный ({len(block['text'])} символов), разбиваем: '{block['text'][:50]}...'")
                # Разбиваем по пробелам на части по ~100 символов
                words = block['text'].split()
                current_part = []
                current_length = 0
                
                for word in words:
                    if current_length + len(word) + 1 > 100 and current_part:
                        # Создаем новый блок для текущей части
                        part_text = ' '.join(current_part)
                        filtered_blocks.append({
                            'text': part_text,
                            'x': block['x'],
                            'y': block['y'],
                            'width': block['width'],
                            'height': block['height'],
                            'confidence': block['confidence']
                        })
                        current_part = [word]
                        current_length = len(word)
                    else:
                        current_part.append(word)
                        current_length += len(word) + 1
                
                # Добавляем последнюю часть
                if current_part:
                    part_text = ' '.join(current_part)
                    filtered_blocks.append({
                        'text': part_text,
                        'x': block['x'],
                        'y': block['y'],
                        'width': block['width'],
                        'height': block['height'],
                        'confidence': block['confidence']
                    })
            else:
                filtered_blocks.append(block)
        
        return filtered_blocks

    def _can_merge_blocks(self, block1, block2):
        """Проверяет, можно ли объединить два блока"""
        # Расстояние по горизонтали
        h_distance = abs(block2['x'] - (block1['x'] + block1['width']))
        
        # Расстояние по вертикали
        v_distance = abs(block2['y'] - block1['y'])
        
        # Размеры шрифтов
        font_size1 = block1['height']
        font_size2 = block2['height']
        
        # Если размеры шрифтов сильно отличаются (>30%), не объединяем
        if abs(font_size1 - font_size2) / max(font_size1, font_size2) > 0.3:
            print(f"[DEBUG] Размеры шрифтов сильно отличаются: {font_size1} vs {font_size2}, не объединяем")
            return False
        
        # Блоки можно объединить, если они близко по горизонтали и вертикали
        # И имеют похожий размер шрифта
        can_merge = h_distance <= font_size1 * 1.5 and v_distance <= font_size1 * 0.3
        
        if can_merge:
            print(f"[DEBUG] Объединяем блоки: '{block1['text']}' + '{block2['text']}' (расстояние: h={h_distance}, v={v_distance})")
        else:
            print(f"[DEBUG] НЕ объединяем блоки: '{block1['text']}' + '{block2['text']}' (расстояние: h={h_distance}, v={v_distance})")
        
        return can_merge

    def _merge_block_group(self, blocks):
        """Объединяет группу блоков в один"""
        if len(blocks) == 1:
            return blocks[0]
        
        # Находим границы объединенного блока
        min_x = min(b['x'] for b in blocks)
        min_y = min(b['y'] for b in blocks)
        max_x = max(b['x'] + b['width'] for b in blocks)
        max_y = max(b['y'] + b['height'] for b in blocks)
        
        # Объединяем текст
        merged_text = ' '.join(b['text'] for b in blocks)
        
        # Вычисляем среднюю уверенность
        avg_confidence = sum(b['confidence'] for b in blocks) / len(blocks)
        
        return {
            'text': merged_text,
            'x': min_x,
            'y': min_y,
            'width': max_x - min_x,
            'height': max_y - min_y,
            'confidence': avg_confidence
        }

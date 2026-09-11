import json
import os
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class DataStorage:
    """Сохранение и загрузка данных"""
    
    def __init__(self, storage_dir: str = 'data'):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def save_data(self, data: Dict, filename: str = None) -> str:
        """Сохраняет данные в JSON"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'scraped_{timestamp}.json'
        
        filepath = os.path.join(self.storage_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Данные сохранены: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            return None
    
    def load_last_data(self) -> Dict:
        """Загружает последние сохранённые данные"""
        files = sorted(os.listdir(self.storage_dir), reverse=True)
        json_files = [f for f in files if f.endswith('.json')]
        
        if not json_files:
            return {}
        
        filepath = os.path.join(self.storage_dir, json_files[0])
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            return {}
    
    def compare_with_previous(self, current_data: Dict) -> Dict:
        """Сравнивает текущие данные с предыдущими"""
        previous = self.load_last_data()
        
        if not previous:
            return {'changes': 'first_run', 'data': current_data}
        
        current_products = {p['name']: p for p in current_data.get('products', [])}
        previous_products = {p['name']: p for p in previous.get('products', [])}
        
        changes = {
            'new_items': [],
            'removed_items': [],
            'price_changes': []
        }
        
        # Новые товары
        for name in current_products:
            if name not in previous_products:
                changes['new_items'].append(current_products[name])
        
        # Удалённые товары
        for name in previous_products:
            if name not in current_products:
                changes['removed_items'].append(previous_products[name])
        
        # Изменения цен
        for name in current_products:
            if name in previous_products:
                old_price = previous_products[name].get('price', 0)
                new_price = current_products[name].get('price', 0)
                
                if old_price != new_price:
                    changes['price_changes'].append({
                        'name': name,
                        'old_price': old_price,
                        'new_price': new_price,
                        'diff': new_price - old_price
                    })
        
        return changes
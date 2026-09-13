import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
import logging
import time
from urllib.parse import urljoin, quote_plus
from datetime import datetime

# Отключаем предупреждения о небезопасных SSL-запросах
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChemicalParser:
    def __init__(self, url: str):
        self.url = url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def fetch_page(self, url: str = None) -> Optional[str]:
        """Получает HTML страницы"""
        target_url = url or self.url
        
        # Более реалистичные заголовки
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        try:
            # Добавляем небольшую задержку для реалистичности
            time.sleep(0.5)
            
            # ОТКЛЮЧАЕМ ПРОВЕРКУ SSL (verify=False)
            response = self.session.get(target_url, headers=headers, timeout=15, verify=False)
            response.raise_for_status()
            logger.info(f"Страница успешно получена: {target_url}")
            return response.text
            
        except requests.exceptions.SSLError as e:
            logger.warning(f"SSL ошибка (сертификат истек), продолжаем без проверки: {e}")
            try:
                response = self.session.get(target_url, headers=headers, timeout=15, verify=False)
                response.raise_for_status()
                logger.info(f"Страница успешно получена (без проверки SSL): {target_url}")
                return response.text
            except Exception as e2:
                logger.error(f"Ошибка при получении страницы (повторная попытка): {e2}")
                return None
                
        except requests.exceptions.Timeout as e:
            logger.error(f"Таймаут при получении страницы: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении страницы: {e}")
            return None
    
    def search_products(self, query: str) -> str:
        """Формирует URL поиска товаров по запросу"""
        encoded_query = quote_plus(query)
        search_url = f"https://lenreactiv-shop.ru/?s={encoded_query}&post_type=product"
        logger.info(f"Ищем товары по запросу: {query}")
        return search_url
    
    def parse_products(self, html: str) -> List[Dict]:
        """Парсит товары со страницы"""
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        product_cards = soup.select('.type-product, .product-small')
        logger.info(f"Всего найдено потенциальных карточек: {len(product_cards)}")
        
        for card in product_cards[:20]:
            try:
                name_elem = card.select_one('.title, .woocommerce-loop-product__title, h3')
                price_elem = card.select_one('.price, .woocommerce-Price-amount, bdi')
                image_elem = card.select_one('img')
                
                if not name_elem or not price_elem:
                    continue
                
                name = name_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True)
                price = self._extract_price(price_text)
                
                if price is None:
                    continue
                
                image_url = None
                if image_elem:
                    image_url = image_elem.get('data-src') or image_elem.get('src')
                    if image_url and not image_url.startswith('http'):
                        image_url = urljoin(self.url, image_url)
                
                products.append({
                    'name': name,
                    'price': price,
                    'image_url': image_url,
                    'currency': 'RUB'
                })
                
            except Exception as e:
                logger.warning(f"Ошибка при парсинге одной карточки: {e}")
                continue
        
        logger.info(f"✅ Успешно распарсено товаров: {len(products)}")
        return products
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Извлекает цену из текста"""
        text = text.split('–')[0].split('-')[0]
        digits = re.sub(r'[^\d,.]', '', text)
        digits = digits.replace(',', '.')
        
        try:
            if ' ' in digits:
                digits = digits.replace(' ', '')
            return float(digits)
        except (ValueError, TypeError):
            return None
    
    def download_image(self, image_url: str, save_path: str = 'temp_image.jpg') -> Optional[str]:
        """Скачивает изображение"""
        if not image_url:
            return None
        try:
            response = self.session.get(image_url, timeout=10, verify=False)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Изображение сохранено: {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Ошибка скачивания изображения: {e}")
            return None
    
    def collect_data(self, search_query: str = None) -> Dict:
        """
        Основной метод сбора данных.
        Если передан search_query - ищет товары по запросу, иначе парсит основную страницу.
        """
        if search_query:
            target_url = self.search_products(search_query)
        else:
            target_url = self.url
        
        html = self.fetch_page(target_url)
        if not html:
            return {'error': 'Не удалось получить страницу'}
        
        products = self.parse_products(html)
        
        # Скачиваем первое изображение
        image_path = None
        for product in products:
            if product.get('image_url'):
                image_path = self.download_image(product['image_url'])
                product['image_saved'] = image_path
                break
        
        return {
            'url': target_url,
            'search_query': search_query,
            'products': products,
            'total_items': len(products),
            'image_path': image_path,
            'timestamp': datetime.now().isoformat()
        }
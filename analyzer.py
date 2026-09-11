import logging
from typing import Dict, List
import base64

# Импортируем только основной класс. Никаких сложных объектов Messages!
from gigachat import GigaChat

logger = logging.getLogger(__name__)


class AIAnalyzer:
    def __init__(self, credentials: str):
        # 1. Жесткая очистка от ЛЮБЫХ пробелов, кавычек и переносов строк
        raw_credentials = credentials.strip().replace('"', '').replace("'", "").replace(" ", "").replace("\n", "").replace("\r", "")
        
        # 2. Явное кодирование в Base64 (это то, что требует современный SDK)
        encoded_credentials = base64.b64encode(raw_credentials.encode('utf-8')).decode('utf-8')
        
        logger.info("Инициализирую GigaChat SDK с Base64 ключом...")
        
        # 3. Передаем в SDK именно ЗАКОДИРОВАННЫЙ ключ
        self.giga = GigaChat(
            credentials=encoded_credentials,
            base_url="https://api.giga.chat/v1",
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,
            model="GigaChat-2"
        )
        logger.info("GigaChat SDK инициализирован успешно!")

    def analyze(self, scraped_data: Dict) -> str:
        products = scraped_data.get('products', [])
        if not products:
            return "⚠️ Не удалось собрать данные с сайта."
        
        data_summary = self._prepare_data_summary(products)

        search_query = scraped_data.get('search_query')
        if search_query:
            context_note = f"Пользователь искал товары по запросу: «{search_query}»."
        else:
            context_note = "Это данные из основного каталога."
        
        # Формируем единый текстовый промпт. 
        # Это работает в ЛЮБОЙ версии библиотеки gigachat и избегает ошибок с объектом Messages
        full_prompt = (
            "Ты — аналитик цен для владельца бизнеса по продаже промышленной химии.\n"
            "Задача: сравни полученные данные. Отметь 2-3 самых значимых наблюдения "
            "(заметно низкие/высокие цены, специфические реактивы).\n"
            "Ограничения: Не придумывай цифры. Пиши простым текстом, без markdown.\n"
            "Формат: 2-4 коротких предложения, по-деловому, с конкретными цифрами.\n\n"
            f"Данные с сайта ({scraped_data.get('url', 'unknown')}):\n"
            f"{data_summary}\n"
            f"Всего товаров: {len(products)}\n"
            f"Сформируй краткий аналитический отчёт."
        )
        
        try:
            logger.info("Отправляю запрос на анализ через официальный SDK...")
            
            # Вызываем chat(), передавая просто строку, как в примере из официальной документации!
            response = self.giga.chat(full_prompt)
            
            # Безопасное извлечение текста (работает для разных версий ответа SDK)
            if hasattr(response, 'choices') and response.choices and hasattr(response.choices[0], 'message'):
                report = response.choices[0].message.content.strip()
            elif hasattr(response, 'text'):
                report = response.text.strip()
            else:
                report = str(response).strip()
                
            logger.info("GigaChat анализ завершён успешно!")
            return report
            
        except Exception as e:
            logger.error(f"Критическая ошибка GigaChat: {e}")
            return f"⚠️ Ошибка при анализе данных: {str(e)}"

    def _prepare_data_summary(self, products: List[Dict]) -> str:
        sorted_products = sorted(products, key=lambda x: x.get('price', 0) or 0)
        cheapest = sorted_products[:5]
        expensive = sorted_products[-5:] if len(sorted_products) >= 5 else []
        
        lines = ["Товары (название - цена):"]
        for p in cheapest:
            if p.get('price'):
                lines.append(f"- {p['name']}: {p['price']} ₽")
        
        if expensive and expensive != cheapest:
            lines.append("\nДорогие позиции:")
            for p in expensive:
                if p.get('price'):
                    lines.append(f"- {p['name']}: {p['price']} ₽")
        
        return "\n".join(lines)
import logging
from apscheduler.schedulers.background import BackgroundScheduler

# Импортируем только то, что действительно нужно из bot
from bot import VKBot, get_main_keyboard

from config import VK_TOKEN, VK_GROUP_ID, GIGACHAT_TOKEN, TARGET_URL, ADMIN_USER_ID
from scraper import ChemicalParser
from analyzer import AIAnalyzer
from utils import DataStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

vk_bot = None


def send_scheduled_report():
    """Автоматическая отправка отчёта по расписанию (по умолчанию)"""
    logger.info("🕒 Запуск планового сбора данных...")
    try:
        parser = ChemicalParser(TARGET_URL)
        scraped_data = parser.collect_data()  # Без запроса - парсит основную страницу
        
        if 'error' in scraped_data:
            vk_bot.send_message(ADMIN_USER_ID, f"❌ Ошибка планового сбора: {scraped_data['error']}")
            return
        
        storage = DataStorage()
        storage.save_data(scraped_data)
        
        analyzer = AIAnalyzer(GIGACHAT_TOKEN)
        report = analyzer.analyze(scraped_data)
        
        image_path = scraped_data.get('image_path')
        full_report = f"📅 ЕЖЕДНЕВНЫЙ АВТОМАТИЧЕСКИЙ ОТЧЁТ\n\n{report}"
        
        vk_bot.send_message(ADMIN_USER_ID, full_report, image_path)
        logger.info("✅ Плановый отчёт успешно отправлен!")
        
    except Exception as e:
        logger.error(f"Ошибка в плановом задании: {e}", exc_info=True)


def run_analysis(user_id: int, search_query: str = None):
    """
    Универсальная функция анализа.
    Если search_query=None - парсит основную страницу.
    Если search_query="серебро" - ищет товары со словом "серебро".
    """
    try:
        # 1. Сообщение о начале работы
        if search_query:
            vk_bot.send_message(user_id, f"🔄 Ищу товары по запросу «{search_query}», подождите немного...")
        else:
            vk_bot.send_message(user_id, "🔄 Собираю данные с сайта, подождите немного...")
        
        # 2. Парсинг
        parser = ChemicalParser(TARGET_URL)
        scraped_data = parser.collect_data(search_query=search_query)
        
        if 'error' in scraped_data:
            vk_bot.send_message(user_id, f"❌ Ошибка: {scraped_data['error']}")
            return
        
        # 3. Проверка: нашлись ли товары
        if not scraped_data.get('products'):
            if search_query:
                vk_bot.send_message(user_id, f"😔 По запросу «{search_query}» ничего не найдено. Попробуйте другое название.")
            else:
                vk_bot.send_message(user_id, "😔 На странице не найдено товаров.")
            return
        
        # 4. Сохранение
        storage = DataStorage()
        storage.save_data(scraped_data)
        
        # 5. AI анализ
        analyzer = AIAnalyzer(GIGACHAT_TOKEN)
        report = analyzer.analyze(scraped_data)
        
        # 6. Формирование и отправка отчёта
        image_path = scraped_data.get('image_path')
        
        if search_query:
            header = f"📊 АНАЛИТИЧЕСКИЙ ОТЧЁТ ПО ЗАПРОСУ «{search_query.upper()}»"
        else:
            header = "📊 АНАЛИТИЧЕСКИЙ ОТЧЁТ"
        
        full_report = f"{header}\n\n{report}\n\n🔎 Найдено товаров: {scraped_data.get('total_items', 0)}"
        
        vk_bot.send_message(user_id, full_report, image_path, keyboard=get_main_keyboard())
        
    except Exception as e:
        logger.error(f"Ошибка при обработке: {e}", exc_info=True)
        vk_bot.send_message(user_id, f"⚠️ Произошла ошибка: {str(e)}")


def handle_user_message(user_id: int, message: str):
    """Обработка сообщений от пользователя"""
    logger.info(f"Пользователь {user_id}: {message}")
    
    text = message.strip().lower()
    
    # 1. Команды и тексты кнопок для полного анализа
    if text in ['/анализ', '/analyse', 'анализ', '📊 анализ каталога']:
        run_analysis(user_id, search_query=None)
        
    # 2. Быстрый поиск по кнопке или команде
    elif text in ['/анализ серебро', '🔍 поиск: серебро']:
        run_analysis(user_id, search_query="серебро")
        
    # 3. Помощь
    elif text in ['/помощь', '/help', '/начать', '/start', '❓ помощь']:
        vk_bot.send_welcome(user_id)
        
    # 4. Статус
    elif text in ['/статус', '/status', '⚙️ статус']:
        vk_bot.send_message(
            user_id, 
            "✅ Бот работает нормально. Отправьте /анализ или нажмите кнопку ниже.",
            keyboard=get_main_keyboard()
        )
        
    # 5. ЛЮБОЕ другое сообщение считаем поисковым запросом! 
    # Это позволяет пользователю просто написать "кислота" без слова /анализ
    else:
        run_analysis(user_id, search_query=message.strip())

if __name__ == '__main__':
    logger.info("🚀 Запуск бота...")
    
    vk_bot = VKBot(VK_TOKEN, VK_GROUP_ID)
    
    # === БОНУС: Настройка расписания ===
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_scheduled_report, 'cron', hour=9, minute=0)
    scheduler.start()
    logger.info("⏰ Планировщик задач запущен (ежедневно в 09:00)")
    
    # Запуск прослушивания сообщений
    vk_bot.listen(handle_user_message)
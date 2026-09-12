import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Thread
from flask import Flask

from bot import VKBot, get_main_keyboard
from config import VK_TOKEN, VK_GROUP_ID, GIGACHAT_TOKEN, TARGET_URL, ADMIN_USER_ID
from scraper import ChemicalParser
from analyzer import AIAnalyzer
from utils import DataStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

vk_bot = None


def send_scheduled_report():
    """Автоматическая отправка отчёта по расписанию"""
    logger.info("🕒 Запуск планового сбора данных...")
    try:
        parser = ChemicalParser(TARGET_URL)
        scraped_data = parser.collect_data()
        
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
    """Универсальная функция анализа"""
    try:
        if search_query:
            vk_bot.send_message(user_id, f"🔄 Ищу товары по запросу «{search_query}», подождите немного...")
        else:
            vk_bot.send_message(user_id, "🔄 Собираю данные с сайта, подождите немного...")
        
        parser = ChemicalParser(TARGET_URL)
        scraped_data = parser.collect_data(search_query=search_query)
        
        if 'error' in scraped_data:
            vk_bot.send_message(user_id, f" Ошибка: {scraped_data['error']}")
            return
        
        if not scraped_data.get('products'):
            if search_query:
                vk_bot.send_message(user_id, f"😔 По запросу «{search_query}» ничего не найдено.")
            else:
                vk_bot.send_message(user_id, "😔 На странице не найдено товаров.")
            return
        
        storage = DataStorage()
        storage.save_data(scraped_data)
        
        analyzer = AIAnalyzer(GIGACHAT_TOKEN)
        report = analyzer.analyze(scraped_data)
        
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
    
    if text in ['/анализ', '/analyse', 'анализ', '📊 анализ каталога']:
        run_analysis(user_id, search_query=None)
        
    elif text in ['/анализ серебро', '🔍 поиск: серебро']:
        run_analysis(user_id, search_query="серебро")
        
    elif text in ['/помощь', '/help', '/начать', '/start', '❓ помощь']:
        vk_bot.send_welcome(user_id)
        
    elif text in ['/статус', '/status', '⚙️ статус']:
        vk_bot.send_message(
            user_id, 
            "✅ Бот работает нормально. Отправьте /анализ или нажмите кнопку ниже.",
            keyboard=get_main_keyboard()
        )
        
    else:
        run_analysis(user_id, search_query=message.strip())


# ==================== ГЛАВНЫЙ БЛОК ====================
if __name__ == '__main__':
    logger.info("🚀 Запуск бота...")
    
    # 1. Инициализируем бота
    vk_bot = VKBot(VK_TOKEN, VK_GROUP_ID)
    
    # 2. Настраиваем планировщик
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_scheduled_report, 'cron', hour=9, minute=0)
    scheduler.start()
    logger.info("⏰ Планировщик задач запущен (ежедневно в 09:00)")
    
    # 3. === ЗАПУСКАЕМ FLASK ПЕРЕД БОТОМ ===
    app = Flask(__name__)
    
    @app.route('/')
    def health_check():
        return "Bot is alive and running! 🤖", 200
    
    @app.route('/health')
    def health():
        return {"status": "healthy", "bot": "running"}, 200
    
    def run_flask():
        # Render передает порт в переменной PORT
        port = int(os.environ.get('PORT', 8080))
        # host='0.0.0.0' КРИТИЧЕСКИ важен для Render!
        app.run(host='0.0.0.0', port=port, threaded=True)
    
    # Запускаем Flask в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    logger.info(f"🌐 Health-check сервер запущен на порту {os.environ.get('PORT', 8080)}")
    
    # 4. Только ПОСЛЕ запуска Flask запускаем бота
    logger.info("🤖 Запуск VK LongPoll...")
    vk_bot.listen(handle_user_message)
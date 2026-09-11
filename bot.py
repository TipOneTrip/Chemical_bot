import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import logging
import os

logger = logging.getLogger(__name__)


def get_main_keyboard():
    """Создает клавиатуру точно по рабочему образцу из твоего бота"""
    keyboard = VkKeyboard(one_time=False)
    
    keyboard.add_button('📊 Анализ каталога', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    
    keyboard.add_button('🔍 Поиск: Серебро', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    
    keyboard.add_button('❓ Помощь', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('⚙️ Статус', color=VkKeyboardColor.SECONDARY)
    
    # Возвращаем сам объект VkKeyboard, а не строку!
    return keyboard


class VKBot:
    """VK бот для отправки отчётов"""
    
    def __init__(self, token: str, group_id: str):
        self.vk = vk_api.VkApi(token=token)
        self.longpoll = VkLongPoll(self.vk)
        self.group_id = group_id
        logger.info("VK бот инициализирован")
    
    def send_message(self, user_id: int, text: str, image_path: str = None, keyboard=None):
        """Отправляет сообщение, используя проверенный метод get_keyboard()"""
        message_data = {
            'user_id': user_id,
            'message': text,
            'random_id': get_random_id()
        }
        
        # ВАЖНО: вызываем get_keyboard() у объекта VkKeyboard, как в твоем рабочем примере
        if keyboard is not None:
            message_data['keyboard'] = keyboard.get_keyboard()
        
        if image_path and os.path.exists(image_path):
            try:
                upload = vk_api.upload.VkUpload(self.vk)
                photo = upload.photo_messages(
                    photos=image_path,
                    peer_id=user_id
                )
                
                if photo:
                    photo_id = f"photo{photo[0]['owner_id']}_{photo[0]['id']}"
                    message_data['attachment'] = photo_id
                    logger.info(f"Изображение прикреплено: {image_path}")
            except Exception as e:
                logger.error(f"Ошибка при загрузке изображения: {e}")
        
        try:
            self.vk.method('messages.send', message_data)
            logger.info(f"Сообщение отправлено пользователю {user_id}")
        except vk_api.exceptions.ApiError as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
    
    def send_welcome(self, user_id: int):
        """Приветственное сообщение с клавиатурой"""
        welcome_text = """
👋 Привет! Я бот для мониторинга цен на промышленную химию.

📊 Мои возможности:
• Парсинг цен с сайтов конкурентов
• AI-анализ рыночной ситуации
• Поиск товаров по названию
• Автоматические отчёты по расписанию

💡 Совет: используйте кнопки ниже или просто напишите название товара, например: 
гидроксид натрия
"""
        self.send_message(user_id, welcome_text.strip(), keyboard=get_main_keyboard())
    
    def listen(self, callback):
        """Слушает сообщения от пользователей"""
        logger.info("Бот слушает сообщения...")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.from_user and event.to_me:
                text = event.text.strip().lower()
                
                if text in ['/начать', '/start']:
                    self.send_welcome(event.user_id)
                else:
                    callback(event.user_id, event.text)
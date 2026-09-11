import os
from dotenv import load_dotenv
load_dotenv()

VK_TOKEN = os.getenv('VK_TOKEN')
VK_GROUP_ID = os.getenv('VK_GROUP_ID')
GIGACHAT_TOKEN = os.getenv('GIGACHAT_TOKEN')
TARGET_URL = os.getenv('TARGET_URL', 'https://lenreactiv-shop.ru/cat/reaktivy/soedineniya-zheleza/')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))
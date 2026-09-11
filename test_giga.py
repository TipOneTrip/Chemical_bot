import requests
import base64
import uuid
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# !!! ВСТАВЬ СЮДА СВОЮ СТРОКУ ИЗ .env (Client_ID:Client_Secret) !!!
# Пример: "a1b2c3d4... : x9y8z7..."
CREDENTIALS = "01a0869e-8455-7de0-a1f8-0d108ad0f6b1:d74f412d-1b17-44fe-a7c6-be1d226e05af"

# Агрессивная очистка от любых пробелов и невидимых символов (частая причина ошибки 400!)
CREDENTIALS = CREDENTIALS.replace(" ", "").replace("\n", "").replace("\r", "")

base_url = "https://ngw.devices.sberbank.ru:9443/api/v2"

print("🔄 1. Получаем токен...")
auth_bytes = CREDENTIALS.encode('utf-8')
base64_auth = base64.b64encode(auth_bytes).decode('utf-8')

token_headers = {
    'Authorization': f'Basic {base64_auth}',
    'RqUID': str(uuid.uuid4()),
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json'
}

token_resp = requests.post(
    f"{base_url}/oauth", 
    headers=token_headers, 
    data={'scope': 'GIGACHAT_API_CORP'}, # Если ты юрлицо, поменяй на GIGACHAT_API_CORP
    verify=False
)

print(f"   Статус токена: {token_resp.status_code}")
if token_resp.status_code != 200:
    print(f"   ❌ Ошибка токена: {token_resp.text}")
else:
    token = token_resp.json()['access_token']
    print("   ✅ Токен получен успешно!")

    print("\n🔄 2. Отправляем тестовый запрос к чату...")
    chat_headers = {
        'Authorization': f'Bearer {token}',
        'RqUID': str(uuid.uuid4()),
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "user", "content": "Напиши слово Тест"}
        ],
        "temperature": 0.7,
        "max_tokens": 10,
        "n": 1
    }

    chat_resp = requests.post(
        f"{base_url}/chat/completions", 
        headers=chat_headers, 
        json=payload, 
        verify=False
    )
    
    print(f"   Статус чата: {chat_resp.status_code}")
    if chat_resp.status_code == 200:
        print(f"   ✅ Ответ ИИ: {chat_resp.json()['choices'][0]['message']['content']}")
    else:
        print(f"   ❌ Ошибка чата: {chat_resp.text}")
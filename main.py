import time
import requests
import pymailtm
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Ваш Telegram токен
TOKEN = '7505320830:AAFD9Wt9dvO1vTqPqa4VEvdxZbiDoAjbBqI'

# Словарь для хранения почтовых ящиков пользователей
user_emails = {}

# Функция для обработки команды /get
async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    email = create_temp_email()  # Создаем временную почту
    user_emails[user_id] = email
    
    # Отправляем пользователю временную почту
    await update.message.reply_text(f'Ваша временная почта: {email}')

    # Теперь запускаем процесс получения тестового кода
    await update.message.reply_text("Процесс получения тестового кода начался...")
    await get_vpn_code(email, user_id)

def create_temp_email():
    """Функция для создания временной почты с использованием mail.tm"""
    client = pymailtm.Client()
    email = client.create_email()
    return email

async def get_vpn_code(email, user_id):
    """Функция для получения тестового кода через сайт HideMyName"""
    demo_url = 'https://hidenx.name/demo/'
    session = requests.Session()

    # Заполняем почтовый адрес на форме
    payload = {'email': email}
    response = session.post(demo_url, data=payload)

    # Проверяем, что перенаправление прошло на success страницу
    if response.url == 'https://hidenx.name/demo/success':
        print("Redirected to success page")

        # Ожидаем получения письма с подтверждением
        await wait_for_email_confirmation(email, user_id)

        # После подтверждения почты ждем код
        await get_code_from_email(email, user_id)

async def wait_for_email_confirmation(email, user_id):
    """Функция для ожидания письма с подтверждением"""
    client = pymailtm.Client()

    while True:
        emails = client.get_inbox(email)
        for message in emails:
            if 'Подтвердите e-mail' in message['subject']:
                # Найдено письмо с подтверждением, переходим по ссылке
                confirmation_link = message['text'].split("href=\"")[1].split("\"")[0]
                confirmation_response = requests.get(confirmation_link)
                if confirmation_response.status_code == 200:
                    print("Email confirmed")
                    return
        time.sleep(5)  # Проверяем почту каждую секунду

async def get_code_from_email(email, user_id):
    """Функция для получения тестового кода из письма"""
    client = pymailtm.Client()

    while True:
        emails = client.get_inbox(email)
        for message in emails:
            if 'Ваш код для тестового доступа' in message['subject']:
                # Ищем тестовый код в теле письма
                if 'Ваш тестовый код:' in message['text']:
                    code = message['text'].split("Ваш тестовый код: ")[1].strip()
                    print(f"Получен код: {code}")
                    await send_code_to_user(code, user_id)
                    return
        time.sleep(5)  # Проверяем почту каждую секунду

async def send_code_to_user(code, user_id):
    """Отправка кода пользователю в Telegram"""
    from telegram import Bot
    bot = Bot(token=TOKEN)

    await bot.send_message(user_id, f"Ваш тестовый код: {code}")

# Основная функция
def main():
    # Создаем объект Application для работы с ботом
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчик команды /get
    application.add_handler(CommandHandler("get", get_code))

    # Запускаем бота в режиме опроса
    application.run_polling()

if __name__ == '__main__':
    main()

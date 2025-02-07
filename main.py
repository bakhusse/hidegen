import os
import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ApplicationBuilder
from bs4 import BeautifulSoup
from pymailtm import MailTm
import requests
import random
import string
import time

# Убедитесь, что директория для базы данных MailTm существует
os.makedirs(os.path.expanduser("~/.pymailtm"), exist_ok=True)

# Инициализация клиента для работы с Mail.tm
mail_client = MailTm()

def generate_username(length=8):
    """Генерация случайного имени пользователя."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def get_available_domains():
    """Получение списка доступных доменов с помощью API Mail.tm."""
    try:
        response = requests.get("https://api.mail.tm/domains")
        if response.status_code == 200:
            data = response.json()
            return [domain['domain'] for domain in data['hydra:member']]
        else:
            print(f"Не удалось получить список доменов. Код ответа: {response.status_code}")
            return []
    except Exception as e:
        print(f"Ошибка при получении доменов: {e}")
        return []

def create_email():
    """Создание почты с помощью API Mail.tm."""
    try:
        domains = get_available_domains()
        if not domains:
            print("Список доменов пуст.")
            return None
        
        domain = domains[0]
        username = generate_username()
        address = f"{username}@{domain}"
        password = generate_username(12)

        # Данные для создания аккаунта
        payload = {
            "address": address,
            "password": password
        }

        response = requests.post("https://api.mail.tm/accounts", json=payload)
        if response.status_code == 201:
            print(f"Почта успешно создана: {address}")
            print(f"Результат create_email: {address}, {password}")
            return address, password
        elif response.status_code == 422:
            print("Ошибка 422: Некорректные данные (например, имя пользователя или домен).")
            print(f"Ответ сервера: {response.json()}")
        else:
            print(f"Не удалось создать почту. Код ответа: {response.status_code}")
            print(f"Ответ сервера: {response.text}")
        return None
    except Exception as e:
        print(f"Ошибка при создании почты: {e}")
        return None

def get_token(email, password):
    """Получение токена для авторизации."""
    print(f"Получение токена для: {email}")
    print(f"Используемый пароль: {password}")
    payload = {"address": email, "password": password}

    try:
        response = requests.post("https://api.mail.tm/token", json=payload)
        if response.status_code == 200:
            token = response.json().get("token")
            print(f"Токен успешно получен: {token}")
            return token
        else:
            print(f"Ошибка авторизации: {response.status_code}")
            print(f"Ответ сервера: {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка при запросе токена: {e}")
        return None


def get_inbox(email, password, retries=20, delay=10):
    token = get_token(email, password)
    if not token:
        print("Не удалось авторизоваться. Проверьте почту и пароль.")
        return []

    headers = {"Authorization": f"Bearer {token}"}

    for attempt in range(retries):
        print(f"Попытка {attempt + 1}/{retries} получить письма...")
        response = requests.get("https://api.mail.tm/messages", headers=headers)
        if response.status_code == 200:
            messages = response.json().get("hydra:member", [])
            if messages:
                print(f"Найдено {len(messages)} писем.")
                for message in messages:
                    print(f"Содержимое письма: {message}")
                return messages
        else:
            print(f"Ошибка при получении писем: {response.status_code}")
            print(f"Ответ сервера: {response.text}")

        time.sleep(delay)

    print("Не удалось получить письма за указанное время.")
    return []

        
demo_url = 'https://hidenx.name/demo/'

def register_on_site(email):
    """Регистрация на сайте с использованием указанной почты."""
    try:
        # Создаем сессию
        session = requests.Session()
        
        def load_page(url):
            """Функция загрузки страницы."""
            response = session.get(url)
            if response.status_code != 200:
                print(f"Не удалось загрузить страницу {url}. Код ответа: {response.status_code}")
                return None
            return BeautifulSoup(response.text, 'html.parser')

        # Загружаем основную страницу
        soup = load_page(demo_url)
        if not soup:
            return None

        # Функция для поиска поля ввода почты
        def find_email_field(soup):
            return soup.find('input', {'name': 'demo_mail'})

        # Находим поле ввода почты
        email_field = find_email_field(soup)
        if not email_field:
            print("Поле для ввода почты не найдено. Переход на резервный URL.")
            
            # Переход на резервный URL
            reset_soup = load_page('https://hidenx.name/demo/reset/')
            if not reset_soup:
                return None

            # Возвращение на основную страницу
            print("Возвращение на основную страницу.")
            soup = load_page(demo_url)
            if not soup:
                return None

            # Повторный поиск поля ввода
            email_field = find_email_field(soup)

        # Если поле не найдено после всех попыток, завершить процесс
        if not email_field:
            print("Поле для ввода почты не найдено даже после повторного перехода.")
            return None

        # Находим все скрытые поля формы
        hidden_inputs = soup.find_all('input', type='hidden')
        form_data = {input['name']: input.get('value', '') for input in hidden_inputs}

        # Добавляем поле для ввода почты
        form_data['demo_mail'] = email

        # Отправляем POST-запрос с данными формы
        response = session.post(demo_url, data=form_data)

        # Проверяем результат
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            title_text = soup.find('title').get_text(strip=True)

            if "Ваш код выслан на почту" in title_text:
                print(f"Почта {email} успешно отправлена.")
                return email
            else:
                print(f"Ответ сервера не подтверждает успешную отправку: {title_text}")
                return None
        else:
            print(f"Ошибка при отправке почты. Код ответа: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при регистрации: {e}")
        return None

import re
from bs4 import BeautifulSoup

def confirm_email(email, password):
    try:
        token = get_token(email, password)
        if not token:
            print("Не удалось авторизоваться. Проверьте почту и пароль.")
            return False

        headers = {"Authorization": f"Bearer {token}"}
        session = requests.Session()  # Создаём сессию для запросов

        for _ in range(20):  # 20 попыток по 8 секунд
            response = requests.get("https://api.mail.tm/messages", headers=headers)
            if response.status_code == 200:
                messages = response.json().get("hydra:member", [])
                if not messages:
                    print("Писем нет, ожидаем...")
                    time.sleep(8)
                    continue

                print(f"Найдено {len(messages)} писем.")
                for message in messages:
                    # Извлекаем ID письма
                    message_id = message["id"]
                    print(f"Обрабатываем письмо с ID: {message_id}")

                    # Извлекаем содержимое письма с помощью GET /messages/{id}
                    email_response = requests.get(f"https://api.mail.tm/messages/{message_id}", headers=headers)
                    if email_response.status_code == 200:
                        email_data = email_response.json()

                        # Извлекаем HTML из письма
                        html_body = email_data.get("html", [""])[0]

                        # Ищем ссылку в HTML по маске https://hidemy.esclick.me/
                        confirm_link = None
                        if html_body:
                            soup = BeautifulSoup(html_body, "html.parser")
                            # Находим все теги <a> с нужным href
                            links = soup.find_all("a", href=re.compile(r"^https://hidemy\.esclick\.me/"))
                            for link in links:
                                # Проверяем, находится ли ссылка в теге <span> с текстом "Подтвердить"
                                parent = link.find_parent("span")
                                if parent and "Подтвердить" in parent.text:
                                    confirm_link = link["href"]
                                    break

                        if confirm_link:
                            print(f"Ссылка для подтверждения: {confirm_link}")

                            # Переход по ссылке для подтверждения через сессию
                            confirm_response = session.get(confirm_link)
                            print(f"Ответ сервера после перехода по ссылке: {confirm_response.status_code}")

                            if confirm_response.status_code == 200:
                                print("Переход по ссылке для подтверждения успешен.")
                                return True
                            else:
                                print(f"Ошибка при подтверждении: {confirm_response.status_code}")
                        else:
                            print("Не удалось найти ссылку для подтверждения в письме.")
                    else:
                        print(f"Ошибка при получении данных письма: {email_response.status_code}")
                print("Ссылки на подтверждение пока нет, ожидаем...")
                time.sleep(8)
            else:
                print(f"Ошибка при получении писем. Код ответа: {response.status_code}")
                return False

        print("Письмо не пришло в течение 160 секунд.")
        return False
    except Exception as e:
        print(f"Ошибка при подтверждении почты: {e}")
        return False
        
def get_test_code(email, password):
    try:
        token = get_token(email, password)
        if not token:
            print("Не удалось авторизоваться. Проверьте почту и пароль.")
            return None

        headers = {"Authorization": f"Bearer {token}"}
        session = requests.Session()

        for _ in range(20):  # 20 попыток по 8 секунд
            response = requests.get("https://api.mail.tm/messages", headers=headers)
            if response.status_code == 200:
                messages = response.json().get("hydra:member", [])
                if not messages:
                    print("Писем нет, ожидаем...")
                    time.sleep(8)
                    continue

                for message in messages:
                    message_id = message["id"]
                    subject = message["subject"]

                    if "Ваш код для тестового доступа к сервису" in subject:
                        print(f"Письмо с тестовым кодом найдено. ID: {message_id}")

                        # Получаем содержимое письма
                        email_response = requests.get(f"https://api.mail.tm/messages/{message_id}", headers=headers)
                        if email_response.status_code == 200:
                            email_data = email_response.json()
                            intro = email_data.get("intro", "")

                            # Извлекаем тестовый код
                            test_code = intro.split(":")[1].strip()
                            print(f"Тестовый код: {test_code}")

                            # Возврат найденного тестового кода и выход из функции
                            return test_code
                        else:
                            print(f"Ошибка при получении данных письма: {email_response.status_code}")
            else:
                print(f"Ошибка при получении писем. Код ответа: {response.status_code}")
                return None

        print("Письмо с тестовым кодом не пришло в течение 160 секунд.")
        return None
    except Exception as e:
        print(f"Ошибка при получении тестового кода: {e}")
        return None


async def start(update: Update, context):
    await update.message.reply_text("Привет! Я могу регистрировать для тебя тестовые коды для hidemyname VPN. Отправь команду /get, чтобы получить тестовый код.")

async def get_test_code_telegram(update: Update, context):
    try:
        # Сообщение о времени ожидания
        await update.message.reply_text("Ваш код будет готов примерно через 2 минуты. Пожалуйста, подождите...")

        # Генерация почты и пароля
        email, password = create_email()
        if not email or not password:
            await update.message.reply_text("Ошибка при создании почты. Попробуйте позже.")
            return

        # Отправка почты, пароля и ссылки пользователю
        await update.message.reply_text(
            f"Почта: {email}\n"
            f"Пароль: {password}\n"
            f"Вы можете проверить свою почту здесь: https://mail.tm/"
        )

        print(f"Созданная почта: {email}")
        print(f"Используемый пароль: {password}")

        # Регистрация на сайте
        if not register_on_site(email):
            await update.message.reply_text("Ошибка при регистрации на сайте.")
            return

        # Подтверждение почты
        if not confirm_email(email, password):
            await update.message.reply_text("Не удалось подтвердить почту.")
            return

        # Получение тестового кода
        test_code = get_test_code(email, password)
        if test_code:
            await update.message.reply_text(f"Ваш тестовый код: {test_code}")
        else:
            await update.message.reply_text("Не удалось получить тестовый код.")
    except Exception as e:
        print(f"Ошибка в процессе получения тестового кода: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

def main():
    TELEGRAM_TOKEN = '7505320830:AAFa_2WvRVEo_I1YkiO-RQDS2FwGtLJY1po'

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get", get_test_code_telegram))

    application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())

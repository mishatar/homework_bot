import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
import telegram.ext
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('chat_id')

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s',
    level=logging.INFO)

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправляет сообщение в телеграмм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f"Сообщение {message} отправлено")
    except Exception:
        logging.error('Не удалось отправить сообщение')
        raise Exception('Не удалось отправить сообщение')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
    except requests.exceptions.RequestException as ex:
        raise Exception(f"Ошибка при запросе к API: {ex}")
    if homework_statuses.status_code != HTTPStatus.OK:
        raise requests.exceptions.StatusCodeException(
            'Неверный код ответа API'
        )
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API."""
    if not isinstance(response, dict):
        raise TypeError('Ответ от API не является словарем')
    if 'homeworks' not in response:
        raise TypeError('Ключ "homeworks" не найден')
    if not isinstance(response['homeworks'], list):
        raise TypeError('В ключе "homeworks" нет списка')
    homeworks = response.get('homeworks')
    if not homeworks:
        raise KeyError('В ключе "homeworks" нет значений')
    return homeworks


def parse_status(homework):
    """Извлекает информацию о статусе домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутсвует ключ "homework_name" в ответе API')
    homework_name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        logging.error('Неверный статус домашки')
        raise NameError('Неверный статус домашки')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    if not check_tokens():
        logging.critical(
            'Отсутсвует одна или несколько переменных окружения')
        raise Exception('Отсутсвует одна или несколько переменных окружения')

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date', timestamp)
            homework = check_response(response)
            message = parse_status(homework[0])
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

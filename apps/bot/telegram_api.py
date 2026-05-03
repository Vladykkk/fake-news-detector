"""Обгортка для Telegram Bot API."""
import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramAPI:
    """Клас для взаємодії з Telegram Bot API."""

    BASE_URL = 'https://api.telegram.org/bot{token}/{method}'

    @classmethod
    def _get_url(cls, method: str) -> str:
        return cls.BASE_URL.format(token=settings.TELEGRAM_BOT_TOKEN, method=method)

    @classmethod
    def send_message(
        cls,
        chat_id: int,
        text: str,
        result_id: int = None,
        parse_mode: str = 'HTML',
    ):
        """Надіслати повідомлення в Telegram чат."""
        token = settings.TELEGRAM_BOT_TOKEN
        if not token or token == 'placeholder-token':
            logger.warning("Telegram bot token not configured")
            return None

        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
        }

        # Додати кнопки зворотного зв'язку
        if result_id:
            payload['reply_markup'] = json.dumps({
                'inline_keyboard': [[
                    {
                        'text': '👍 Правильно',
                        'callback_data': f'feedback_correct_{result_id}',
                    },
                    {
                        'text': '👎 Помилка',
                        'callback_data': f'feedback_wrong_{result_id}',
                    },
                ]]
            })

        try:
            response = requests.post(
                cls._get_url('sendMessage'),
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return None

    @classmethod
    def set_webhook(cls, url: str, secret_token: str = None):
        """Встановити webhook URL для бота."""
        payload = {'url': url}
        if secret_token:
            payload['secret_token'] = secret_token

        try:
            response = requests.post(
                cls._get_url('setWebhook'),
                json=payload,
                timeout=10,
            )
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to set webhook: {e}")
            return None

"""Telegram bot handlers — class-based approach."""
import logging
from django.conf import settings

from .telegram_api import TelegramAPI
from .formatters import format_result_message

logger = logging.getLogger(__name__)


class CommandHandler:
    """Обробник команд Telegram (/start, /help, /stats)."""

    COMMANDS = {}

    @classmethod
    def handle(cls, message: dict):
        text = message.get('text', '')
        chat_id = message['chat']['id']
        command = text.split()[0].split('@')[0]  # /start@botname → /start

        handler = cls.COMMANDS.get(command, cls._unknown)
        handler(chat_id)

    @classmethod
    def _start(cls, chat_id: int):
        TelegramAPI.send_message(chat_id, (
            "<b>IPSO Detector Bot</b>\n\n"
            "Я аналізую тексти на ознаки російських ІПСО "
            "(інформаційно-психологічних операцій).\n\n"
            "<b>Як користуватися:</b>\n"
            "1. Надішліть або перешліть текст повідомлення\n"
            "2. Отримайте результат аналізу за декілька секунд\n\n"
            "<b>Команди:</b>\n"
            "/start — Почати роботу\n"
            "/help — Довідка\n"
            "/stats — Статистика бота"
        ))

    @classmethod
    def _help(cls, chat_id: int):
        TelegramAPI.send_message(chat_id, (
            "<b>Довідка IPSO Detector</b>\n\n"
            "Система аналізує текст за трьома модулями:\n"
            "1. <b>Наративи</b> — AI-класифікація за 7 типами ІПСО\n"
            "2. <b>Риторика</b> — виявлення маніпулятивних технік\n"
            "3. <b>Подібність</b> — порівняння з базою відомих ІПСО\n\n"
            "Результат: підсумковий бал від 0% до 100%\n"
            "- <b>0-35%</b> — Безпечно\n"
            "- <b>35-70%</b> — Підозрілий\n"
            "- <b>70-100%</b> — ІПСО виявлено\n\n"
            "Мінімальна довжина тексту: 30 символів."
        ))

    @classmethod
    def _stats(cls, chat_id: int):
        from apps.core.models import AnalysisResult, Feedback

        total = AnalysisResult.objects.filter(source='telegram').count()
        ipso = AnalysisResult.objects.filter(source='telegram', verdict='ipso').count()
        suspicious = AnalysisResult.objects.filter(source='telegram', verdict='suspicious').count()
        safe = AnalysisResult.objects.filter(source='telegram', verdict='safe').count()
        feedbacks = Feedback.objects.count()

        TelegramAPI.send_message(chat_id, (
            "<b>Статистика бота</b>\n\n"
            f"Всього аналізів: {total}\n"
            f"  ІПСО: {ipso}\n"
            f"  Підозрілий: {suspicious}\n"
            f"  Безпечно: {safe}\n\n"
            f"Відгуків отримано: {feedbacks}"
        ))

    @classmethod
    def _unknown(cls, chat_id: int):
        TelegramAPI.send_message(chat_id, "Невідома команда. Спробуйте /help")


# Реєстрація команд
CommandHandler.COMMANDS = {
    '/start': CommandHandler._start,
    '/help': CommandHandler._help,
    '/stats': CommandHandler._stats,
}


class MessageHandler:
    """Обробник текстових повідомлень — запуск аналізу."""

    @classmethod
    def handle(cls, message: dict):
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        username = message.get('from', {}).get('username', '')
        message_id = message.get('message_id', 0)

        if len(text) < 30:
            TelegramAPI.send_message(
                chat_id, "Текст занадто короткий. Мінімум 30 символів."
            )
            return

        # Підтвердження прийому
        TelegramAPI.send_message(chat_id, "🔍 Аналізую текст...")

        # Запуск аналізу
        if settings.USE_CELERY:
            from apps.analyzer.tasks import analyze_content_task
            analyze_content_task.delay(
                text=text,
                source='telegram',
                chat_id=chat_id,
                message_id=message_id,
                username=username,
            )
        else:
            cls._analyze_sync(text, chat_id, message_id, username)

    @classmethod
    def _analyze_sync(cls, text, chat_id, message_id, username):
        from apps.analyzer.pipeline import analyze_text
        from apps.core.models import TelegramAnalysis

        result = analyze_text(text, source='telegram')
        TelegramAnalysis.objects.create(
            result=result,
            chat_id=chat_id,
            message_id=message_id,
            username=username,
        )
        response_text = format_result_message(result)
        TelegramAPI.send_message(chat_id, response_text, result_id=result.id)


class CallbackHandler:
    """Обробник inline callback queries (кнопки зворотного зв'язку)."""

    @classmethod
    def handle(cls, callback_query: dict):
        data = callback_query.get('data', '')
        chat_id = callback_query['message']['chat']['id']

        if data.startswith('feedback_'):
            cls._handle_feedback(data, chat_id)

    @classmethod
    def _handle_feedback(cls, data: str, chat_id: int):
        parts = data.split('_')
        if len(parts) != 3:
            return

        feedback_type = parts[1]  # correct / wrong
        try:
            result_id = int(parts[2])
        except ValueError:
            return

        from apps.core.models import Feedback
        Feedback.objects.create(
            result_id=result_id,
            feedback_type=feedback_type,
            chat_id=chat_id,
        )
        TelegramAPI.send_message(chat_id, "Дякуємо за відгук! 🙏")

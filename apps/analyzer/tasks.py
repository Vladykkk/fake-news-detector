"""
Celery tasks for asynchronous analysis.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def analyze_content_task(self, text: str, source: str = 'api', **kwargs):
    """
    Async Celery task to run the full analysis pipeline.

    Args:
        text: Raw text to analyze
        source: Origin ('telegram', 'api', 'web')
        kwargs: Extra context (chat_id, message_id, username for Telegram)

    Returns:
        dict with analysis result id and verdict
    """
    try:
        from .pipeline import analyze_text
        result = analyze_text(text, source=source)

        # If this is a Telegram request, create TelegramAnalysis record
        if source == 'telegram' and kwargs.get('chat_id'):
            from apps.core.models import TelegramAnalysis
            TelegramAnalysis.objects.create(
                result=result,
                chat_id=kwargs['chat_id'],
                message_id=kwargs.get('message_id', 0),
                username=kwargs.get('username', ''),
            )

            # Send result back to Telegram
            _send_telegram_result(result, kwargs['chat_id'])

        return {
            'result_id': result.id,
            'verdict': result.verdict,
            'score': result.final_score,
        }

    except Exception as exc:
        logger.error(f"Analysis task failed: {exc}")
        raise self.retry(exc=exc)


def _send_telegram_result(result, chat_id: int):
    """Send formatted analysis result back to Telegram user."""
    try:
        from apps.bot.formatters import format_result_message
        from apps.bot.bot_instance import send_message

        message = format_result_message(result)
        send_message(chat_id, message)
    except Exception as e:
        logger.error(f"Failed to send Telegram result: {e}")

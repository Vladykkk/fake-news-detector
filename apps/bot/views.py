"""Telegram webhook endpoint — class-based view."""
import json
import logging

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .handlers import CommandHandler, MessageHandler, CallbackHandler

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(View):
    """
    POST /bot/webhook/
    Приймає оновлення від Telegram через webhook.
    """
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        # Перевірка webhook secret
        secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        expected = settings.TELEGRAM_WEBHOOK_SECRET
        if expected and secret != expected:
            logger.warning("Invalid webhook secret")
            return HttpResponse(status=403)

        try:
            update = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Callback query (inline кнопки зворотного зв'язку)
        if 'callback_query' in update:
            CallbackHandler.handle(update['callback_query'])
            return JsonResponse({'ok': True})

        # Звичайне повідомлення
        message = update.get('message')
        if not message:
            return JsonResponse({'ok': True})

        text = message.get('text', '')

        # Команди
        if text.startswith('/'):
            CommandHandler.handle(message)
            return JsonResponse({'ok': True})

        # Текстове повідомлення → аналіз
        MessageHandler.handle(message)
        return JsonResponse({'ok': True})

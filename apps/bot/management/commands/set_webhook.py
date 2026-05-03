"""
Management command to set/delete Telegram webhook.

Usage:
    python manage.py set_webhook https://your-domain.com/bot/webhook/
    python manage.py set_webhook --delete
    python manage.py set_webhook --info
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Set, delete, or check Telegram bot webhook'

    def add_arguments(self, parser):
        parser.add_argument('url', nargs='?', default=None, help='Webhook URL')
        parser.add_argument('--delete', action='store_true', help='Delete current webhook')
        parser.add_argument('--info', action='store_true', help='Show current webhook info')

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token or token == 'placeholder-token':
            raise CommandError('TELEGRAM_BOT_TOKEN not configured in .env')

        base = f'https://api.telegram.org/bot{token}'

        if options['info']:
            resp = requests.get(f'{base}/getWebhookInfo', timeout=10).json()
            result = resp.get('result', {})
            url = result.get('url', '(not set)')
            pending = result.get('pending_update_count', 0)
            last_error = result.get('last_error_message', '—')
            self.stdout.write(
                f"URL: {url}\n"
                f"Pending updates: {pending}\n"
                f"Last error: {last_error}"
            )
            return

        if options['delete']:
            resp = requests.post(
                f'{base}/deleteWebhook', json={'drop_pending_updates': True}, timeout=10,
            ).json()
            if resp.get('ok'):
                self.stdout.write(self.style.SUCCESS('Webhook deleted.'))
            else:
                self.stderr.write(f"Error: {resp}")
            return

        url = options['url']
        if not url:
            raise CommandError('Provide a webhook URL or use --delete / --info')

        payload = {'url': url}
        secret = settings.TELEGRAM_WEBHOOK_SECRET
        if secret:
            payload['secret_token'] = secret

        resp = requests.post(f'{base}/setWebhook', json=payload, timeout=10).json()
        if resp.get('ok'):
            self.stdout.write(self.style.SUCCESS(f'Webhook set to: {url}'))
        else:
            self.stderr.write(f"Error: {resp}")

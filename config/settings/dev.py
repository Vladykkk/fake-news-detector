from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ['*']
USE_CELERY = False  # Run tasks synchronously in dev

# PostgreSQL via Docker Compose
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='ipso_detector'),
        'USER': config('DB_USER', default='ipso_user'),
        'PASSWORD': config('DB_PASSWORD', default='ipso_password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

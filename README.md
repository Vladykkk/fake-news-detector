# IPSO Detector

Розподілена інформаційна система для виявлення російських інформаційно-психологічних
операцій (ІПСО) у відкритих текстових повідомленнях з використанням штучного інтелекту.

Дипломна робота бакалавра — Рибак Владислав Ярославович, НУ «Львівська політехніка», група РІ-31сп, 2026.

## Архітектура

Система складається з трьох модулів аналізу, об'єднаних в ансамблеву оцінку:

| Модуль       | Метод                                            | Вага |
|--------------|--------------------------------------------------|------|
| Наративи     | LLM (OpenRouter API) — zero-shot класифікація    | 0.40 |
| Риторика     | Rule-based regex patterns (UK + EN)              | 0.30 |
| Подібність   | sentence-transformers + cosine similarity        | 0.30 |

Фінальна оцінка: `S = 0.40 × narrative + 0.30 × rhetoric + 0.30 × similarity`

Пороги вердикту:
- `safe` — S < 0.35 (безпечний)
- `suspicious` — 0.35 ≤ S < 0.70 (підозрілий)
- `ipso` — S ≥ 0.70 (ІПСО виявлено)

## Технології

- **Python 3.10+**
- **Django 4.2 LTS** + **Django REST Framework** (ViewSets, class-based views)
- **Celery 5** + **Redis** — асинхронна обробка задач
- **PostgreSQL** (prod) / **SQLite** (dev)
- **sentence-transformers** (`paraphrase-multilingual-MiniLM-L12-v2`)
- **OpenRouter API** — для LLM-класифікації наративів
- **python-telegram-bot** — інтеграція з Telegram Bot API
- **HTMX + Bootstrap 5** — веб-інтерфейс без SPA-фреймворку

## Структура проєкту

```
ipso-detector-api/
├── config/              # Django settings (base/dev/prod), URLs, Celery
├── apps/
│   ├── core/            # Моделі БД: AnalysisResult, KnownNarrative, Feedback
│   ├── analyzer/        # Аналітичний pipeline (translator, rhetoric, narrative, similarity)
│   ├── api/             # REST API — ViewSets, serializers
│   ├── bot/             # Telegram webhook handlers
│   └── web/             # HTMX dashboard з class-based views
├── templates/web/       # Django-шаблони
├── data/narratives/     # JSON seed для відомих наративів
├── requirements/        # base.txt, dev.txt, prod.txt
└── manage.py
```

## Запуск проєкту

1. **Клонувати репозиторій**
   ```bash
   git clone <repo-url>
   cd ipso-detector-api
   ```

2. **Створити virtualenv та встановити залежності**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements/dev.txt
   ```

3. **Налаштувати `.env`** (скопіювати з `.env.example`)
   ```env
   DEBUG=True
   SECRET_KEY=your-secret-key
   OPENROUTER_API_KEY=your-openrouter-key
   TELEGRAM_BOT_TOKEN=your-telegram-token
   TELEGRAM_WEBHOOK_SECRET=your-webhook-secret
   USE_CELERY=False
   ```

4. **Застосувати міграції та заповнити базу відомих наративів**
   ```bash
   python manage.py migrate
   python manage.py seed_narratives
   ```

5. **Запустити сервер розробки**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

6. **Відкрити інтерфейси**
   - Веб-дашборд: <http://localhost:8000/>
   - REST API: <http://localhost:8000/api/>
   - Django Admin: <http://localhost:8000/admin/>

## REST API

| Метод | Endpoint                   | Опис                                    |
|-------|----------------------------|------------------------------------------|
| POST  | `/api/analysis/`           | Створити новий аналіз                    |
| GET   | `/api/analysis/`           | Список усіх аналізів (з пагінацією)      |
| GET   | `/api/analysis/{id}/`      | Отримати конкретний результат            |
| GET   | `/api/analysis/stats/`     | Агрегована статистика                    |
| POST  | `/api/feedback/`           | Надіслати фідбек на результат            |
| GET   | `/api/narratives/`         | Список відомих ІПСО-наративів            |
| POST  | `/bot/webhook/`            | Telegram webhook endpoint                |

Приклад запиту:

```bash
curl -X POST http://localhost:8000/api/analysis/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Текст для аналізу...", "source": "api"}'
```

## Тести

```bash
python manage.py test
```

Поточне покриття: 37 тестів (core, analyzer, api, web).

## Ліцензія

Академічний проєкт — використання з посиланням на автора.

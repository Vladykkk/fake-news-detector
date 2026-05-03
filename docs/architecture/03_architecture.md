# Архітектура системи IPSO Detector

> Розділи 2.2, 2.3 та 3.1 дипломної роботи

---

## 1. Високорівнева архітектура (діаграма розгортання)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DigitalOcean Droplet                             │
│                        Ubuntu 24.04 LTS                                 │
│                                                                         │
│  ┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐  │
│  │   nginx     │────▶│  API Gateway     │     │  Telegram Bot       │  │
│  │  (reverse   │     │  (Django+DRF     │     │  Service            │  │
│  │   proxy)    │     │   Gunicorn)      │     │  (python-telegram-  │  │
│  │  :80/:443   │     │  :8003           │     │   bot, async)       │  │
│  └──────┬──────┘     └────────┬─────────┘     └──────────┬──────────┘  │
│         │                     │                           │             │
│         │              ┌──────▼──────┐                    │             │
│         │              │             │                    │             │
│         │              │    Redis    │◀───────────────────┘             │
│         │              │   :6379     │                                  │
│         │              │  (broker +  │                                  │
│         │              │   cache)    │                                  │
│         │              └──────┬──────┘                                  │
│         │                     │                                         │
│         │         ┌───────────┼───────────┐                            │
│         │         ▼           ▼           ▼                            │
│         │  ┌────────────┐┌────────────┐┌────────────┐                  │
│         │  │ Analyzer   ││ Analyzer   ││ Analyzer   │                  │
│         │  │ Worker #1  ││ Worker #2  ││ Worker #N  │                  │
│         │  │ (Celery)   ││ (Celery)   ││ (Celery)   │                  │
│         │  └──────┬─────┘└──────┬─────┘└──────┬─────┘                  │
│         │         │             │             │                         │
│         │         └──────┬──────┘─────────────┘                        │
│         │                ▼                                              │
│         │       ┌──────────────────┐                                   │
│         │       │   PostgreSQL     │                                   │
│         │       │   :5432          │                                   │
│         │       │   (persistent    │                                   │
│         │       │    storage)      │                                   │
│         │       └──────────────────┘                                   │
│         │                                                               │
└─────────┼───────────────────────────────────────────────────────────────┘
          │
          │  HTTPS
          ▼
┌───────────────────┐     ┌────────────────────┐
│  Користувачі      │     │  Зовнішні сервіси  │
│  - Telegram       │     │  - OpenRouter API   │
│  - Веб-браузер    │     │  - Google Translate │
│  - API клієнти    │     │  - Telegram API     │
└───────────────────┘     └────────────────────┘
```

---

## 2. Компоненти системи

### 2.1 API Gateway (Django + DRF + Gunicorn)

**Призначення:** Центральна точка входу для всіх HTTP-запитів.

**Відповідальність:**
- Обробка HTTP-запитів від веб-клієнтів та API-клієнтів
- Обробка Telegram webhook (POST /bot/webhook/)
- Рендеринг веб-інтерфейсу (Django templates + HTMX)
- Django admin панель
- Валідація вхідних даних (серіалізатори DRF)
- Делегування задач аналізу до Celery Workers через Redis
- Повернення результатів із бази даних

**Технології:** Django 4.2, DRF, Gunicorn (3 workers), HTMX

**Порт:** 8003 (за nginx reverse proxy)

### 2.2 Telegram Bot Service

**Призначення:** Обробка взаємодії з Telegram-користувачами.

**Відповідальність:**
- Обробка команд (/start, /help, /stats)
- Прийом текстових повідомлень та пересланих постів
- Форматування результатів аналізу у HTML-повідомлення
- Управління inline-кнопками зворотного зв'язку
- Відправка підтвердження прийому ("🔍 Аналізую...")

**Технології:** python-telegram-bot v20 (async), webhook mode

**Комунікація:** Отримує задачі від API Gateway, відправляє задачі аналізу в Redis через Celery

### 2.3 Analyzer Workers (Celery)

**Призначення:** Виконання AI-аналізу тексту в асинхронному режимі.

**Відповідальність:**
- Виконання повного pipeline аналізу:
  1. Визначення мови (langdetect)
  2. Переклад на англійську (deep-translator → Google Translate)
  3. Rule-based аналіз риторики (regex patterns)
  4. LLM-класифікація наративів (OpenRouter API)
  5. Semantic similarity з відомими наративами (sentence-transformers)
  6. Ансамблевий скоринг (зважена комбінація)
- Збереження результату в PostgreSQL
- Відправка результату користувачу (через Telegram API або webhook callback)

**Технології:** Celery 5, sentence-transformers (MiniLM), OpenRouter API

**Масштабування:** Кількість workers регулюється через --concurrency параметр (default: 2)

### 2.4 Data Layer

**PostgreSQL** — основна база даних:
- AnalysisResult — результати аналізу
- TelegramAnalysis — зв'язок з Telegram-чатом
- Feedback — зворотний зв'язок
- KnownNarrative — база відомих ІПСО-наративів з embeddings

**Redis** — подвійна роль:
- **Message Broker** для Celery (черга задач аналізу)
- **Cache** для часто використовуваних даних (embeddings відомих наративів)

---

## 3. Комунікаційна модель

### Топологія: Зоряна (Star) з Redis у центрі

```
                    ┌─────────────┐
                    │  Telegram   │
                    │  Bot Service│
                    └──────┬──────┘
                           │
┌──────────────┐    ┌──────▼──────┐    ┌──────────────┐
│  API Gateway │───▶│    Redis    │◀───│  Analyzer    │
│  (Django)    │    │  (Broker)   │    │  Worker #1   │
└──────────────┘    └──────┬──────┘    └──────────────┘
                           │
                    ┌──────▼──────┐
                    │  Analyzer   │
                    │  Worker #2  │
                    └─────────────┘
```

### Протоколи комунікації

| Від → До | Протокол | Формат | Опис |
|----------|----------|--------|------|
| Користувач → nginx | HTTPS | HTTP/1.1 | Зовнішній трафік |
| nginx → API Gateway | HTTP | Proxy pass | Внутрішній reverse proxy |
| Telegram → nginx | HTTPS | JSON (webhook) | Telegram Update payload |
| API Gateway → Redis | AMQP-like | Celery task serialization (JSON) | Делегування задач |
| Redis → Analyzer Worker | AMQP-like | Celery task deserialization | Отримання задач |
| Analyzer Worker → PostgreSQL | TCP | SQL (psycopg2) | Збереження результатів |
| Analyzer Worker → OpenRouter | HTTPS | JSON (REST API) | LLM inference |
| Analyzer Worker → Google Translate | HTTPS | REST | Переклад тексту |
| Analyzer Worker → Telegram API | HTTPS | JSON (Bot API) | Відправка результату |
| API Gateway → PostgreSQL | TCP | SQL (Django ORM) | Читання результатів |

### Формат повідомлень у черзі (Celery Task Payload)

```json
{
  "task": "apps.analyzer.tasks.analyze_content_task",
  "args": [],
  "kwargs": {
    "text": "Зеленський вкрав мільярди...",
    "chat_id": 123456789,
    "message_id": 42,
    "username": "user123",
    "source": "telegram"
  },
  "retries": 0,
  "eta": null
}
```

---

## 4. Діаграма потоків даних (DFD)

### Рівень 0 — Контекстна діаграма

```
┌──────────────┐                                    ┌──────────────┐
│  Telegram    │──── текст повідомлення ────▶┐      │  OpenRouter  │
│  Користувач  │◀── результат аналізу ──────┤      │  API         │
└──────────────┘                             │      └───────▲──────┘
                                             ▼              │
┌──────────────┐                     ┌───────────────┐      │
│  Веб         │── текст для аналізу▶│               │──────┘
│  Користувач  │◀─ результат ────────│  IPSO         │
└──────────────┘                     │  Detector     │
                                     │  System       │
┌──────────────┐                     │               │──────┐
│  API         │── POST /analyze/ ──▶│               │      │
│  Клієнт      │◀─ JSON response ───│               │      ▼
└──────────────┘                     └───────────────┘ ┌────────────┐
                                             ▲         │ Google     │
┌──────────────┐                             │         │ Translate  │
│  Адміністра- │── управління наративами ────┘         └────────────┘
│  тор         │◀── статистика ─────────────┘
└──────────────┘
```

### Рівень 1 — Декомпозиція основного процесу

```
                        ┌─────────────────┐
    вхідний текст ─────▶│  1.0 Прийом     │
                        │  та валідація   │──── помилка (текст замалий)
                        └────────┬────────┘
                                 │ валідований текст
                                 ▼
                        ┌─────────────────┐
                        │  2.0 Попередня  │──────────────▶ Google Translate API
                        │  обробка        │◀──────────────
                        │  (мова+переклад)│
                        └────────┬────────┘
                                 │ англійський текст + мова
                                 ▼
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  3.1 Аналіз     │ │  3.2 Класифі-   │ │  3.3 Семантичне │
    │  риторики       │ │  кація наративів│ │  порівняння     │
    │  (rule-based)   │ │  (OpenRouter    │ │  (embeddings)   │
    │                 │ │   LLM)          │ │                 │
    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
             │ rhetoric_score    │ narrative_score    │ similarity_score
             └──────────────────┬┘───────────────────┘
                                ▼
                       ┌─────────────────┐
                       │  4.0 Ансамблевий│
                       │  скоринг        │
                       │  (weighted sum) │
                       └────────┬────────┘
                                │ final_score + verdict
                                ▼
                       ┌─────────────────┐
                       │  5.0 Збереження │─────▶ PostgreSQL
                       │  та відповідь   │
                       └─────────────────┘
```

---

## 5. Workflow — сценарій «Telegram-користувач надсилає повідомлення»

```
[Користувач]                [API Gateway]           [Redis/Celery]         [Analyzer Worker]        [Зовнішні API]
     │                            │                       │                       │                       │
     │── надсилає текст ─────────▶│                       │                       │                       │
     │                            │── валідація ─────────▶│                       │                       │
     │                            │   webhook secret      │                       │                       │
     │                            │                       │                       │                       │
     │◀── "🔍 Аналізую..." ──────│                       │                       │                       │
     │                            │── analyze_task ──────▶│                       │                       │
     │                            │   .delay(text,        │                       │                       │
     │                            │    chat_id, ...)      │                       │                       │
     │                            │                       │── deliver task ──────▶│                       │
     │                            │                       │                       │                       │
     │                            │                       │                       │── detect_language ───▶│
     │                            │                       │                       │◀── "uk" ──────────────│
     │                            │                       │                       │                       │
     │                            │                       │                       │── translate ─────────▶│ Google
     │                            │                       │                       │◀── english text ──────│ Translate
     │                            │                       │                       │                       │
     │                            │                       │                       │── analyze_rhetoric()  │
     │                            │                       │                       │   (local, regex)      │
     │                            │                       │                       │                       │
     │                            │                       │                       │── classify ──────────▶│ OpenRouter
     │                            │                       │                       │◀── narratives ────────│ (LLM)
     │                            │                       │                       │                       │
     │                            │                       │                       │── similarity()        │
     │                            │                       │                       │   (local embeddings)  │
     │                            │                       │                       │                       │
     │                            │                       │                       │── ensemble score ─────│
     │                            │                       │                       │── save to PostgreSQL ─│
     │                            │                       │                       │                       │
     │◀──────────────────── formatted result + keyboard ──│                       │ Telegram
     │                            │                       │                       │ Bot API
     │── натискає 👍/👎 ─────────▶│                       │                       │
     │                            │── save feedback ──────│───────────────────────│──▶ PostgreSQL
     │◀── "Дякуємо!" ────────────│                       │                       │
```

---

## 6. ER-діаграма (інфологічна модель)

```
┌─────────────────────────┐       ┌─────────────────────────┐
│     AnalysisResult      │       │    TelegramAnalysis     │
├─────────────────────────┤       ├─────────────────────────┤
│ PK id                   │       │ PK id                   │
│    original_text        │──1:1──│ FK result_id            │
│    detected_language     │       │    chat_id              │
│    translated_text       │       │    message_id           │
│    source               │       │    username             │
│    narrative_score       │       │    created_at           │
│    rhetoric_score        │       └─────────────────────────┘
│    similarity_score      │
│    final_score           │       ┌─────────────────────────┐
│    verdict               │       │       Feedback          │
│    detected_narratives   │       ├─────────────────────────┤
│    detected_rhetoric     │──1:N──│ PK id                   │
│    similar_narratives    │       │ FK result_id            │
│    processing_time_ms    │       │    feedback_type         │
│    created_at            │       │    chat_id              │
└─────────────────────────┘       │    created_at           │
                                   └─────────────────────────┘

┌─────────────────────────┐
│    KnownNarrative       │
├─────────────────────────┤
│ PK id                   │  (порівняння через cosine similarity,
│    title                │   не FK — зв'язок семантичний)
│    description          │
│    category             │
│    example_texts (JSON) │
│    embedding (JSON)     │
│    source               │
│    is_active            │
│    created_at           │
└─────────────────────────┘
```

**Зв'язки:**
- **AnalysisResult ↔ TelegramAnalysis**: 1:1 — кожен Telegram-аналіз прив'язаний до одного результату
- **AnalysisResult ↔ Feedback**: 1:N — один результат може мати декілька відгуків (від різних користувачів, які бачать переслане)
- **KnownNarrative**: незалежна сутність, зв'язок з AnalysisResult — логічний (через cosine similarity), не реляційний

---

## 7. Обґрунтування вибору архітектури

### Чому SOA з чергою повідомлень, а не моноліт чи мікросервіси

**Розподіленість.** Система складається з 4 логічно незалежних компонентів (API Gateway, Bot Service, Analyzer Workers, Data Layer), які комунікують через Redis (брокер повідомлень) та PostgreSQL (спільне сховище). Кожен компонент може бути запущений як окремий процес, а Analyzer Workers можуть масштабуватись горизонтально.

**Асинхронність.** AI-аналіз — це тривала операція (3–10 секунд через зовнішній API). Синхронний підхід блокував би веб-сервер та Telegram webhook. Celery + Redis забезпечують неблокуючу обробку з автоматичними retry.

**Відмовостійкість.** Збій одного Analyzer Worker не впливає на Gateway чи Bot Service. Celery автоматично перевидає задачу іншому доступному воркеру. Systemd забезпечує автоматичний перезапуск процесів.

**Єдина кодова база.** На відміну від мікросервісів, усі компоненти використовують один Django-проєкт, що спрощує розробку одним розробником та забезпечує консистентність моделей даних.

**Економність.** Усі компоненти розміщуються на одному DigitalOcean droplet, але логічно розділені та готові до розведення на окремі вузли при потребі.

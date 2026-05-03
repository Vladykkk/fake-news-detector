# Маппінг існуючих діаграм → нова архітектура

> Цей документ описує, що потрібно змінити в існуючих діаграмах (папка diagrams/)
> для відповідності оновленій SOA-архітектурі з Telegram-ботом, веб-інтерфейсом та Django API.

---

## Загальна зміна контексту

**Було:** Браузерне розширення (Extension), яке аналізує веб-сторінки на наявність фейків.

**Стало:** Розподілена серверна система (Django + Celery + Redis), яка приймає текст через Telegram-бот, веб-інтерфейс та REST API і повертає структурований результат аналізу.

---

## 1. Діаграма варіантів використання (Use Case)

**Статус:** Потребує значних змін

**Що зберегти:**
- Use case "Аналіз тексту на наявність неправдивої інформації" — основний, залишається
- Use case "Застосовування алгоритму штучного інтелекту" — залишається як <<include>>
- Use case "Оновлення бази даних" — залишається (збереження результатів + управління наративами)
- Use case "Надання пояснення" — залишається (форматований результат з деталями)

**Що змінити:**

| Було | Стало |
|------|-------|
| Актор "Користувач" (один) | 3 актори: "Telegram-користувач", "Веб-користувач", "API-клієнт" |
| Актор "Розширення" | Актор "Система IPSO Detector" (або прибрати, бо це сама система) |
| UC "Перегляд веб-сторінки" | UC "Надсилання тексту через Telegram" / "Введення тексту на веб-сторінці" |
| UC "Налаштування параметрів" | UC "Управління базою наративів" (адміністратор) |
| UC "Блокування на основі результату" | Прибрати (система не блокує, а інформує) |
| UC "Обробленя NLP" | UC "Переклад та визначення мови" |
| UC "Перевірка достовірності джерела" | UC "Порівняння з базою відомих ІПСО-наративів" |
| — | Додати: UC "Перегляд історії аналізів" |
| — | Додати: UC "Надання зворотного зв'язку" (👍/👎) |
| — | Додати: UC "Перегляд статистики" (/stats) |
| — | Додати актор: "Адміністратор" |

**Оновлені актори:**
1. **Telegram-користувач** — надсилає текст, отримує результат, дає зворотний зв'язок
2. **Веб-користувач** — вводить текст на сайті, переглядає результат та історію
3. **API-клієнт** — інтегрується через REST API
4. **Адміністратор** — управляє наративами, переглядає статистику через Django admin

---

## 2. Діаграма діяльності (Activity)

**Статус:** Потребує помірних змін — загальний flow подібний

**Що зберегти:**
- Загальний потік: перевірка → аналіз тексту → рішення → результат — це коректно
- Decision node для визначення достовірності — аналогічний до нашого verdict (safe/suspicious/ipso)

**Що змінити:**

| Було | Стало |
|------|-------|
| "Очікування. Надання доступу до вмісту сторінки" | "Прийом тексту через Telegram/Web/API" |
| "Перевірка чи наданий доступ" | "Валідація тексту (≥30 символів)" |
| "Очікування. Відкрити сторінку" | Прибрати (немає веб-сторінки) |
| "Перевірка джерела на достовірність" | "Визначення мови + переклад" |
| DecisionNode "Джерело достовірне/не достовірне" | DecisionNode "verdict: safe / suspicious / ipso" |
| "Генерація тексту попередження підозрілого тексту" | "Форматування результату аналізу" |
| "Підсвітка підозрілого тексту" | "Відправка результату користувачу" |
| "Перевірка джерела на достовірність" | "Аналіз риторики + LLM класифікація + similarity" |

**Додати:**
- Fork node після "Визначення мови": паралельний запуск 3 модулів аналізу
- Join node: збір результатів 3 модулів → ансамблевий скоринг
- Activity "Збереження результату в БД"
- Activity "Очікування зворотного зв'язку (feedback)"

---

## 3. Діаграма класів (Class)

**Статус:** Потребує значних змін — класи під Extension не відповідають Django-моделям

**Маппінг класів:**

| Було (Extension) | Стало (Django) | Нотатки |
|------------------|----------------|---------|
| User (name, visitPage(), initiateTextAnalysis()) | Telegram User / Web User (не зберігається як модель, дані в TelegramAnalysis) | Зовнішній актор |
| Extension (isActive, analyzeText(), toggleActivation()) | **Прибрати** — немає розширення | — |
| NLPProcessor (inputText, processText(), detectLanguage(), extractLanguageText()) | **TranslatorModule** (detect_language(), translate_to_english(), preprocess()) | Модуль apps/analyzer/translator.py |
| SourceCredibilityChecker (credibilityDatabase, checkSourceCredibility(), updateCredibilityScore()) | **SimilarityModule** (analyze_similarity(), cosine_similarity(), compute_and_store_embeddings()) | Модуль apps/analyzer/similarity.py |
| AIAlgorithm (model, analyzeContext(), isFactual()) | **NarrativeModule** (analyze_narratives(), classify via OpenRouter) + **RhetoricModule** (analyze_rhetoric()) | 2 окремих модулі |
| ProcessedText (originalText, tokenizedText, namedEntities, sentimentScore, keywords) | **Проміжний dict** у pipeline (preprocessed: original, detected_language, translated) | Не зберігається як окрема модель |
| FakeNewsDatabase (knownFakes, addFakeReport(), verifyAgainstDatabase(), updateDatabase()) | **KnownNarrative** (Django model) + management command seed_narratives | apps/core/models.py |
| AnalysisResults (confidenceScore, reportedFactors, highlightedText, isHighlighted) | **AnalysisResult** (Django model: final_score, verdict, detected_narratives, detected_rhetoric, similar_narratives) | apps/core/models.py |

**Додати нові класи:**
- **AnalysisPipeline** — оркестратор (apps/analyzer/pipeline.py): analyze(), analyze_and_save(), get_verdict()
- **TelegramAnalysis** — модель зв'язку з Telegram
- **Feedback** — модель зворотного зв'язку
- **CeleryTask** (analyze_content_task) — асинхронна задача
- **TelegramHandlers** — обробники команд бота
- **APIViews** (AnalyzeView, HistoryView) — REST ендпоінти

---

## 4. Діаграма компонентів (Component)

**Статус:** Потребує значних змін

**Маппінг:**

| Було | Стало |
|------|-------|
| FakeTextAnalyzer.exe | — (немає виконуваного файлу, серверна система) |
| Розширення | **API Gateway** (Django + Gunicorn) |
| MainExtension | **AnalysisPipeline** (apps/analyzer/pipeline.py) |
| Аналізатор тексту | **Analyzer Workers** (Celery processes) |
| Генератор звітів | **Formatter** (apps/bot/formatters.py + web templates) |
| База даних | **PostgreSQL** + **Redis** |
| Інтерфейс для користувача | **Telegram Bot** + **Web Interface** + **REST API** |

**Нові компоненти:**
- **nginx** (reverse proxy)
- **Redis** (message broker + cache)
- **OpenRouter Client** (зовнішній AI API)
- **Translator** (Google Translate через deep-translator)

---

## 5. Діаграма кооперації (Collaboration)

**Статус:** Потребує помірних змін — логіка взаємодії подібна

Пронумеровані повідомлення потрібно оновити:
1. Користувач → Telegram Bot: надсилає текст
2. Telegram Bot → API Gateway: webhook POST
3. API Gateway → Redis: analyze_task.delay()
4. Redis → Analyzer Worker: deliver task
5. Analyzer Worker → Google Translate: переклад
6. Analyzer Worker → внутрішній analyze_rhetoric()
7. Analyzer Worker → OpenRouter: classify narratives
8. Analyzer Worker → внутрішній analyze_similarity()
9. Analyzer Worker → PostgreSQL: save AnalysisResult
10. Analyzer Worker → Telegram API: send formatted result

---

## 6. Діаграма послідовності (Sequence)

**Статус:** Потребує помірних змін — структура lifelines аналогічна

**Маппінг lifelines:**

| Було | Стало |
|------|-------|
| Користувач | Telegram-користувач |
| Розширення | API Gateway (Django) |
| Веб-Сторінка | — (прибрати, веб-сторінка тепер наша, не зовнішня) |
| NLP | Translator Module + Rhetoric Module |
| AI | OpenRouter (LLM) + Similarity Module |
| База даних | PostgreSQL |

**Додати lifelines:**
- Redis / Celery (між API Gateway та Analyzer Worker)
- Telegram API (для відправки результату)

**Оновлена послідовність відповідає Workflow з файлу 03_architecture.md (секція 5).**

---

## Рекомендований інструмент для оновлення

Рекомендую перемалювати діаграми у **draw.io** (diagrams.net) або **PlantUML**:
- draw.io: візуальний редактор, експорт у PNG/SVG, безкоштовний
- PlantUML: текстовий формат (зручно для версіонування в Git), автогенерація діаграм

Для диплому потрібні чисті, читабельні діаграми на **українській мові** з відстанню читання 3–6 м (вимога методички).

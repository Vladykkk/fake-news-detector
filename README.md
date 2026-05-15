# 🛡️ IPSO Detector

A distributed information system for detecting Russian information-psychological operations (IPSO) in open-source text messages using artificial intelligence. The system combines LLM-based narrative classification, rule-based rhetorical marker analysis, and semantic similarity to a database of known narratives into a single ensemble score.

Bachelor's thesis — Rybak Vladyslav Yaroslavovych, Lviv Polytechnic National University, group RI-31sp, 2026.

## ✨ Technologies

- `Python 3.12`
- `Django 4.2 LTS` + `Django REST Framework`
- `Celery 5` + `Redis`
- `PostgreSQL 16`
- `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`)
- `OpenRouter API` (LLM) + `DeepL API` (translation)
- `python-telegram-bot`
- `HTMX` + `Bootstrap 5`
- `Docker` + `Docker Compose`
- `Gunicorn`

## 🚀 Features

- Ensemble IPSO score from three independent modules (narratives, rhetoric, similarity)
- REST API with pagination, feedback, and statistics endpoints
- Telegram bot for analyzing messages directly in the messenger
- HTMX-powered web dashboard — no SPA framework required
- Asynchronous task processing via Celery + Redis
- Fully containerized — single-command launch via Docker Compose

## 📍 Architecture

The system consists of three analysis modules combined into an ensemble score:

| Module     | Method                                          | Weight |
| ---------- | ----------------------------------------------- | ------ |
| Narratives | LLM (OpenRouter API) — zero-shot classification | 0.40   |
| Rhetoric   | Rule-based regex patterns (UK + EN)             | 0.30   |
| Similarity | sentence-transformers + cosine similarity       | 0.30   |

Final score: `S = 0.40 × narrative + 0.30 × rhetoric + 0.30 × similarity`

Verdict thresholds:

- `safe` — S < 0.35
- `suspicious` — 0.35 ≤ S < 0.70
- `ipso` — S ≥ 0.70 (IPSO detected)

## 📂 Project Structure

```
fake-news-detector/
├── config/              # Django settings (base/dev/prod), URLs, Celery
├── apps/
│   ├── core/            # DB models: AnalysisResult, KnownNarrative, Feedback
│   ├── analyzer/        # Analysis pipeline (translator, rhetoric, narrative, similarity)
│   ├── api/             # REST API — ViewSets, serializers
│   ├── bot/             # Telegram handlers (polling / webhook)
│   └── web/             # HTMX dashboard with class-based views
├── templates/web/       # Django templates
├── data/narratives/     # JSON seed for known narratives
├── scripts/             # Helper scripts (test_pipeline.sh)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── manage.py
```

## 🚦 Running with Docker (recommended)

1. **Clone the repository**

   ```bash
   git clone <repo-url>
   cd fake-news-detector
   ```

2. **Create `.env`** (copy from `.env.example` and fill in the keys)

   ```bash
   cp .env.example .env
   ```

   Fill in `OPENROUTER_API_KEY`, `DEEPL_API_KEY`, `TELEGRAM_BOT_TOKEN`, `SECRET_KEY`, `DB_PASSWORD`.

3. **Bring up all services**

   ```bash
   docker compose up --build
   ```

   Compose automatically starts PostgreSQL, Redis, the web server (gunicorn), and the Telegram bot. Migrations and seeding of known narratives run on first startup.

4. **Open the interfaces**
   - Web dashboard: <http://localhost:8000/>
   - REST API: <http://localhost:8000/api/>
   - Django Admin: <http://localhost:8000/admin/>

5. **Create a superuser** (optional)
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

## 🛠️ Running Locally (without Docker)

1. **Create virtualenv and install dependencies**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip3 install -r requirements.txt
   ```

2. **Start PostgreSQL and Redis** (e.g. via `docker compose up db redis`)

3. **Configure `.env`** (see above) — set `DB_HOST=localhost`

4. **Apply migrations and seed the database**

   ```bash
   python3 manage.py migrate
   python3 manage.py seed_narratives --compute-embeddings
   ```

5. **Run the development server**

   ```bash
   python3 manage.py runserver 0.0.0.0:8000
   ```

6. **Run the Telegram bot** (in a separate terminal)
   ```bash
   python3 manage.py run_bot
   ```

## 🔌 REST API

| Method | Endpoint               | Description                   |
| ------ | ---------------------- | ----------------------------- |
| POST   | `/api/analysis/`       | Create a new analysis         |
| GET    | `/api/analysis/`       | List all analyses (paginated) |
| GET    | `/api/analysis/{id}/`  | Retrieve a specific result    |
| GET    | `/api/analysis/stats/` | Aggregated statistics         |
| POST   | `/api/feedback/`       | Submit feedback on a result   |
| GET    | `/api/narratives/`     | List known IPSO narratives    |
| POST   | `/bot/webhook/`        | Telegram webhook endpoint     |

Example request:

```bash
curl -X POST http://localhost:8000/api/analysis/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Text to analyze...", "source": "api"}'
```

## 🧪 Tests

```bash
# Locally
python3 manage.py test

# Inside the container
docker compose exec web python manage.py test
```

## 📜 License

Academic project — use with attribution to the author.

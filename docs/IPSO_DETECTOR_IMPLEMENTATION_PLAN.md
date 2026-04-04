# IPSO Detector — Implementation Plan
## Django + Telegram Bot + AI Pipeline

> **For Claude Code:** This document is a full technical specification for implementing
> an information system that detects Russian psyops (ІПСО) using AI methods.
> Implement step by step in the order given. Do not skip phases.

---

## 1. Project Overview

**Goal:** A Django backend with a Telegram bot that accepts text/forwarded posts,
analyzes them for signs of information psychological operations (ІПСО/psyops),
and returns a structured analysis with confidence score and reasons.

**Stack:**
- Backend: Django 4.2 + Django REST Framework
- Task queue: Celery + Redis
- Database: PostgreSQL
- Bot: python-telegram-bot v20 (async)
- AI: HuggingFace Transformers (BERT) + spaCy + sentence-transformers
- Hosting: DigitalOcean Ubuntu 24.04 droplet
- Reverse proxy: nginx + Let's Encrypt SSL

---

## 2. Repository Structure

```
ipso_detector/
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
│
├── apps/
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── views.py          # Webhook endpoint
│   │   ├── handlers.py       # Telegram command/message handlers
│   │   ├── keyboards.py      # Inline keyboard builders
│   │   ├── formatters.py     # Format analysis result → Telegram message
│   │   └── urls.py
│   │
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── pipeline.py       # Main orchestrator — entry point for all analysis
│   │   ├── translator.py     # Language detection + translation to EN/UK
│   │   ├── narrative.py      # BERT-based narrative classifier
│   │   ├── rhetoric.py       # Rule-based rhetorical manipulation detector
│   │   ├── similarity.py     # Cosine similarity against known IPSO narratives
│   │   ├── tasks.py          # Celery async tasks
│   │   └── constants.py      # Narrative labels, thresholds, keyword lists
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── views.py          # REST API endpoints
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   └── core/
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py         # DB models
│       ├── admin.py
│       └── migrations/
│
├── data/
│   └── narratives/
│       └── known_narratives.json   # Seeded IPSO narrative database
│
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
│
├── .env.example
├── manage.py
└── README.md
```

---

## 3. Dependencies

### requirements/base.txt
```
django==4.2.16
djangorestframework==3.15.2
psycopg2-binary==2.9.9
python-decouple==3.8
celery==5.3.6
redis==5.0.1
python-telegram-bot==20.7
gunicorn==21.2.0
django-cors-headers==4.3.1
```

### requirements/prod.txt
```
-r base.txt
```

### requirements/dev.txt
```
-r base.txt
django-debug-toolbar==4.3.0
pytest-django==4.8.0
factory-boy==3.3.0
```

### AI requirements (install separately, heavy):
```
transformers==4.40.0
torch==2.3.0
sentence-transformers==2.7.0
spacy==3.7.4
deep-translator==1.11.4
langdetect==1.0.9
numpy==1.26.4
scikit-learn==1.4.2
```

**Install spaCy language models after install:**
```bash
python -m spacy download en_core_web_sm
python -m spacy download uk_core_news_sm
python -m spacy download ru_core_news_sm
```

---

## 4. Environment Variables

### .env.example
```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DJANGO_SETTINGS_MODULE=config.settings.prod

# Database
DB_NAME=ipso_detector
DB_USER=ipso_user
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
TELEGRAM_WEBHOOK_SECRET=random-secret-string-for-webhook-validation

# Hugging Face (optional — for remote inference fallback)
HF_API_TOKEN=your-hf-token

# Analysis thresholds
IPSO_SCORE_SAFE=0.35
IPSO_SCORE_SUSPICIOUS=0.70

# Feature flags
USE_LOCAL_BERT=True       # False = use HF Inference API (saves RAM)
USE_CELERY=True           # False = synchronous (dev mode)
```

---

## 5. Django Settings

### config/settings/base.py
```python
from decouple import config, Csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
]

LOCAL_APPS = [
    'apps.core',
    'apps.bot',
    'apps.analyzer',
    'apps.api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'Europe/Kyiv'

# Telegram
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN')
TELEGRAM_WEBHOOK_SECRET = config('TELEGRAM_WEBHOOK_SECRET')

# Analysis config
IPSO_SCORE_SAFE = config('IPSO_SCORE_SAFE', default=0.35, cast=float)
IPSO_SCORE_SUSPICIOUS = config('IPSO_SCORE_SUSPICIOUS', default=0.70, cast=float)
USE_LOCAL_BERT = config('USE_LOCAL_BERT', default=True, cast=bool)
USE_CELERY = config('USE_CELERY', default=True, cast=bool)

# Weights for ensemble scoring
ANALYZER_WEIGHTS = {
    'narrative': 0.40,
    'rhetoric': 0.30,
    'similarity': 0.30,
}

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True
```

### config/settings/dev.py
```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']
USE_CELERY = False  # Run synchronously in dev
USE_LOCAL_BERT = False  # Use HF API in dev to save RAM
```

### config/settings/prod.py
```python
from .base import *

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## 6. Celery Configuration

### config/celery.py
```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

app = Celery('ipso_detector')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

### config/__init__.py
```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

---

## 7. Database Models

### apps/core/models.py
```python
from django.db import models


class AnalysisResult(models.Model):
    """Stores every analysis request and its result."""

    class Verdict(models.TextChoices):
        SAFE = 'safe', 'Безпечно'
        SUSPICIOUS = 'suspicious', 'Підозрілий'
        IPSO = 'ipso', 'ІПСО'

    # Input
    original_text = models.TextField()
    detected_language = models.CharField(max_length=10, blank=True)
    translated_text = models.TextField(blank=True)
    source = models.CharField(max_length=50, default='telegram')  # telegram, api, web

    # Scores (0.0 – 1.0 for each module)
    narrative_score = models.FloatField(default=0.0)
    rhetoric_score = models.FloatField(default=0.0)
    similarity_score = models.FloatField(default=0.0)
    final_score = models.FloatField(default=0.0)

    # Result
    verdict = models.CharField(max_length=20, choices=Verdict.choices, default=Verdict.SAFE)
    detected_narratives = models.JSONField(default=list)   # [{"label": "demoralization", "confidence": 0.87}]
    detected_rhetoric = models.JSONField(default=list)     # [{"type": "whataboutism", "snippet": "..."}]
    similar_narratives = models.JSONField(default=list)    # [{"id": 1, "similarity": 0.91, "title": "..."}]

    # Metadata
    processing_time_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.verdict}] {self.final_score:.2f} — {self.original_text[:60]}"


class TelegramAnalysis(models.Model):
    """Links AnalysisResult to a specific Telegram interaction."""
    result = models.OneToOneField(AnalysisResult, on_delete=models.CASCADE, related_name='telegram')
    chat_id = models.BigIntegerField()
    message_id = models.BigIntegerField()
    username = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Feedback(models.Model):
    """User feedback on analysis results (👍 / 👎)."""

    class FeedbackType(models.TextChoices):
        CORRECT = 'correct', 'Правильно'
        WRONG = 'wrong', 'Помилка'

    result = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name='feedbacks')
    feedback_type = models.CharField(max_length=10, choices=FeedbackType.choices)
    chat_id = models.BigIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class KnownNarrative(models.Model):
    """Database of known IPSO narratives for similarity comparison."""

    class Category(models.TextChoices):
        DEMORALIZATION = 'demoralization', 'Деморалізація'
        DISTRUST = 'distrust', 'Підрив довіри'
        FALSE_EQUIVALENCE = 'false_equivalence', 'Хибна рівність'
        PANIC = 'panic', 'Паніка та страх'
        CORRUPTION = 'corruption', 'Корупція'
        MILITARY_LOSSES = 'military_losses', 'Втрати ЗСУ'
        WESTERN_ABANDONMENT = 'western_abandonment', 'Захід зраджує'
        OTHER = 'other', 'Інше'

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=Category.choices)
    example_texts = models.JSONField(default=list)  # List of example strings
    embedding = models.JSONField(null=True, blank=True)  # Stored vector embedding
    source = models.CharField(max_length=100, blank=True)  # e.g. "StopFake", "VoxCheck"
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.category}] {self.title}"
```

### apps/core/admin.py
```python
from django.contrib import admin
from .models import AnalysisResult, TelegramAnalysis, Feedback, KnownNarrative


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ['verdict', 'final_score', 'detected_language', 'source', 'created_at']
    list_filter = ['verdict', 'source', 'detected_language']
    search_fields = ['original_text']
    readonly_fields = ['created_at', 'processing_time_ms']


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['feedback_type', 'result', 'created_at']
    list_filter = ['feedback_type']


@admin.register(KnownNarrative)
class KnownNarrativeAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'source', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['title', 'description']
```

---

## 8. AI Pipeline

### apps/analyzer/constants.py
```python
# Rhetorical manipulation patterns (regex-based, language-agnostic after translation)
RHETORIC_PATTERNS = {
    'whataboutism': [
        r'\bwhat about\b',
        r'\band what about\b',
        r'\bbut what about\b',
        r'\bwhere were you when\b',
        r'\bwhy don.t you talk about\b',
    ],
    'false_authority': [
        r'\bsources in\b',
        r'\bexperts say\b',
        r'\banalysts claim\b',
        r'\binsiders report\b',
        r'\baccording to military sources\b',
        r'\bofficial sources confirm\b',
    ],
    'fear_panic': [
        r'\bmillions will die\b',
        r'\bcollapse is inevitable\b',
        r'\bno hope\b',
        r'\ball is lost\b',
        r'\bwithin days\b.{0,20}\bfall\b',
        r'\bno chance of\b',
    ],
    'demoralization': [
        r'\buseless resistance\b',
        r'\bfutile to fight\b',
        r'\bzelensky.{0,20}fled\b',
        r'\bzelensky.{0,20}billion\b',
        r'\bcoward\b',
        r'\bsurrender.{0,30}only option\b',
    ],
    'false_equivalence': [
        r'\bboth sides\b',
        r'\bequally guilty\b',
        r'\bboth are wrong\b',
        r'\bno difference between\b',
        r'\bsame as\b.{0,30}\bnazi\b',
    ],
    'cherry_picking': [
        r'\bone soldier said\b',
        r'\bone case proves\b',
        r'\bas an example\b.{0,20}\bthis shows all\b',
    ],
}

# Narrative labels for BERT classifier output mapping
NARRATIVE_LABELS = {
    0: 'neutral',
    1: 'demoralization',
    2: 'distrust_institutions',
    3: 'false_equivalence',
    4: 'panic_fear',
    5: 'military_losses_exaggeration',
    6: 'western_abandonment',
    7: 'corruption_accusation',
}

# Verdict thresholds (overridden by settings)
THRESHOLD_SAFE = 0.35
THRESHOLD_SUSPICIOUS = 0.70

# Minimum text length to analyze (skip very short texts)
MIN_TEXT_LENGTH = 30
```

### apps/analyzer/translator.py
```python
"""
Language detection and translation module.
Translates any input text to English for unified analysis.
"""
import logging
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """Detect language code of text. Returns 'unknown' on failure."""
    try:
        return detect(text)
    except LangDetectException:
        return 'unknown'


def translate_to_english(text: str, source_lang: str = 'auto') -> str:
    """
    Translate text to English.
    Returns original text if translation fails or language is already English.
    """
    if source_lang == 'en':
        return text

    try:
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        return translated or text
    except Exception as e:
        logger.warning(f"Translation failed: {e}. Using original text.")
        return text


def preprocess(text: str) -> dict:
    """
    Full preprocessing step.
    Returns dict with original, detected_language, translated_text.
    """
    text = text.strip()
    lang = detect_language(text)
    translated = translate_to_english(text, source_lang=lang)

    return {
        'original': text,
        'detected_language': lang,
        'translated': translated,
    }
```

### apps/analyzer/rhetoric.py
```python
"""
Rule-based rhetorical manipulation detector.
Uses regex patterns on translated (English) text.
No ML model required — runs fast.
"""
import re
import logging
from .constants import RHETORIC_PATTERNS

logger = logging.getLogger(__name__)


def analyze_rhetoric(text: str) -> dict:
    """
    Scan text for rhetorical manipulation patterns.

    Args:
        text: English-translated text to analyze

    Returns:
        {
            'score': float,           # 0.0 – 1.0
            'detections': [           # List of found patterns
                {'type': str, 'snippet': str, 'confidence': float}
            ]
        }
    """
    text_lower = text.lower()
    detections = []
    matched_types = set()

    for pattern_type, patterns in RHETORIC_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match and pattern_type not in matched_types:
                # Extract surrounding context (up to 80 chars)
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                snippet = text[start:end].strip()

                detections.append({
                    'type': pattern_type,
                    'snippet': snippet,
                    'confidence': 0.75,  # Rule-based = fixed confidence
                })
                matched_types.add(pattern_type)
                break  # One detection per type is enough

    # Score: each unique type found adds to the score, max 1.0
    # With 6 pattern types total, each contributes ~0.167
    score = min(len(matched_types) / 3.0, 1.0)  # Saturates at 3+ matches

    return {
        'score': round(score, 3),
        'detections': detections,
    }
```

### apps/analyzer/narrative.py
```python
"""
BERT-based narrative classifier.
Phase 1: Uses zero-shot classification (no fine-tuning needed to start).
Phase 2 (later): Replace with fine-tuned model on Ukrainian propaganda dataset.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# IPSO narrative candidates for zero-shot classification
NARRATIVE_CANDIDATES = [
    "demoralization of Ukrainian soldiers and civilians",
    "distrust in Ukrainian government and institutions",
    "false equivalence between Ukraine and Russia",
    "panic about imminent military defeat",
    "exaggerated Ukrainian military losses",
    "claim that Western support is ending",
    "corruption accusations against Ukrainian leadership",
    "neutral factual information",
]

_classifier = None


def _get_classifier():
    """Lazy load the classifier model (loads once, reused)."""
    global _classifier

    if _classifier is not None:
        return _classifier

    if not settings.USE_LOCAL_BERT:
        return None  # Will use HF API instead

    try:
        from transformers import pipeline
        logger.info("Loading zero-shot classification model...")
        _classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",  # Good multilingual zero-shot model
            device=-1,  # CPU inference (-1), use 0 for GPU
        )
        logger.info("Model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load BERT model: {e}")
        _classifier = None

    return _classifier


def _classify_via_hf_api(text: str) -> dict:
    """Fallback: use Hugging Face Inference API."""
    import requests
    from django.conf import settings

    api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
    headers = {"Authorization": f"Bearer {getattr(settings, 'HF_API_TOKEN', '')}"}

    payload = {
        "inputs": text[:512],  # API has token limits
        "parameters": {"candidate_labels": NARRATIVE_CANDIDATES},
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"HF API call failed: {e}")
        return {}


def analyze_narratives(text: str) -> dict:
    """
    Classify text against known IPSO narrative categories.

    Args:
        text: English-translated text (max 512 tokens for BERT)

    Returns:
        {
            'score': float,
            'detections': [{'label': str, 'confidence': float}]
        }
    """
    text = text[:1500]  # Truncate for model limits

    classifier = _get_classifier()

    if classifier is not None:
        # Local inference
        try:
            result = classifier(text, NARRATIVE_CANDIDATES, multi_label=True)
            raw_scores = dict(zip(result['labels'], result['scores']))
        except Exception as e:
            logger.error(f"Local inference failed: {e}")
            raw_scores = {}
    else:
        # Remote HF API
        result = _classify_via_hf_api(text)
        if result:
            raw_scores = dict(zip(result.get('labels', []), result.get('scores', [])))
        else:
            raw_scores = {}

    if not raw_scores:
        return {'score': 0.0, 'detections': []}

    # Filter out "neutral" and low-confidence results
    neutral_label = "neutral factual information"
    detections = [
        {'label': label, 'confidence': round(score, 3)}
        for label, score in raw_scores.items()
        if label != neutral_label and score > 0.4
    ]
    detections.sort(key=lambda x: x['confidence'], reverse=True)

    # Score = max confidence among non-neutral narratives
    neutral_score = raw_scores.get(neutral_label, 0.5)
    ipso_score = max((d['confidence'] for d in detections), default=0.0)

    # Adjust: if model is very confident it's neutral, reduce IPSO score
    final_score = ipso_score * (1 - neutral_score * 0.5)

    return {
        'score': round(final_score, 3),
        'detections': detections[:3],  # Top 3 narratives
    }
```

### apps/analyzer/similarity.py
```python
"""
Cosine similarity against known IPSO narratives from the database.
Uses sentence-transformers to create embeddings.
"""
import json
import logging
import numpy as np
from django.conf import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Lazy load sentence transformer model."""
    global _model

    if _model is not None:
        return _model

    if not settings.USE_LOCAL_BERT:
        return None

    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence transformer model...")
        _model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("Sentence transformer loaded.")
    except Exception as e:
        logger.error(f"Failed to load sentence transformer: {e}")

    return _model


def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(vec_a)
    b = np.array(vec_b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def analyze_similarity(text: str) -> dict:
    """
    Compare text against known IPSO narratives in the database.

    Returns:
        {
            'score': float,
            'matches': [{'title': str, 'category': str, 'similarity': float}]
        }
    """
    from apps.core.models import KnownNarrative

    model = _get_model()
    if model is None:
        return {'score': 0.0, 'matches': []}

    try:
        # Encode input text
        text_embedding = model.encode(text).tolist()

        # Get all active narratives with stored embeddings
        narratives = KnownNarrative.objects.filter(is_active=True).exclude(embedding=None)

        if not narratives.exists():
            logger.warning("No narratives with embeddings found in database.")
            return {'score': 0.0, 'matches': []}

        matches = []
        for narrative in narratives:
            sim = cosine_similarity(text_embedding, narrative.embedding)
            if sim > 0.55:  # Only keep meaningful matches
                matches.append({
                    'id': narrative.id,
                    'title': narrative.title,
                    'category': narrative.category,
                    'similarity': round(sim, 3),
                })

        matches.sort(key=lambda x: x['similarity'], reverse=True)
        top_matches = matches[:3]

        score = max((m['similarity'] for m in top_matches), default=0.0)

        return {
            'score': round(score, 3),
            'matches': top_matches,
        }

    except Exception as e:
        logger.error(f"Similarity analysis failed: {e}")
        return {'score': 0.0, 'matches': []}


def compute_and_store_embeddings():
    """
    Management command helper: compute embeddings for all KnownNarrative entries.
    Call this once after seeding the database.
    """
    from apps.core.models import KnownNarrative

    model = _get_model()
    if model is None:
        logger.error("Cannot compute embeddings: model not loaded.")
        return

    narratives = KnownNarrative.objects.filter(embedding=None, is_active=True)
    count = 0

    for narrative in narratives:
        # Combine title + description for richer embedding
        text = f"{narrative.title}. {narrative.description}"
        embedding = model.encode(text).tolist()
        narrative.embedding = embedding
        narrative.save(update_fields=['embedding'])
        count += 1

    logger.info(f"Computed embeddings for {count} narratives.")
    return count
```

### apps/analyzer/pipeline.py
```python
"""
Main analysis orchestrator.
This is the single entry point for all content analysis.
All other modules are called from here.
"""
import time
import logging
from django.conf import settings

from .translator import preprocess
from .rhetoric import analyze_rhetoric
from .narrative import analyze_narratives
from .similarity import analyze_similarity
from .constants import MIN_TEXT_LENGTH

logger = logging.getLogger(__name__)


def get_verdict(score: float) -> str:
    """Determine verdict based on final score."""
    if score >= settings.IPSO_SCORE_SUSPICIOUS:
        return 'ipso'
    elif score >= settings.IPSO_SCORE_SAFE:
        return 'suspicious'
    return 'safe'


def analyze(text: str, source: str = 'api') -> dict:
    """
    Full analysis pipeline.

    Args:
        text: Raw input text (any language)
        source: 'telegram', 'api', or 'web'

    Returns:
        Complete analysis result dict matching AnalysisResult model structure.
    """
    start_time = time.time()

    # Basic validation
    if not text or len(text.strip()) < MIN_TEXT_LENGTH:
        return {
            'error': f'Text too short. Minimum {MIN_TEXT_LENGTH} characters required.',
            'original_text': text,
        }

    # Step 1: Preprocess (detect language, translate)
    preprocessed = preprocess(text)
    translated = preprocessed['translated']
    detected_lang = preprocessed['detected_language']

    logger.info(f"Analyzing text [{detected_lang}] length={len(text)} source={source}")

    # Step 2: Run all analyzers
    weights = settings.ANALYZER_WEIGHTS

    rhetoric_result = analyze_rhetoric(translated)
    narrative_result = analyze_narratives(translated)
    similarity_result = analyze_similarity(translated)

    # Step 3: Weighted ensemble score
    final_score = (
        narrative_result['score'] * weights['narrative'] +
        rhetoric_result['score'] * weights['rhetoric'] +
        similarity_result['score'] * weights['similarity']
    )
    final_score = round(min(final_score, 1.0), 3)

    verdict = get_verdict(final_score)
    processing_time = int((time.time() - start_time) * 1000)

    result = {
        'original_text': text,
        'detected_language': detected_lang,
        'translated_text': translated if detected_lang != 'en' else '',
        'source': source,

        'narrative_score': narrative_result['score'],
        'rhetoric_score': rhetoric_result['score'],
        'similarity_score': similarity_result['score'],
        'final_score': final_score,

        'verdict': verdict,
        'detected_narratives': narrative_result.get('detections', []),
        'detected_rhetoric': rhetoric_result.get('detections', []),
        'similar_narratives': similarity_result.get('matches', []),

        'processing_time_ms': processing_time,
    }

    logger.info(f"Analysis complete: verdict={verdict} score={final_score} time={processing_time}ms")
    return result


def analyze_and_save(text: str, source: str = 'api') -> 'AnalysisResult':
    """
    Run analysis and persist result to database.
    Returns the saved AnalysisResult instance.
    """
    from apps.core.models import AnalysisResult

    result_data = analyze(text, source=source)

    if 'error' in result_data:
        raise ValueError(result_data['error'])

    instance = AnalysisResult.objects.create(**result_data)
    return instance
```

### apps/analyzer/tasks.py
```python
"""
Celery async tasks for analysis.
Used by the Telegram bot to avoid blocking webhook responses.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def analyze_content_task(self, text: str, chat_id: int, message_id: int,
                          username: str = '', source: str = 'telegram'):
    """
    Async task: analyze content and send result back to Telegram user.

    This task is triggered by the webhook handler and runs in a Celery worker.
    """
    try:
        from apps.analyzer.pipeline import analyze_and_save
        from apps.core.models import TelegramAnalysis
        from apps.bot.formatters import format_result_message
        from apps.bot.keyboards import feedback_keyboard
        import asyncio
        from telegram import Bot
        from django.conf import settings

        # Run analysis
        result = analyze_and_save(text, source=source)

        # Link to Telegram interaction
        TelegramAnalysis.objects.create(
            result=result,
            chat_id=chat_id,
            message_id=message_id,
            username=username or '',
        )

        # Send result back to user
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        message_text = format_result_message(result)
        keyboard = feedback_keyboard(result.id)

        asyncio.run(bot.send_message(
            chat_id=chat_id,
            text=message_text,
            parse_mode='HTML',
            reply_markup=keyboard,
            reply_to_message_id=message_id,
        ))

    except ValueError as e:
        # Text too short or validation error — inform user
        import asyncio
        from telegram import Bot
        from django.conf import settings

        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        asyncio.run(bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ {str(e)}",
            reply_to_message_id=message_id,
        ))

    except Exception as exc:
        logger.error(f"analyze_content_task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)
```

---

## 9. Telegram Bot

### apps/bot/keyboards.py
```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def feedback_keyboard(result_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for user feedback on analysis result."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍 Правильно", callback_data=f"feedback:correct:{result_id}"),
            InlineKeyboardButton("👎 Помилка", callback_data=f"feedback:wrong:{result_id}"),
        ]
    ])
```

### apps/bot/formatters.py
```python
"""
Format AnalysisResult into a human-readable Telegram HTML message.
"""

VERDICT_EMOJI = {
    'safe': '✅',
    'suspicious': '⚠️',
    'ipso': '🚨',
}

VERDICT_LABEL = {
    'safe': 'Безпечний контент',
    'suspicious': 'Підозрілий контент',
    'ipso': 'Виявлено ознаки ІПСО',
}

NARRATIVE_LABELS_UA = {
    'demoralization of Ukrainian soldiers and civilians': 'Деморалізація',
    'distrust in Ukrainian government and institutions': 'Підрив довіри до влади',
    'false equivalence between Ukraine and Russia': 'Хибна рівність',
    'panic about imminent military defeat': 'Паніка та страх',
    'exaggerated Ukrainian military losses': 'Перебільшення втрат ЗСУ',
    'claim that Western support is ending': 'Захід відмовляється від України',
    'corruption accusations against Ukrainian leadership': 'Звинувачення у корупції',
}

RHETORIC_LABELS_UA = {
    'whataboutism': 'Whataboutism',
    'false_authority': 'Вигаданий авторитет',
    'fear_panic': 'Нагнітання страху',
    'demoralization': 'Деморалізація',
    'false_equivalence': 'Хибна рівність',
    'cherry_picking': 'Вирваний з контексту факт',
}


def format_result_message(result) -> str:
    """Format AnalysisResult model instance to HTML Telegram message."""

    emoji = VERDICT_EMOJI.get(result.verdict, '❓')
    label = VERDICT_LABEL.get(result.verdict, result.verdict)
    score_pct = int(result.final_score * 100)

    lines = [
        f"{emoji} <b>{label}</b> ({score_pct}%)",
        "",
    ]

    # Module scores bar
    lines.append("<b>Деталі аналізу:</b>")
    lines.append(f"  Наративи: {int(result.narrative_score * 100)}%")
    lines.append(f"  Риторика: {int(result.rhetoric_score * 100)}%")
    lines.append(f"  База наративів: {int(result.similarity_score * 100)}%")

    # Detected narratives
    if result.detected_narratives:
        lines.append("")
        lines.append("📌 <b>Виявлені наративи:</b>")
        for n in result.detected_narratives[:3]:
            label_ua = NARRATIVE_LABELS_UA.get(n['label'], n['label'])
            conf = int(n['confidence'] * 100)
            lines.append(f"  • {label_ua} ({conf}%)")

    # Detected rhetoric
    if result.detected_rhetoric:
        lines.append("")
        lines.append("🎭 <b>Маніпулятивні техніки:</b>")
        for r in result.detected_rhetoric[:3]:
            label_ua = RHETORIC_LABELS_UA.get(r['type'], r['type'])
            lines.append(f"  • {label_ua}")
            if r.get('snippet'):
                snippet = r['snippet'][:60].strip()
                lines.append(f"    <i>«{snippet}...»</i>")

    # Similar known narratives
    if result.similar_narratives:
        lines.append("")
        lines.append("🔗 <b>Схожість з відомими кампаніями:</b>")
        for s in result.similar_narratives[:2]:
            sim = int(s['similarity'] * 100)
            lines.append(f"  • {s['title']} ({sim}%)")

    lines.append("")
    lines.append(f"<i>Мова оригіналу: {result.detected_language} · "
                 f"Час аналізу: {result.processing_time_ms}ms</i>")

    return "\n".join(lines)
```

### apps/bot/handlers.py
```python
"""
Telegram bot command and message handlers.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from django.conf import settings

logger = logging.getLogger(__name__)

HELP_TEXT = """
🔍 <b>ІПСО Детектор</b>

Я аналізую текст на ознаки інформаційно-психологічних операцій (ІПСО).

<b>Як користуватись:</b>
• Перешліть підозрілий пост з будь-якого каналу
• Або надішліть текст напряму

<b>Що я аналізую:</b>
• Пропагандистські наративи
• Маніпулятивні риторичні техніки
• Схожість з відомими ІПСО-кампаніями

<b>Команди:</b>
/start — Початок роботи
/help — Ця довідка
/stats — Статистика бота
"""


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        f"Привіт, {update.effective_user.first_name}! 👋\n\n" + HELP_TEXT
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(HELP_TEXT)


async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from apps.core.models import AnalysisResult
    total = AnalysisResult.objects.count()
    ipso_count = AnalysisResult.objects.filter(verdict='ipso').count()
    suspicious_count = AnalysisResult.objects.filter(verdict='suspicious').count()

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"Всього аналізів: {total}\n"
        f"🚨 ІПСО виявлено: {ipso_count}\n"
        f"⚠️ Підозрілих: {suspicious_count}\n"
        f"✅ Безпечних: {total - ipso_count - suspicious_count}"
    )
    await update.message.reply_html(text)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages and forwarded posts."""
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip()
    chat_id = message.chat_id
    message_id = message.message_id
    username = update.effective_user.username or ''

    # Immediately acknowledge
    await message.reply_text("🔍 Аналізую...")

    if settings.USE_CELERY:
        # Async via Celery
        from apps.analyzer.tasks import analyze_content_task
        analyze_content_task.delay(
            text=text,
            chat_id=chat_id,
            message_id=message_id,
            username=username,
            source='telegram',
        )
    else:
        # Synchronous (dev mode)
        from apps.analyzer.pipeline import analyze_and_save
        from apps.bot.formatters import format_result_message
        from apps.bot.keyboards import feedback_keyboard
        from apps.core.models import TelegramAnalysis

        try:
            result = analyze_and_save(text, source='telegram')
            TelegramAnalysis.objects.create(
                result=result,
                chat_id=chat_id,
                message_id=message_id,
                username=username,
            )
            await message.reply_html(
                format_result_message(result),
                reply_markup=feedback_keyboard(result.id),
            )
        except ValueError as e:
            await message.reply_text(f"⚠️ {str(e)}")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard feedback button presses."""
    query = update.callback_query
    await query.answer()

    data = query.data  # e.g. "feedback:correct:42"
    parts = data.split(':')

    if len(parts) == 3 and parts[0] == 'feedback':
        from apps.core.models import Feedback, AnalysisResult

        feedback_type = parts[1]  # 'correct' or 'wrong'
        result_id = int(parts[2])

        try:
            result = AnalysisResult.objects.get(id=result_id)
            Feedback.objects.create(
                result=result,
                feedback_type=feedback_type,
                chat_id=query.message.chat_id,
            )
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text("Дякуємо за відгук! 🙏")
        except AnalysisResult.DoesNotExist:
            logger.warning(f"Feedback for non-existent result id={result_id}")
```

### apps/bot/views.py
```python
"""
Telegram webhook endpoint.
Receives POST requests from Telegram servers and dispatches to handlers.
"""
import json
import logging
import hmac
import hashlib

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_application():
    """Build and return the python-telegram-bot Application (cached)."""
    from telegram import Bot
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        CallbackQueryHandler, filters
    )
    from .handlers import (
        start_handler, help_handler, stats_handler,
        message_handler, callback_handler,
    )

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    return app


@csrf_exempt
@require_POST
def webhook_view(request):
    """
    POST /bot/webhook/<secret>/
    Telegram sends updates here.
    """
    # Validate secret token
    secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        logger.warning("Webhook received with invalid secret token")
        return HttpResponse(status=403)

    try:
        import asyncio
        from telegram import Update

        data = json.loads(request.body)
        app = _get_application()

        # Process update asynchronously
        async def process():
            await app.initialize()
            update = Update.de_json(data, app.bot)
            await app.process_update(update)

        asyncio.run(process())

    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)

    # Always return 200 to Telegram (prevents retry storms)
    return JsonResponse({"ok": True})
```

### apps/bot/urls.py
```python
from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.webhook_view, name='telegram-webhook'),
]
```

---

## 10. REST API

### apps/api/serializers.py
```python
from rest_framework import serializers
from apps.core.models import AnalysisResult


class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisResult
        fields = [
            'id', 'original_text', 'detected_language',
            'narrative_score', 'rhetoric_score', 'similarity_score', 'final_score',
            'verdict', 'detected_narratives', 'detected_rhetoric', 'similar_narratives',
            'processing_time_ms', 'created_at',
        ]
        read_only_fields = fields


class AnalyzeRequestSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=10, max_length=10000)
```

### apps/api/views.py
```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import AnalyzeRequestSerializer, AnalysisResultSerializer


class AnalyzeView(APIView):
    """
    POST /api/analyze/
    Body: {"text": "..."}
    Returns full analysis result.
    """
    def post(self, request):
        serializer = AnalyzeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        text = serializer.validated_data['text']

        try:
            from apps.analyzer.pipeline import analyze_and_save
            result = analyze_and_save(text, source='api')
            return Response(AnalysisResultSerializer(result).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'Analysis failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HistoryView(APIView):
    """GET /api/history/?limit=20"""
    def get(self, request):
        from apps.core.models import AnalysisResult
        limit = min(int(request.query_params.get('limit', 20)), 100)
        results = AnalysisResult.objects.all()[:limit]
        return Response(AnalysisResultSerializer(results, many=True).data)
```

### apps/api/urls.py
```python
from django.urls import path
from . import views

urlpatterns = [
    path('analyze/', views.AnalyzeView.as_view(), name='api-analyze'),
    path('history/', views.HistoryView.as_view(), name='api-history'),
]
```

---

## 11. URL Configuration

### config/urls.py
```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('bot/', include('apps.bot.urls')),
    path('api/', include('apps.api.urls')),
]
```

---

## 12. Initial Data Seed

### data/narratives/known_narratives.json
```json
[
  {
    "title": "ЗСУ зазнають катастрофічних втрат",
    "description": "Narrative claiming Ukrainian military suffers catastrophic losses that are being hidden from public",
    "category": "military_losses",
    "source": "StopFake",
    "example_texts": [
      "Реальні втрати ЗСУ замовчуються владою, насправді загинули десятки тисяч",
      "Украинские потери скрывают от народа, реально погибло намного больше"
    ]
  },
  {
    "title": "Захід втомився від України та скорочує допомогу",
    "description": "Narrative that Western countries are abandoning Ukraine and reducing military/financial support",
    "category": "western_abandonment",
    "source": "VoxCheck",
    "example_texts": [
      "Захід втомився від України, допомога скорочується",
      "European countries are tired of funding Ukraine's war"
    ]
  },
  {
    "title": "Зеленський корумпований і вкрав мільярди",
    "description": "Unfounded corruption accusations against Ukrainian president Zelensky",
    "category": "corruption",
    "source": "StopFake",
    "example_texts": [
      "Зеленський вкрав мільярди іноземної допомоги",
      "Zelensky bought villas in Europe with Western aid money"
    ]
  },
  {
    "title": "Обидві сторони однаково винні у конфлікті",
    "description": "False equivalence narrative claiming Ukraine is equally responsible for the war",
    "category": "false_equivalence",
    "source": "EU DisinfoLab",
    "example_texts": [
      "В цьому конфлікті винні обидві сторони",
      "NATO provoked Russia into this conflict, both sides are guilty"
    ]
  },
  {
    "title": "Опір марний, Україна програє",
    "description": "Demoralization narrative claiming Ukrainian resistance is futile",
    "category": "demoralization",
    "source": "InformNapalm",
    "example_texts": [
      "Опір марний, Україна все одно програє",
      "Resistance is useless, Ukraine cannot win against Russia's army"
    ]
  }
]
```

### Management command to seed narratives: apps/core/management/commands/seed_narratives.py
```python
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from apps.core.models import KnownNarrative
from apps.analyzer.similarity import compute_and_store_embeddings


class Command(BaseCommand):
    help = 'Seed the database with known IPSO narratives and compute embeddings'

    def handle(self, *args, **options):
        data_path = Path('data/narratives/known_narratives.json')

        with open(data_path) as f:
            narratives = json.load(f)

        created = 0
        for item in narratives:
            obj, is_new = KnownNarrative.objects.get_or_create(
                title=item['title'],
                defaults=item,
            )
            if is_new:
                created += 1

        self.stdout.write(f"Created {created} narratives.")
        self.stdout.write("Computing embeddings...")
        count = compute_and_store_embeddings()
        self.stdout.write(self.style.SUCCESS(f"Done. Embeddings computed for {count} narratives."))
```

---

## 13. Deployment

### Systemd service files

**/etc/systemd/system/ipso-gunicorn.service**
```ini
[Unit]
Description=IPSO Detector Gunicorn
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/ipso-detector
ExecStart=/var/www/ipso-detector/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8003 \
    --timeout 120 \
    config.wsgi:application
Restart=on-failure
EnvironmentFile=/var/www/ipso-detector/.env

[Install]
WantedBy=multi-user.target
```

**/etc/systemd/system/ipso-celery.service**
```ini
[Unit]
Description=IPSO Detector Celery Worker
After=network.target redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/ipso-detector
ExecStart=/var/www/ipso-detector/venv/bin/celery \
    -A config worker \
    --loglevel=info \
    --concurrency=2
Restart=on-failure
EnvironmentFile=/var/www/ipso-detector/.env

[Install]
WantedBy=multi-user.target
```

### nginx config

**/etc/nginx/sites-available/ipso-detector**
```nginx
server {
    server_name yourdomain.com;

    location /bot/ {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Telegram-Bot-Api-Secret-Token $http_x_telegram_bot_api_secret_token;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
    }

    location /static/ {
        alias /var/www/ipso-detector/staticfiles/;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}
```

### Register Telegram webhook (run once after deploy)
```bash
curl -X POST \
  "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourdomain.com/bot/webhook/",
    "secret_token": "<YOUR_WEBHOOK_SECRET>"
  }'
```

### First deploy commands
```bash
# On server
git clone https://github.com/youruser/ipso-detector.git /var/www/ipso-detector
cd /var/www/ipso-detector
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/prod.txt
pip install transformers torch sentence-transformers spacy deep-translator langdetect
python -m spacy download en_core_web_sm

# Setup DB
createdb ipso_detector
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --no-input
python manage.py seed_narratives

# Start services
sudo systemctl enable ipso-gunicorn ipso-celery
sudo systemctl start ipso-gunicorn ipso-celery
```

---

## 14. Implementation Order

Implement in this exact order. Each phase is independently testable.

**Phase 1 — Django skeleton + working webhook (no AI)**
1. Create Django project with the structure above
2. Create all models and run migrations
3. Implement `bot/views.py` webhook endpoint (just log and return 200)
4. Implement basic handlers: `/start`, `/help`, echo back received message
5. Test: send message to bot → see it echoed back

**Phase 2 — Rule-based analysis (no ML models)**
1. Implement `analyzer/translator.py`
2. Implement `analyzer/rhetoric.py` with regex patterns
3. Implement `analyzer/pipeline.py` (rhetoric only, skip narrative + similarity)
4. Wire pipeline into bot handler (synchronous, no Celery yet)
5. Implement `bot/formatters.py`
6. Test: send propaganda text → get formatted result with rhetoric detections

**Phase 3 — Celery async**
1. Set up Redis
2. Implement `analyzer/tasks.py`
3. Switch bot handler to use `analyze_content_task.delay()`
4. Implement feedback callback handler
5. Test: full async flow with feedback buttons

**Phase 4 — BERT narrative classifier**
1. Implement `analyzer/narrative.py` with zero-shot classification
2. Start with HF Inference API (USE_LOCAL_BERT=False)
3. Integrate into pipeline with weights
4. Test: compare rhetoric-only vs full pipeline results

**Phase 5 — Similarity against known narratives**
1. Implement `analyzer/similarity.py`
2. Create and run `seed_narratives` management command
3. Integrate similarity into pipeline
4. Test: send text similar to a seeded narrative → check similarity score

**Phase 6 — REST API**
1. Implement `api/views.py` and `api/serializers.py`
2. Test with curl or Postman

**Phase 7 — Deploy to DigitalOcean**
1. Create droplet (Ubuntu 24.04, 4GB RAM, Frankfurt)
2. Configure nginx + SSL
3. Set up systemd services
4. Register Telegram webhook
5. Run seed_narratives on server

---

## 15. Testing

### Quick test for rhetoric module (no models needed)
```python
# Run in Django shell: python manage.py shell
from apps.analyzer.rhetoric import analyze_rhetoric

test_texts = [
    "Обидві сторони однаково винні у цьому конфлікті",
    "За даними джерел у Генштабі, реальні втрати ЗСУ набагато більші",
    "Це просто новина про погоду в Києві",
]

for text in test_texts:
    from apps.analyzer.translator import translate_to_english
    translated = translate_to_english(text)
    result = analyze_rhetoric(translated)
    print(f"\nText: {text[:50]}")
    print(f"Score: {result['score']}")
    print(f"Detections: {result['detections']}")
```

### Quick test for full pipeline
```python
from apps.analyzer.pipeline import analyze

result = analyze("Зеленський вкрав мільярди, опір марний, Захід нас кидає")
print(f"Verdict: {result['verdict']}")
print(f"Score: {result['final_score']}")
print(f"Rhetoric: {result['detected_rhetoric']}")
```

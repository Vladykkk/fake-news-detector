"""
Language detection and translation module.
Uses DeepL API (primary) with Google Translate fallback.
Translates any input text to English for unified analysis.
"""
import logging
import requests
from django.conf import settings
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

# DeepL source language mapping (langdetect code → DeepL code)
DEEPL_LANG_MAP = {
    'uk': 'UK',
    'ru': 'RU',
    'en': 'EN',
    'de': 'DE',
    'fr': 'FR',
    'pl': 'PL',
    'es': 'ES',
    'it': 'IT',
    'pt': 'PT',
    'nl': 'NL',
    'ja': 'JA',
    'zh-cn': 'ZH',
    'zh-tw': 'ZH',
}


def detect_language(text: str) -> str:
    """Detect language code of text. Returns 'unknown' on failure."""
    try:
        return detect(text)
    except LangDetectException:
        return 'unknown'


def _translate_deepl(text: str, source_lang: str = 'auto') -> str | None:
    """
    Translate text to English using DeepL API.

    Returns translated text on success, None on failure.
    Supports both DeepL Free and Pro API endpoints.
    """
    api_key = getattr(settings, 'DEEPL_API_KEY', '')
    if not api_key:
        return None

    # DeepL Free keys end with ':fx', use free endpoint
    if api_key.endswith(':fx'):
        base_url = 'https://api-free.deepl.com/v2/translate'
    else:
        base_url = 'https://api.deepl.com/v2/translate'

    params = {
        'text': [text],
        'target_lang': 'EN',
    }

    # Map detected language to DeepL code if available
    deepl_source = DEEPL_LANG_MAP.get(source_lang)
    if deepl_source and deepl_source != 'EN':
        params['source_lang'] = deepl_source

    try:
        response = requests.post(
            base_url,
            headers={
                'Authorization': f'DeepL-Auth-Key {api_key}',
                'Content-Type': 'application/json',
            },
            json=params,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        translated = data['translations'][0]['text']
        logger.info(
            "DeepL translation OK: %s → EN, chars=%d",
            data['translations'][0].get('detected_source_language', source_lang),
            len(translated),
        )
        return translated

    except requests.RequestException as e:
        logger.warning("DeepL API failed: %s", e)
        return None
    except (KeyError, IndexError) as e:
        logger.warning("DeepL unexpected response: %s", e)
        return None


def _translate_google(text: str) -> str | None:
    """
    Fallback: translate via deep-translator (Google Translate).
    Returns translated text on success, None on failure.
    """
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        if translated:
            logger.info("Google Translate fallback OK, chars=%d", len(translated))
            return translated
        return None
    except Exception as e:
        logger.warning("Google Translate fallback failed: %s", e)
        return None


def translate_to_english(text: str, source_lang: str = 'auto') -> str:
    """
    Translate text to English.
    Strategy: DeepL API → Google Translate fallback → original text.
    Returns original text if both fail or language is already English.
    """
    if source_lang == 'en':
        return text

    # Try DeepL first
    translated = _translate_deepl(text, source_lang)
    if translated:
        return translated

    # Fallback to Google Translate
    translated = _translate_google(text)
    if translated:
        return translated

    logger.warning("All translators failed. Using original text.")
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

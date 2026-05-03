"""
LLM-based narrative classifier using OpenRouter API.
Sends a zero-shot classification prompt to identify IPSO narrative categories.
"""
import json
import logging
import requests
from django.conf import settings
from .constants import NARRATIVE_LABELS

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are an expert analyst specializing in identifying Russian information-psychological operations (IPSO) targeting Ukraine.

Analyze the following text and determine if it contains any of these IPSO narrative categories:
1. demoralization — attempts to break the spirit of Ukrainians or their military
2. distrust_institutions — undermining trust in Ukrainian government, military leadership, or institutions
3. false_equivalence — equating Ukraine with Russia or suggesting "both sides are equally bad"
4. panic_fear — spreading panic about imminent defeat, collapse, or catastrophe
5. military_losses_exaggeration — exaggerating Ukrainian military losses or minimizing Russian losses
6. western_abandonment — claiming Western countries are abandoning Ukraine
7. corruption_accusation — accusing Ukrainian leadership of corruption to undermine trust

Respond ONLY with a JSON object in this exact format:
{
  "is_ipso": true/false,
  "narratives": [{"label": "category_name", "confidence": 0.0-1.0}],
  "reasoning": "brief explanation"
}

If the text is neutral/safe, return {"is_ipso": false, "narratives": [], "reasoning": "explanation"}.

TEXT TO ANALYZE:
"""


def analyze_narratives(text: str) -> dict:
    """
    Classify text against known IPSO narrative categories using LLM.

    Args:
        text: English-translated text (truncated to 1500 chars)

    Returns:
        {
            'score': float (0.0 – 1.0),
            'detections': [{'label': str, 'confidence': float}],
            'reasoning': str,
        }
    """
    text = text[:1500]

    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    model = getattr(settings, 'OPENROUTER_MODEL', 'google/gemini-2.0-flash-001')

    if not api_key or api_key == 'placeholder':
        logger.warning("OpenRouter API key not configured. Returning zero score.")
        return {'score': 0.0, 'detections': [], 'reasoning': 'API key not configured'}

    logger.info(
        "Calling OpenRouter: model=%s, key_prefix=%s..., text_len=%d",
        model, api_key[:10], len(text),
    )

    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': [
                    {'role': 'user', 'content': CLASSIFICATION_PROMPT + text}
                ],
                'temperature': 0.1,
                'max_tokens': 500,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        # Log usage info returned by OpenRouter for debugging
        usage = data.get('usage', {})
        logger.info(
            "OpenRouter response: model=%s, prompt_tokens=%s, completion_tokens=%s, total_tokens=%s",
            data.get('model', '?'),
            usage.get('prompt_tokens', '?'),
            usage.get('completion_tokens', '?'),
            usage.get('total_tokens', '?'),
        )

        content = data['choices'][0]['message']['content']
        # Parse JSON from response (handle markdown code blocks)
        content = content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].rsplit('```', 1)[0]

        result = json.loads(content)

        detections = []
        for narr in result.get('narratives', []):
            label = narr.get('label', '')
            if label in NARRATIVE_LABELS:
                detections.append({
                    'label': label,
                    'confidence': float(narr.get('confidence', 0.5)),
                })

        # Score: average confidence of detected narratives, or 0
        if detections:
            score = sum(d['confidence'] for d in detections) / len(detections)
        else:
            score = 0.0

        # Boost score if is_ipso flag is explicitly True
        if result.get('is_ipso') and score < 0.3:
            score = 0.3

        return {
            'score': round(min(score, 1.0), 3),
            'detections': detections,
            'reasoning': result.get('reasoning', ''),
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return {'score': 0.0, 'detections': [], 'reasoning': f'Parse error: {e}'}
    except requests.RequestException as e:
        logger.error(f"OpenRouter API call failed: {e}")
        return {'score': 0.0, 'detections': [], 'reasoning': f'API error: {e}'}
    except Exception as e:
        logger.error(f"Narrative analysis failed: {e}")
        return {'score': 0.0, 'detections': [], 'reasoning': f'Error: {e}'}

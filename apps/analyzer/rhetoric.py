"""
Rule-based rhetorical manipulation detector.
Uses regex patterns on both original and translated text.
No ML model required — runs fast.
"""
import re
import logging
from .constants import RHETORIC_PATTERNS_EN, RHETORIC_PATTERNS_UK

logger = logging.getLogger(__name__)


def _scan_patterns(text: str, patterns: dict) -> list:
    """Scan text against a set of rhetoric patterns."""
    text_lower = text.lower()
    detections = []
    matched_types = set()

    for pattern_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text_lower)
            if match and pattern_type not in matched_types:
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                snippet = text[start:end].strip()

                detections.append({
                    'type': pattern_type,
                    'snippet': snippet,
                    'confidence': 0.75,
                })
                matched_types.add(pattern_type)
                break

    return detections


def analyze_rhetoric(text: str, language: str = 'en') -> dict:
    """
    Scan text for rhetorical manipulation patterns.
    Uses both English and Ukrainian patterns for maximum coverage.

    Args:
        text: Text to analyze
        language: Detected language of the text ('uk', 'en', etc.)

    Returns:
        {
            'score': float (0.0 – 1.0),
            'detections': [{'type': str, 'snippet': str, 'confidence': float}]
        }
    """
    all_detections = []
    matched_types = set()

    # Always try Ukrainian patterns on original text
    uk_detections = _scan_patterns(text, RHETORIC_PATTERNS_UK)
    for d in uk_detections:
        if d['type'] not in matched_types:
            all_detections.append(d)
            matched_types.add(d['type'])

    # Also try English patterns (useful when text is translated or in English)
    en_detections = _scan_patterns(text, RHETORIC_PATTERNS_EN)
    for d in en_detections:
        if d['type'] not in matched_types:
            all_detections.append(d)
            matched_types.add(d['type'])

    # Score: each unique type found adds to the score, max 1.0
    score = min(len(matched_types) / 3.0, 1.0)

    logger.debug(
        'Rhetoric analysis: %d types detected, score=%.3f',
        len(matched_types), score,
    )

    return {
        'score': round(score, 3),
        'detections': all_detections,
    }

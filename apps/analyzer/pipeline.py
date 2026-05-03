"""
Main analysis pipeline orchestrator.
Combines all three analysis modules into an ensemble score.
"""
import time
import logging
from django.conf import settings
from apps.core.models import AnalysisResult
from .constants import MIN_TEXT_LENGTH
from .translator import preprocess
from .rhetoric import analyze_rhetoric
from .narrative import analyze_narratives
from .similarity import analyze_similarity

logger = logging.getLogger(__name__)


def analyze_text(text: str, source: str = 'api') -> AnalysisResult:
    """
    Full analysis pipeline: preprocess → 3 modules → ensemble → save.

    Args:
        text: Raw input text (any language)
        source: Origin of request ('telegram', 'api', 'web')

    Returns:
        AnalysisResult instance (saved to database)
    """
    start_time = time.time()

    # Validate minimum length
    text = text.strip()
    if len(text) < MIN_TEXT_LENGTH:
        result = AnalysisResult.objects.create(
            original_text=text,
            source=source,
            verdict=AnalysisResult.Verdict.SAFE,
            final_score=0.0,
            processing_time_ms=0,
        )
        return result

    # Step 1: Language detection + translation
    preprocessed = preprocess(text)

    # Step 2: Run three analysis modules
    rhetoric_result = analyze_rhetoric(
        preprocessed['translated'],
        language=preprocessed['detected_language'],
    )
    narrative_result = analyze_narratives(preprocessed['translated'])
    similarity_result = analyze_similarity(preprocessed['original'])

    # Step 3: Ensemble scoring (weighted combination)
    weights = settings.ANALYZER_WEIGHTS
    final_score = (
        weights['narrative'] * narrative_result['score']
        + weights['rhetoric'] * rhetoric_result['score']
        + weights['similarity'] * similarity_result['score']
    )
    final_score = round(min(final_score, 1.0), 3)

    # Step 4: Determine verdict
    if final_score >= settings.IPSO_SCORE_SUSPICIOUS:
        verdict = AnalysisResult.Verdict.IPSO
    elif final_score >= settings.IPSO_SCORE_SAFE:
        verdict = AnalysisResult.Verdict.SUSPICIOUS
    else:
        verdict = AnalysisResult.Verdict.SAFE

    # Step 5: Calculate processing time
    processing_time_ms = int((time.time() - start_time) * 1000)

    # Step 6: Save to database
    result = AnalysisResult.objects.create(
        original_text=text,
        detected_language=preprocessed['detected_language'],
        translated_text=preprocessed['translated'],
        source=source,
        narrative_score=narrative_result['score'],
        rhetoric_score=rhetoric_result['score'],
        similarity_score=similarity_result['score'],
        final_score=final_score,
        verdict=verdict,
        detected_narratives=narrative_result.get('detections', []),
        detected_rhetoric=rhetoric_result.get('detections', []),
        similar_narratives=similarity_result.get('similar_narratives', []),
        processing_time_ms=processing_time_ms,
    )

    logger.info(
        f"Analysis complete: verdict={verdict}, score={final_score}, "
        f"time={processing_time_ms}ms, source={source}"
    )

    return result

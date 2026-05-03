"""
Semantic similarity module.
Compares input text embedding against known IPSO narrative embeddings.
Uses sentence-transformers for fast local inference.
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Lazy load the sentence-transformers model."""
    global _model
    if _model is not None:
        return _model

    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers model...")
        _model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("Model loaded successfully.")
        return _model
    except Exception as e:
        logger.error(f"Failed to load sentence-transformers model: {e}")
        return None


def compute_embedding(text: str) -> list:
    """Compute embedding vector for a text string."""
    model = _get_model()
    if model is None:
        return []

    try:
        embedding = model.encode(text, show_progress_bar=False)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Embedding computation failed: {e}")
        return []


def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """Compute cosine similarity between two vectors."""
    if not vec_a or not vec_b:
        return 0.0

    a = np.array(vec_a)
    b = np.array(vec_b)

    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot / (norm_a * norm_b))


def analyze_similarity(text: str) -> dict:
    """
    Compare text against known IPSO narratives from database.

    Args:
        text: Text to analyze (can be in any language)

    Returns:
        {
            'score': float (0.0 – 1.0),
            'similar_narratives': [{'id': int, 'title': str, 'similarity': float}]
        }
    """
    from apps.core.models import KnownNarrative

    text_embedding = compute_embedding(text)
    if not text_embedding:
        return {'score': 0.0, 'similar_narratives': []}

    narratives = KnownNarrative.objects.filter(
        is_active=True,
        embedding__isnull=False,
    )

    similarities = []
    for narrative in narratives:
        if not narrative.embedding:
            continue

        sim = cosine_similarity(text_embedding, narrative.embedding)
        if sim >= 0.55:  # Threshold for "similar enough"
            similarities.append({
                'id': narrative.id,
                'title': narrative.title,
                'category': narrative.category,
                'similarity': round(sim, 3),
            })

    # Sort by similarity descending
    similarities.sort(key=lambda x: x['similarity'], reverse=True)
    top_matches = similarities[:5]

    # Score: max similarity found, or 0
    score = top_matches[0]['similarity'] if top_matches else 0.0

    return {
        'score': round(min(score, 1.0), 3),
        'similar_narratives': top_matches,
    }

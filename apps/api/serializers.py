from rest_framework import serializers
from apps.core.models import AnalysisResult, Feedback, KnownNarrative


class AnalyzeRequestSerializer(serializers.Serializer):
    """Вхідний серіалізатор для запитів на аналіз."""
    text = serializers.CharField(
        min_length=30,
        max_length=10000,
        help_text='Текст для аналізу (30–10000 символів)',
    )


class AnalysisResultSerializer(serializers.ModelSerializer):
    """Повний серіалізатор результату аналізу."""
    verdict_display = serializers.CharField(
        source='get_verdict_display', read_only=True
    )

    class Meta:
        model = AnalysisResult
        fields = [
            'id', 'original_text', 'detected_language', 'translated_text',
            'source', 'narrative_score', 'rhetoric_score', 'similarity_score',
            'final_score', 'verdict', 'verdict_display',
            'detected_narratives', 'detected_rhetoric', 'similar_narratives',
            'processing_time_ms', 'created_at',
        ]
        read_only_fields = fields


class AnalysisResultListSerializer(serializers.ModelSerializer):
    """Компактний серіалізатор для списку результатів."""
    verdict_display = serializers.CharField(
        source='get_verdict_display', read_only=True
    )

    class Meta:
        model = AnalysisResult
        fields = [
            'id', 'verdict', 'verdict_display', 'final_score',
            'detected_language', 'source', 'processing_time_ms', 'created_at',
        ]
        read_only_fields = fields


class FeedbackSerializer(serializers.ModelSerializer):
    """Серіалізатор для зворотного зв'язку."""

    class Meta:
        model = Feedback
        fields = ['id', 'result', 'feedback_type', 'chat_id', 'created_at']
        read_only_fields = ['id', 'created_at']


class KnownNarrativeSerializer(serializers.ModelSerializer):
    """Серіалізатор для відомих ІПСО-наративів."""
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )

    class Meta:
        model = KnownNarrative
        fields = [
            'id', 'title', 'description', 'category', 'category_display',
            'example_texts', 'source', 'is_active', 'created_at',
        ]
        read_only_fields = fields

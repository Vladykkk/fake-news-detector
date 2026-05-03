from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.models import AnalysisResult, Feedback, KnownNarrative
from .serializers import (
    AnalyzeRequestSerializer,
    AnalysisResultSerializer,
    AnalysisResultListSerializer,
    FeedbackSerializer,
    KnownNarrativeSerializer,
)


class AnalysisViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    """
    ViewSet для аналізу текстів.

    list:    GET  /api/analysis/          — список усіх результатів
    retrieve: GET  /api/analysis/{id}/     — деталі одного результату
    create:  POST /api/analysis/          — новий аналіз (приймає {text})
    stats:   GET  /api/analysis/stats/    — зведена статистика
    """
    queryset = AnalysisResult.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['verdict', 'source', 'detected_language']
    search_fields = ['original_text']
    ordering_fields = ['created_at', 'final_score']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return AnalysisResultListSerializer
        if self.action == 'create':
            return AnalyzeRequestSerializer
        return AnalysisResultSerializer

    def create(self, request, *args, **kwargs):
        """POST /api/analysis/ — запуск нового аналізу."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data['text']

        if settings.USE_CELERY:
            from apps.analyzer.tasks import analyze_content_task
            task = analyze_content_task.delay(text, source='api')
            return Response(
                {'task_id': task.id, 'status': 'processing'},
                status=status.HTTP_202_ACCEPTED,
            )

        from apps.analyzer.pipeline import analyze_text
        result = analyze_text(text, source='api')
        return Response(
            AnalysisResultSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """GET /api/analysis/stats/ — зведена статистика."""
        from django.db.models import Count, Avg

        qs = self.get_queryset()
        total = qs.count()
        by_verdict = dict(
            qs.values_list('verdict')
            .annotate(cnt=Count('id'))
            .values_list('verdict', 'cnt')
        )
        avg_score = qs.aggregate(avg=Avg('final_score'))['avg'] or 0

        return Response({
            'total_analyses': total,
            'by_verdict': {
                'safe': by_verdict.get('safe', 0),
                'suspicious': by_verdict.get('suspicious', 0),
                'ipso': by_verdict.get('ipso', 0),
            },
            'average_score': round(avg_score, 3),
        })


class FeedbackViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    """
    list:   GET  /api/feedback/   — список відгуків
    create: POST /api/feedback/   — новий відгук
    """
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['feedback_type']


class KnownNarrativeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:     GET /api/narratives/       — список відомих наративів
    retrieve: GET /api/narratives/{id}/  — деталі наративу
    """
    queryset = KnownNarrative.objects.filter(is_active=True)
    serializer_class = KnownNarrativeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category']
    search_fields = ['title', 'description']

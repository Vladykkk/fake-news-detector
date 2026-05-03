"""Tests for the web dashboard views."""
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse

from apps.core.models import AnalysisResult


class WebViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_index_page_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'IPSO Detector')
        self.assertContains(response, 'Аналізувати')

    def test_history_empty(self):
        response = self.client.get('/history/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Поки що немає результатів')

    def test_history_with_results(self):
        AnalysisResult.objects.create(
            original_text='a'*50, verdict='safe', final_score=0.15,
            detected_language='uk', source='web', processing_time_ms=120,
        )
        response = self.client.get('/history/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Безпечно')
        self.assertContains(response, '15.0%')

    def test_result_detail_page(self):
        obj = AnalysisResult.objects.create(
            original_text='Test text for detail view', verdict='ipso',
            final_score=0.85, detected_language='uk',
        )
        response = self.client.get(f'/result/{obj.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ІПСО виявлено')
        self.assertContains(response, '85.0%')

    def test_result_detail_not_found(self):
        response = self.client.get('/result/99999/')
        self.assertEqual(response.status_code, 404)

    def test_analyze_post_too_short(self):
        response = self.client.post('/analyze/', {'text': 'короткий'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'занадто короткий')

    @patch('apps.analyzer.pipeline.analyze_similarity')
    @patch('apps.analyzer.pipeline.analyze_narratives')
    def test_analyze_post_success(self, mock_narratives, mock_similarity):
        mock_narratives.return_value = {'score': 0.0, 'detections': []}
        mock_similarity.return_value = {'score': 0.0, 'similar_narratives': []}

        response = self.client.post('/analyze/', {
            'text': 'Це текст для перевірки обробки форми який має достатньо слів.',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AnalysisResult.objects.count(), 1)
        result = AnalysisResult.objects.first()
        self.assertEqual(result.source, 'web')

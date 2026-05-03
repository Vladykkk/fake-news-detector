"""Tests for the REST API endpoints."""
from unittest.mock import patch
from rest_framework.test import APITestCase
from rest_framework import status

from apps.core.models import AnalysisResult, KnownNarrative, Feedback


class AnalysisAPITests(APITestCase):
    """Tests for /api/analysis/ endpoints."""

    @patch('apps.analyzer.pipeline.analyze_similarity')
    @patch('apps.analyzer.pipeline.analyze_narratives')
    def test_create_analysis(self, mock_narratives, mock_similarity):
        """POST /api/analysis/ should create a new analysis."""
        mock_narratives.return_value = {'score': 0.0, 'detections': []}
        mock_similarity.return_value = {'score': 0.0, 'similar_narratives': []}

        payload = {
            'text': 'Це звичайний текст для аналізу який має достатню довжину для обробки.',
            'source': 'api',
        }
        response = self.client.post('/api/analysis/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertIn('verdict', response.data)
        self.assertIn('final_score', response.data)
        self.assertEqual(AnalysisResult.objects.count(), 1)

    def test_create_analysis_text_too_short(self):
        """Short text should be rejected by serializer validation."""
        payload = {'text': 'Короткий', 'source': 'api'}
        response = self.client.post('/api/analysis/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_analyses(self):
        """GET /api/analysis/ should return paginated list."""
        AnalysisResult.objects.create(
            original_text='test1', verdict='safe', final_score=0.2,
        )
        AnalysisResult.objects.create(
            original_text='test2', verdict='ipso', final_score=0.85,
        )

        response = self.client.get('/api/analysis/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_retrieve_analysis(self):
        obj = AnalysisResult.objects.create(
            original_text='sample text for retrieval test',
            verdict='suspicious', final_score=0.5,
        )
        response = self.client.get(f'/api/analysis/{obj.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], obj.id)

    def test_stats_endpoint(self):
        """GET /api/analysis/stats/ should return aggregate statistics."""
        AnalysisResult.objects.create(original_text='a'*30, verdict='safe', final_score=0.1)
        AnalysisResult.objects.create(original_text='b'*30, verdict='ipso', final_score=0.9)
        AnalysisResult.objects.create(original_text='c'*30, verdict='suspicious', final_score=0.5)

        response = self.client.get('/api/analysis/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_analyses'], 3)
        self.assertIn('by_verdict', response.data)
        self.assertEqual(response.data['by_verdict']['safe'], 1)
        self.assertEqual(response.data['by_verdict']['ipso'], 1)
        self.assertEqual(response.data['by_verdict']['suspicious'], 1)
        self.assertAlmostEqual(response.data['average_score'], 0.5, places=1)


class FeedbackAPITests(APITestCase):
    """Tests for /api/feedback/ endpoints."""

    def setUp(self):
        self.result = AnalysisResult.objects.create(
            original_text='sample', verdict='ipso', final_score=0.8,
        )

    def test_create_feedback(self):
        payload = {
            'result': self.result.id,
            'feedback_type': 'correct',
            'chat_id': 12345,
        }
        response = self.client.post('/api/feedback/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Feedback.objects.count(), 1)

    def test_list_feedback(self):
        Feedback.objects.create(
            result=self.result, feedback_type='correct', chat_id=1,
        )
        Feedback.objects.create(
            result=self.result, feedback_type='wrong', chat_id=2,
        )

        response = self.client.get('/api/feedback/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)


class KnownNarrativeAPITests(APITestCase):
    """Tests for /api/narratives/ endpoints."""

    def setUp(self):
        self.narrative = KnownNarrative.objects.create(
            title='Test narrative',
            description='Test description',
            category='demoralization',
            example_texts=['Example 1', 'Example 2'],
        )

    def test_list_narratives(self):
        response = self.client.get('/api/narratives/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_retrieve_narrative(self):
        response = self.client.get(f'/api/narratives/{self.narrative.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test narrative')

    def test_narratives_readonly(self):
        """POST to /api/narratives/ should be forbidden (ReadOnly ViewSet)."""
        payload = {
            'title': 'Forbidden',
            'description': 'should not work',
            'category': 'panic',
            'example_texts': [],
        }
        response = self.client.post('/api/narratives/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

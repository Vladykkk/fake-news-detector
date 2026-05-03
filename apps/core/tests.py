"""Tests for core models."""
from django.test import TestCase

from apps.core.models import AnalysisResult, Feedback, KnownNarrative, TelegramAnalysis


class AnalysisResultModelTests(TestCase):
    def test_create_default_verdict(self):
        result = AnalysisResult.objects.create(
            original_text='sample text',
        )
        self.assertEqual(result.verdict, AnalysisResult.Verdict.SAFE)
        self.assertEqual(result.final_score, 0.0)
        self.assertEqual(result.detected_narratives, [])

    def test_str_representation(self):
        result = AnalysisResult.objects.create(
            original_text='some sample text',
            verdict='ipso',
            final_score=0.85,
        )
        self.assertIn('ipso', str(result))
        self.assertIn('0.85', str(result))

    def test_ordering(self):
        r1 = AnalysisResult.objects.create(original_text='first')
        r2 = AnalysisResult.objects.create(original_text='second')
        r3 = AnalysisResult.objects.create(original_text='third')
        results = list(AnalysisResult.objects.all())
        # Most recent first due to Meta.ordering = ['-created_at']
        self.assertEqual(results[0].pk, r3.pk)
        self.assertEqual(results[2].pk, r1.pk)


class KnownNarrativeModelTests(TestCase):
    def test_create_narrative(self):
        narrative = KnownNarrative.objects.create(
            title='Test',
            description='Desc',
            category='demoralization',
            example_texts=['ex1', 'ex2'],
        )
        self.assertEqual(narrative.is_active, True)
        self.assertIsNone(narrative.embedding)

    def test_category_choices(self):
        narrative = KnownNarrative.objects.create(
            title='Test',
            description='Desc',
            category=KnownNarrative.Category.PANIC,
        )
        self.assertEqual(narrative.get_category_display(), 'Паніка та страх')


class FeedbackModelTests(TestCase):
    def setUp(self):
        self.result = AnalysisResult.objects.create(
            original_text='sample', verdict='ipso', final_score=0.8,
        )

    def test_create_feedback(self):
        fb = Feedback.objects.create(
            result=self.result,
            feedback_type=Feedback.FeedbackType.CORRECT,
            chat_id=123,
        )
        self.assertEqual(fb.feedback_type, 'correct')
        self.assertEqual(self.result.feedbacks.count(), 1)

    def test_cascade_delete(self):
        Feedback.objects.create(
            result=self.result,
            feedback_type='wrong',
            chat_id=1,
        )
        self.result.delete()
        self.assertEqual(Feedback.objects.count(), 0)


class TelegramAnalysisModelTests(TestCase):
    def test_one_to_one_with_result(self):
        result = AnalysisResult.objects.create(
            original_text='sample',
        )
        tg = TelegramAnalysis.objects.create(
            result=result,
            chat_id=12345,
            message_id=67890,
            username='testuser',
        )
        self.assertEqual(result.telegram, tg)
        self.assertEqual(tg.username, 'testuser')

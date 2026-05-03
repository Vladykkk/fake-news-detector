"""Tests for the analysis pipeline modules."""
from unittest.mock import patch
from django.test import TestCase, override_settings

from apps.core.models import AnalysisResult, KnownNarrative
from apps.analyzer.rhetoric import analyze_rhetoric
from apps.analyzer.translator import detect_language
from apps.analyzer.pipeline import analyze_text


class RhetoricAnalyzerTests(TestCase):
    """Tests for the rule-based rhetoric analyzer."""

    def test_empty_text(self):
        result = analyze_rhetoric('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['detections'], [])

    def test_clean_text(self):
        text = 'Сьогодні в Києві відбулась зустріч президента з прем’єр-міністром.'
        result = analyze_rhetoric(text, language='uk')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(len(result['detections']), 0)

    def test_ukrainian_patterns_detected(self):
        """Ukrainian rhetoric patterns should trigger on original text."""
        text = (
            'Захід зрадив Україну! Експерти кажуть що опір безнадійний. '
            'Обидві сторони однаково винні. А де ви були коли це починалось?'
        )
        result = analyze_rhetoric(text, language='uk')
        self.assertGreater(result['score'], 0.5)
        detection_types = {d['type'] for d in result['detections']}
        self.assertIn('false_authority', detection_types)
        self.assertIn('demoralization', detection_types)
        self.assertIn('false_equivalence', detection_types)
        self.assertIn('whataboutism', detection_types)

    def test_english_patterns_detected(self):
        text = (
            'What about your own problems? Experts say all is lost. '
            'Both sides are equally guilty. No hope for Ukraine.'
        )
        result = analyze_rhetoric(text, language='en')
        self.assertGreater(result['score'], 0.5)
        detection_types = {d['type'] for d in result['detections']}
        self.assertIn('whataboutism', detection_types)
        self.assertIn('false_authority', detection_types)
        self.assertIn('fear_panic', detection_types)
        self.assertIn('false_equivalence', detection_types)

    def test_score_capped_at_one(self):
        text = (
            'What about your problems? Experts say all is lost. '
            'Both sides equally guilty. Surrender is the only option. '
            'One soldier said useless resistance.'
        )
        result = analyze_rhetoric(text, language='en')
        self.assertLessEqual(result['score'], 1.0)


class TranslatorTests(TestCase):
    """Tests for language detection and translation."""

    def test_detect_ukrainian(self):
        text = 'Сьогодні в Україні дуже тепла погода, люди гуляють у парку.'
        self.assertEqual(detect_language(text), 'uk')

    def test_detect_english(self):
        text = 'Today the weather in Ukraine is very warm, people are walking in the park.'
        self.assertEqual(detect_language(text), 'en')

    def test_empty_text(self):
        # Should not crash on empty input
        result = detect_language('')
        self.assertIn(result, ['unknown', 'en', 'uk'])

    def test_english_not_translated(self):
        """English text should be returned as-is."""
        from apps.analyzer.translator import translate_to_english
        text = 'This is already in English.'
        result = translate_to_english(text, source_lang='en')
        self.assertEqual(result, text)

    @patch('apps.analyzer.translator._translate_deepl', return_value='Translated via DeepL')
    def test_deepl_used_first(self, mock_deepl):
        """DeepL should be called first when available."""
        from apps.analyzer.translator import translate_to_english
        result = translate_to_english('Тестовий текст', source_lang='uk')
        self.assertEqual(result, 'Translated via DeepL')
        mock_deepl.assert_called_once()

    @patch('apps.analyzer.translator._translate_google', return_value='Translated via Google')
    @patch('apps.analyzer.translator._translate_deepl', return_value=None)
    def test_google_fallback(self, mock_deepl, mock_google):
        """Google Translate should be used if DeepL fails."""
        from apps.analyzer.translator import translate_to_english
        result = translate_to_english('Тестовий текст', source_lang='uk')
        self.assertEqual(result, 'Translated via Google')
        mock_deepl.assert_called_once()
        mock_google.assert_called_once()

    @patch('apps.analyzer.translator._translate_google', return_value=None)
    @patch('apps.analyzer.translator._translate_deepl', return_value=None)
    def test_original_if_both_fail(self, mock_deepl, mock_google):
        """Original text should be returned if all translators fail."""
        from apps.analyzer.translator import translate_to_english
        text = 'Оригінальний текст'
        result = translate_to_english(text, source_lang='uk')
        self.assertEqual(result, text)


class PipelineTests(TestCase):
    """Integration tests for the full analysis pipeline."""

    def test_short_text_returns_safe(self):
        """Texts shorter than MIN_TEXT_LENGTH should immediately be marked safe."""
        result = analyze_text('Короткий текст', source='api')
        self.assertEqual(result.verdict, AnalysisResult.Verdict.SAFE)
        self.assertEqual(result.final_score, 0.0)

    @patch('apps.analyzer.pipeline.analyze_rhetoric')
    @patch('apps.analyzer.pipeline.analyze_similarity')
    @patch('apps.analyzer.pipeline.analyze_narratives')
    def test_full_pipeline_saves_result(self, mock_narratives, mock_similarity, mock_rhetoric):
        """Pipeline should run all three modules and save to DB."""
        mock_narratives.return_value = {'score': 0.8, 'detections': [{'label': 'demoralization', 'confidence': 0.8}]}
        mock_similarity.return_value = {'score': 0.6, 'similar_narratives': []}
        mock_rhetoric.return_value = {'score': 1.0, 'detections': [{'type': 'demoralization', 'snippet': 'test', 'confidence': 0.75}]}

        text = (
            'Захід давно зрадив Україну і не збирається допомагати далі. '
            'Експерти кажуть що опір безнадійний, всі ресурси вичерпані.'
        )
        result = analyze_text(text, source='web')

        self.assertEqual(AnalysisResult.objects.count(), 1)
        self.assertEqual(result.source, 'web')
        self.assertEqual(result.detected_language, 'uk')
        self.assertEqual(result.rhetoric_score, 1.0)
        self.assertEqual(result.narrative_score, 0.8)
        self.assertEqual(result.similarity_score, 0.6)
        # Expected: 0.40*0.8 + 0.30*1.0 + 0.30*0.6 = 0.32 + 0.3 + 0.18 = 0.80
        self.assertAlmostEqual(result.final_score, 0.80, places=2)
        self.assertEqual(result.verdict, AnalysisResult.Verdict.IPSO)

    @patch('apps.analyzer.pipeline.analyze_similarity')
    @patch('apps.analyzer.pipeline.analyze_narratives')
    def test_pipeline_safe_verdict(self, mock_narratives, mock_similarity):
        """Clean text should yield safe verdict."""
        mock_narratives.return_value = {'score': 0.0, 'detections': []}
        mock_similarity.return_value = {'score': 0.0, 'similar_narratives': []}

        text = 'Сьогодні в Києві відкрився новий парк для дітей, там багато атракціонів.'
        result = analyze_text(text, source='api')
        self.assertEqual(result.verdict, AnalysisResult.Verdict.SAFE)

    @patch('apps.analyzer.pipeline.analyze_similarity')
    @patch('apps.analyzer.pipeline.analyze_narratives')
    def test_processing_time_recorded(self, mock_narratives, mock_similarity):
        mock_narratives.return_value = {'score': 0.0, 'detections': []}
        mock_similarity.return_value = {'score': 0.0, 'similar_narratives': []}

        text = 'Це звичайний текст для тестування обробки часу. Має достатню довжину.'
        result = analyze_text(text, source='api')
        self.assertGreaterEqual(result.processing_time_ms, 0)

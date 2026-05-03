from django.db import models


class AnalysisResult(models.Model):
    """Stores every analysis request and its result."""

    class Verdict(models.TextChoices):
        SAFE = 'safe', 'Безпечно'
        SUSPICIOUS = 'suspicious', 'Підозрілий'
        IPSO = 'ipso', 'ІПСО'

    # Input
    original_text = models.TextField()
    detected_language = models.CharField(max_length=10, blank=True)
    translated_text = models.TextField(blank=True)
    source = models.CharField(max_length=50, default='telegram')  # telegram, api, web

    # Scores (0.0 – 1.0 for each module)
    narrative_score = models.FloatField(default=0.0)
    rhetoric_score = models.FloatField(default=0.0)
    similarity_score = models.FloatField(default=0.0)
    final_score = models.FloatField(default=0.0)

    # Result
    verdict = models.CharField(max_length=20, choices=Verdict.choices, default=Verdict.SAFE)
    detected_narratives = models.JSONField(default=list)
    detected_rhetoric = models.JSONField(default=list)
    similar_narratives = models.JSONField(default=list)

    # Metadata
    processing_time_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.verdict}] {self.final_score:.2f} — {self.original_text[:60]}"


class TelegramAnalysis(models.Model):
    """Links AnalysisResult to a specific Telegram interaction."""
    result = models.OneToOneField(
        AnalysisResult, on_delete=models.CASCADE, related_name='telegram'
    )
    chat_id = models.BigIntegerField()
    message_id = models.BigIntegerField()
    username = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Telegram @{self.username} chat={self.chat_id}"


class Feedback(models.Model):
    """User feedback on analysis results."""

    class FeedbackType(models.TextChoices):
        CORRECT = 'correct', 'Правильно'
        WRONG = 'wrong', 'Помилка'

    result = models.ForeignKey(
        AnalysisResult, on_delete=models.CASCADE, related_name='feedbacks'
    )
    feedback_type = models.CharField(max_length=10, choices=FeedbackType.choices)
    chat_id = models.BigIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.feedback_type} for result #{self.result_id}"


class KnownNarrative(models.Model):
    """Database of known IPSO narratives for similarity comparison."""

    class Category(models.TextChoices):
        DEMORALIZATION = 'demoralization', 'Деморалізація'
        DISTRUST = 'distrust', 'Підрив довіри'
        FALSE_EQUIVALENCE = 'false_equivalence', 'Хибна рівність'
        PANIC = 'panic', 'Паніка та страх'
        CORRUPTION = 'corruption', 'Корупція'
        MILITARY_LOSSES = 'military_losses', 'Втрати ЗСУ'
        WESTERN_ABANDONMENT = 'western_abandonment', 'Захід зраджує'
        OTHER = 'other', 'Інше'

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=Category.choices)
    example_texts = models.JSONField(default=list)
    embedding = models.JSONField(null=True, blank=True)
    source = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'title']

    def __str__(self):
        return f"[{self.category}] {self.title}"

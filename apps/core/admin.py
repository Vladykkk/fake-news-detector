from django.contrib import admin
from .models import AnalysisResult, TelegramAnalysis, Feedback, KnownNarrative


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ['verdict', 'final_score', 'detected_language', 'source', 'created_at']
    list_filter = ['verdict', 'source', 'detected_language']
    search_fields = ['original_text']
    readonly_fields = ['created_at', 'processing_time_ms']


@admin.register(TelegramAnalysis)
class TelegramAnalysisAdmin(admin.ModelAdmin):
    list_display = ['username', 'chat_id', 'result', 'created_at']
    search_fields = ['username']


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['feedback_type', 'result', 'created_at']
    list_filter = ['feedback_type']


@admin.register(KnownNarrative)
class KnownNarrativeAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'source', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['title', 'description']

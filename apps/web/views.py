"""Web dashboard views — class-based (Django Templates + HTMX)."""
from django.views import View
from django.views.generic import ListView, DetailView, TemplateView
from django.http import HttpResponse
from django.shortcuts import render

from apps.core.models import AnalysisResult


class IndexView(TemplateView):
    """Головна сторінка з формою аналізу та останніми результатами."""
    template_name = 'web/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_results'] = AnalysisResult.objects.all()[:10]
        return context


class AnalyzeView(View):
    """POST-обробник форми аналізу (HTMX)."""
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        text = request.POST.get('text', '').strip()

        if len(text) < 30:
            return HttpResponse(
                '<div class="alert alert-warning">'
                'Текст занадто короткий (мінімум 30 символів).'
                '</div>'
            )

        from apps.analyzer.pipeline import analyze_text
        result = analyze_text(text, source='web')

        return render(request, 'web/partials/result.html', {'result': result})


class ResultDetailView(DetailView):
    """Детальний перегляд результату аналізу."""
    model = AnalysisResult
    template_name = 'web/result_detail.html'
    context_object_name = 'result'


class HistoryView(ListView):
    """Список усіх результатів аналізу."""
    model = AnalysisResult
    template_name = 'web/history.html'
    context_object_name = 'results'
    paginate_by = 50
    ordering = ['-created_at']

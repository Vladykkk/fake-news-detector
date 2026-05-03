from django.urls import path
from .views import IndexView, AnalyzeView, ResultDetailView, HistoryView

urlpatterns = [
    path('', IndexView.as_view(), name='web-index'),
    path('analyze/', AnalyzeView.as_view(), name='web-analyze'),
    path('result/<int:pk>/', ResultDetailView.as_view(), name='web-result-detail'),
    path('history/', HistoryView.as_view(), name='web-history'),
]

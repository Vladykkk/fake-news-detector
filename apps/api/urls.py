from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'analysis', views.AnalysisViewSet, basename='analysis')
router.register(r'feedback', views.FeedbackViewSet, basename='feedback')
router.register(r'narratives', views.KnownNarrativeViewSet, basename='narratives')

urlpatterns = [
    path('', include(router.urls)),
]

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.api.urls')),
    path('bot/', include('apps.bot.urls')),
    path('', include('apps.web.urls')),
]

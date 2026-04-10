"""
Головний маршрутизатор проєкту MarketingAI.
"""
from django.contrib import admin
from django.urls import path, include
from apps.chat.views import chatwoot_webhook
from apps.calendar_sync.views import legacy_google_calendar_schedule

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat/', include('apps.chat.urls')),
    path('api/chatwoot-webhook/', chatwoot_webhook),
    path('api/billing/', include('apps.billing.urls')),
    # Сумісність: старий redirect URI / кешований фронтенд (див. legacy_google_calendar_schedule)
    path('api/google-calendar/schedule/', legacy_google_calendar_schedule),
    path('api/calendar/', include('apps.calendar_sync.urls')),
    path('', include('apps.accounts.urls')),
]

from django.urls import path
from . import views

app_name = 'calendar_sync'

urlpatterns = [
    path('oauth/start/', views.google_oauth_start),
    path('oauth/callback/', views.google_oauth_callback, name='oauth_callback'),
    path('save-schedule/', views.save_schedule),
    path('schedule/', views.get_schedule),
    path('schedule/delete/', views.delete_schedule),
    path('status/', views.calendar_status),
]

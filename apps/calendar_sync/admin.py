from django.contrib import admin
from .models import GoogleCalendarCredential, ScheduleSlot


@admin.register(GoogleCalendarCredential)
class GoogleCalendarCredentialAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_expiry', 'updated_at']
    readonly_fields = ['access_token', 'refresh_token', 'token_expiry', 'created_at', 'updated_at']


@admin.register(ScheduleSlot)
class ScheduleSlotAdmin(admin.ModelAdmin):
    list_display = ['user', 'day_of_week', 'start_time', 'end_time', 'google_event_id']
    list_filter = ['day_of_week', 'user']

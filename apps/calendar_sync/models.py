from django.conf import settings
from django.db import models


class GoogleCalendarCredential(models.Model):
    """Зберігає OAuth2 токени для Google Calendar кожного користувача."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='google_calendar_credential',
    )
    access_token = models.TextField(blank=True, default='')
    refresh_token = models.TextField(blank=True, default='')
    token_expiry = models.DateTimeField(null=True, blank=True)
    token_uri = models.CharField(max_length=255, default='https://oauth2.googleapis.com/token')
    client_id = models.CharField(max_length=255, blank=True, default='')
    client_secret = models.CharField(max_length=255, blank=True, default='')
    scopes = models.TextField(default='https://www.googleapis.com/auth/calendar')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Google Calendar Credential'
        verbose_name_plural = 'Google Calendar Credentials'

    def __str__(self):
        email = getattr(self.user, 'email', '') or str(self.user_id)
        return f'{email} — Google Calendar'


class ScheduleSlot(models.Model):
    """Один 30-хвилинний слот у розкладі користувача."""

    DAY_CHOICES = [
        (0, 'Понеділок'),
        (1, 'Вівторок'),
        (2, 'Середа'),
        (3, 'Четвер'),
        (4, 'Пʼятниця'),
        (5, 'Субота'),
        (6, 'Неділя'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='schedule_slots',
    )
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    google_event_id = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'day_of_week', 'start_time'],
                name='calendar_sync_scheduleslot_user_day_start_uniq',
            ),
        ]

    def __str__(self):
        email = getattr(self.user, 'email', '') or str(self.user_id)
        return f'{email} — {self.get_day_of_week_display()} {self.start_time}'

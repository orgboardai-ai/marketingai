import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GoogleCalendarCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('access_token', models.TextField(blank=True, default='')),
                ('refresh_token', models.TextField(blank=True, default='')),
                ('token_expiry', models.DateTimeField(blank=True, null=True)),
                ('token_uri', models.CharField(default='https://oauth2.googleapis.com/token', max_length=255)),
                ('client_id', models.CharField(blank=True, default='', max_length=255)),
                ('client_secret', models.CharField(blank=True, default='', max_length=255)),
                ('scopes', models.TextField(default='https://www.googleapis.com/auth/calendar')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='google_calendar_credential', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Google Calendar Credential',
                'verbose_name_plural': 'Google Calendar Credentials',
            },
        ),
        migrations.CreateModel(
            name='ScheduleSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day_of_week', models.PositiveSmallIntegerField(choices=[(0, 'Понеділок'), (1, 'Вівторок'), (2, 'Середа'), (3, 'Четвер'), (4, 'Пʼятниця'), (5, 'Субота'), (6, 'Неділя')])),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('google_event_id', models.CharField(blank=True, default='', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedule_slots', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['day_of_week', 'start_time'],
            },
        ),
        migrations.AddConstraint(
            model_name='scheduleslot',
            constraint=models.UniqueConstraint(fields=('user', 'day_of_week', 'start_time'), name='calendar_sync_scheduleslot_user_day_start_uniq'),
        ),
    ]

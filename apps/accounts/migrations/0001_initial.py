from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


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
                ('token_uri', models.CharField(blank=True, default='https://oauth2.googleapis.com/token', max_length=255)),
                ('token_expiry', models.DateTimeField(blank=True, null=True)),
                ('calendar_id', models.CharField(blank=True, default='primary', max_length=255)),
                ('scopes', models.TextField(blank=True, default='')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='google_calendar_credential', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]


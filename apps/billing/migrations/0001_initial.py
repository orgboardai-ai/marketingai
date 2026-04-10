# Generated manually for MarketingAI

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
            name='UserPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan', models.CharField(choices=[('free', 'Free'), ('basic', 'Basic'), ('pro', 'Pro')], default='free', max_length=20)),
                ('steps_used', models.IntegerField(default=0)),
                ('steps_limit', models.IntegerField(default=3)),
                ('wayforpay_order_id', models.CharField(blank=True, max_length=255)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='user_plan', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'План користувача',
                'verbose_name_plural': 'Плани користувачів',
            },
        ),
    ]

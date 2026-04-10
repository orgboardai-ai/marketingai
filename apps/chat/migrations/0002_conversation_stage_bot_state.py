# Стан етапу / питання та прапорець бота для n8n та Chatwoot

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='bot_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='conversation',
            name='question_index',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='conversation',
            name='stage_index',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]

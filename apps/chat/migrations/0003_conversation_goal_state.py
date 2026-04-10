from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_conversation_stage_bot_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='goal_title',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='conversation',
            name='goal_confirmed',
            field=models.BooleanField(default=False),
        ),
    ]


"""
Моделі чату: розмова та повідомлення (user / ai / agent).
"""
from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """Одна розмова користувача з AI/агентом."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations',
    )
    chatwoot_conversation_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Синхронізація з етапами на сайті та n8n (0 = етап 1)
    stage_index = models.PositiveSmallIntegerField(default=0)
    question_index = models.PositiveSmallIntegerField(default=0)
    # Поки False — повідомлення не йдуть у n8n (перехоплення оператором Chatwoot)
    bot_active = models.BooleanField(default=True)
    # Постановка цілі (етап "Інструкція"): зберігаємо, щоб UI був динамічним і відновлювався після офлайну
    goal_title = models.CharField(max_length=255, blank=True, default='')
    goal_confirmed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Розмова'
        verbose_name_plural = 'Розмови'

    def __str__(self):
        u = getattr(self.user, 'email', None) or self.user.get_username()
        return f'Conversation {self.id} — {u}'


class Message(models.Model):
    """Один меседж у розмові."""
    SENDER_CHOICES = [
        ('user', 'User'),
        ('ai', 'AI'),
        ('agent', 'Agent'),
    ]
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Повідомлення'
        verbose_name_plural = 'Повідомлення'

    def __str__(self):
        return f'{self.sender}: {self.text[:50]}'

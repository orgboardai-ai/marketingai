"""
Моделі тарифів та платежів (WayForPay).
"""
from django.conf import settings
from django.db import models


class UserPlan(models.Model):
    """План користувача: free / basic / pro та ліміти кроків."""
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('pro', 'Pro'),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_plan',
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    steps_used = models.IntegerField(default=0)
    steps_limit = models.IntegerField(default=3)  # free: 3, basic: 4, pro: 9
    wayforpay_order_id = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'План користувача'
        verbose_name_plural = 'Плани користувачів'

    def __str__(self):
        return f'{self.user.email} — {self.plan}'

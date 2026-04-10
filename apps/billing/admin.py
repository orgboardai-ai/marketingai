from django.contrib import admin
from .models import UserPlan


@admin.register(UserPlan)
class UserPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'steps_used', 'steps_limit', 'wayforpay_order_id')
    list_filter = ('plan',)
    search_fields = ('user__email', 'wayforpay_order_id')

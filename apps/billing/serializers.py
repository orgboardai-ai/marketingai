"""
Серіалізатори білінгу: створення чекауту WayForPay.
"""
from rest_framework import serializers


class CheckoutSerializer(serializers.Serializer):
    """POST /api/billing/checkout/: план для покупки."""
    plan = serializers.ChoiceField(choices=['basic', 'pro'])

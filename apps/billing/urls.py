"""
URL-и API білінгу: checkout, webhook WayForPay.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout),
    path('webhook/', views.webhook),
]

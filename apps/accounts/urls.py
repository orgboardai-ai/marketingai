"""
URL-и сторінок: головна, ціни, дашборд, чат, логін, реєстрація, білінг.
"""
from django.urls import path
from . import views
from . import google_signin

urlpatterns = [
    path('', views.home, name='home'),
    path('pricing/', views.pricing, name='pricing'),
    path('contacts/', views.contacts, name='contacts'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('chat/', views.chat_page, name='chat'),
    path('billing/', views.billing_page, name='billing'),
    path('accounts/google/start/', google_signin.google_signin_start, name='google_signin_start'),
    path('accounts/google/callback/', google_signin.google_signin_callback, name='google_signin_callback'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]

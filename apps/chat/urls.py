"""
URL-и API чату та webhook Chatwoot.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('message/', views.send_message),
    path('messages/', views.list_messages),
    path('response/', views.incoming_response),
    path('conversations/', views.list_conversations),
    path('conversation/<int:pk>/', views.conversation_detail),
]


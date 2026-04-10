from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'stage_index', 'question_index', 'bot_active',
        'chatwoot_conversation_id', 'created_at',
    )
    list_filter = ('created_at', 'bot_active')
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'text_preview', 'created_at')
    list_filter = ('sender', 'created_at')

    def text_preview(self, obj):
        return (obj.text or '')[:60]
    text_preview.short_description = 'Текст'

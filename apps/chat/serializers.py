"""
Серіалізатори для API чату.
"""
from rest_framework import serializers
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ('id', 'sender', 'text', 'created_at')
        read_only_fields = fields


class ConversationStateSerializer(serializers.ModelSerializer):
    """Стан розмови для фронтенду та синхронізації етапів."""
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            'id', 'stage_index', 'question_index', 'bot_active',
            'goal_title', 'goal_confirmed',
            'created_at', 'message_count',
        )
        read_only_fields = ('id', 'created_at', 'message_count')

    def get_message_count(self, obj):
        return obj.messages.count()


class ConversationPatchSerializer(serializers.Serializer):
    """PATCH: оновлення етапу зі степера на сайті."""
    stage_index = serializers.IntegerField(min_value=0, max_value=50)


class SendMessageSerializer(serializers.Serializer):
    """POST /api/chat/message/: повідомлення, відкриття чату або синхронізація етапу."""
    text = serializers.CharField(required=False, allow_blank=True, max_length=50000)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    event = serializers.ChoiceField(
        choices=['user_message', 'chat_opened'],
        default='user_message',
    )
    stage_index = serializers.IntegerField(required=False, min_value=0, max_value=50)

    def validate(self, attrs):
        ev = attrs.get('event') or 'user_message'
        text = (attrs.get('text') or '').strip()
        if ev == 'user_message' and not text:
            raise serializers.ValidationError({
                'text': 'Текст обов’язковий для звичайного повідомлення.',
            })
        attrs['text'] = text
        return attrs


class IncomingResponseSerializer(serializers.Serializer):
    """POST /api/chat/response/ від n8n."""
    conversation_id = serializers.IntegerField()
    message_id = serializers.IntegerField(required=False, allow_null=True)
    text = serializers.CharField()
    sender = serializers.ChoiceField(choices=['ai', 'agent'], default='ai')
    stage_index = serializers.IntegerField(required=False, min_value=0, max_value=50)
    question_index = serializers.IntegerField(required=False, min_value=0, max_value=500)
    # постановка цілі (керування динамічним UI)
    goal_title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    goal_confirmed = serializers.BooleanField(required=False)

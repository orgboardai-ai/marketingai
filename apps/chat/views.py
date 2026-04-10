"""
API чату: повідомлення, історія, стан етапу, вебхуки n8n та Chatwoot.
"""
import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import Conversation, Message
from .serializers import (
    MessageSerializer,
    SendMessageSerializer,
    IncomingResponseSerializer,
    ConversationStateSerializer,
    ConversationPatchSerializer,
)


def _history_for_n8n(conv, limit=40):
    """Останні повідомлення для контексту LLM у n8n (хронологічно)."""
    rows = list(conv.messages.order_by('-id')[:limit])
    rows.reverse()
    return [{'sender': m.sender, 'text': m.text} for m in rows]


def _send_to_chatwoot(conversation_id_cw, text, incoming=True):
    """Відправити повідомлення в Chatwoot."""
    if not all([settings.CHATWOOT_BASE_URL, settings.CHATWOOT_API_TOKEN, settings.CHATWOOT_ACCOUNT_ID]):
        return
    url = (
        f"{settings.CHATWOOT_BASE_URL}/api/v1/accounts/{settings.CHATWOOT_ACCOUNT_ID}"
        f"/conversations/{conversation_id_cw}/messages"
    )
    headers = {'api_access_token': settings.CHATWOOT_API_TOKEN}
    payload = {
        'content': text,
        'message_type': 'incoming' if incoming else 'outgoing',
        'private': False,
    }
    try:
        requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception:
        pass


def _send_to_n8n(conv, message_id, text, user_id, event):
    """
    Повний контекст для n8n: етап, питання, історія, подія (відкриття чату / повідомлення).
    message_id може бути None для chat_opened.
    """
    if not settings.N8N_WEBHOOK_URL:
        return
    if not conv.bot_active:
        return
    try:
        requests.post(
            settings.N8N_WEBHOOK_URL,
            json={
                'conversation_id': conv.id,
                'message_id': message_id,
                'user_id': user_id,
                'text': text or '',
                'event': event,
                'stage_index': conv.stage_index,
                'question_index': conv.question_index,
                'bot_active': conv.bot_active,
                'history': _history_for_n8n(conv),
            },
            timeout=20,
        )
    except Exception:
        pass


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def conversation_detail(request, pk):
    """
    GET — стан розмови (етап, індекс питання, bot_active) для відновлення після офлайну.
    PATCH — синхронізація stage_index зі степера на сайті.
    """
    conv = get_object_or_404(Conversation, pk=pk, user=request.user)
    if request.method == 'GET':
        return Response(ConversationStateSerializer(conv).data)
    ser = ConversationPatchSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    conv.stage_index = ser.validated_data['stage_index']
    conv.save(update_fields=['stage_index'])
    return Response(ConversationStateSerializer(conv).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """
    Звичайне повідомлення або подія chat_opened (старт чату без тексту користувача).
    """
    ser = SendMessageSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    event = ser.validated_data['event']
    text = ser.validated_data['text']
    conv_id = ser.validated_data.get('conversation_id')
    stage_from_client = ser.validated_data.get('stage_index')

    if conv_id:
        try:
            conv = Conversation.objects.get(id=conv_id, user=request.user)
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)
    else:
        conv = Conversation.objects.create(user=request.user)

    if stage_from_client is not None:
        conv.stage_index = stage_from_client
        conv.save(update_fields=['stage_index'])

    if event == 'chat_opened':
        # Без повідомлення користувача в БД — лише запуск сценарію n8n
        if conv.bot_active and settings.N8N_WEBHOOK_URL:
            _send_to_n8n(conv, None, '', request.user.id, 'chat_opened')
        return Response(
            {
                'conversation_id': conv.id,
                'message_id': None,
                'event': 'chat_opened',
            },
            status=status.HTTP_201_CREATED,
        )

    msg = Message.objects.create(conversation=conv, sender='user', text=text)

    if conv.chatwoot_conversation_id:
        _send_to_chatwoot(conv.chatwoot_conversation_id, text, incoming=True)

    if conv.bot_active:
        _send_to_n8n(conv, msg.id, text, request.user.id, 'user_message')

    return Response(
        {'conversation_id': conv.id, 'message_id': msg.id, 'event': 'user_message'},
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_messages(request):
    """Полінг або повна історія: без after — усі повідомлення (відновлення після офлайну)."""
    conv_id = request.query_params.get('conversation_id')
    after = request.query_params.get('after')
    if not conv_id:
        return Response({'detail': 'conversation_id required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        conv = Conversation.objects.get(id=conv_id, user=request.user)
    except Conversation.DoesNotExist:
        return Response({'detail': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

    qs = conv.messages.all().order_by('id')
    if after:
        try:
            after_id = int(after)
            qs = qs.filter(id__gt=after_id)
        except ValueError:
            pass
    serializer = MessageSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def incoming_response(request):
    """Відповідь від n8n; опційно оновлюємо stage_index / question_index."""
    ser = IncomingResponseSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    conv_id = ser.validated_data['conversation_id']
    text = ser.validated_data['text']
    sender = ser.validated_data.get('sender', 'ai')

    try:
        conv = Conversation.objects.get(id=conv_id)
    except Conversation.DoesNotExist:
        return Response({'detail': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

    Message.objects.create(conversation=conv, sender=sender, text=text)

    update_fields = []
    if ser.validated_data.get('stage_index') is not None:
        conv.stage_index = ser.validated_data['stage_index']
        update_fields.append('stage_index')
    if ser.validated_data.get('question_index') is not None:
        conv.question_index = ser.validated_data['question_index']
        update_fields.append('question_index')
    if ser.validated_data.get('goal_title') is not None:
        conv.goal_title = (ser.validated_data.get('goal_title') or '').strip()
        update_fields.append('goal_title')
    if ser.validated_data.get('goal_confirmed') is not None:
        conv.goal_confirmed = bool(ser.validated_data.get('goal_confirmed'))
        update_fields.append('goal_confirmed')
    if update_fields:
        conv.save(update_fields=update_fields)

    if sender == 'ai' and conv.chatwoot_conversation_id:
        _send_to_chatwoot(conv.chatwoot_conversation_id, text, incoming=False)

    return Response({'status': 'ok'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def chatwoot_webhook(request):
    """
    Повідомлення від оператора Chatwoot → БД; перехоплення: вимикаємо бота.
    """
    try:
        data = request.data
        event = data.get('event') or data.get('event_type') or ''
        payload = data.get('payload') or data
        if 'message_created' in event or 'message_created' in str(payload):
            msg_payload = payload.get('message') or payload
            content = msg_payload.get('content') or msg_payload.get('text', '')
            conv_cw_id = (msg_payload.get('conversation') or {}).get('id') or payload.get('conversation_id')
            if not conv_cw_id or not content:
                return Response({'status': 'ignored'}, status=status.HTTP_200_OK)
            conv = Conversation.objects.filter(chatwoot_conversation_id=conv_cw_id).first()
            if conv:
                if msg_payload.get('message_type') == 'outgoing' or msg_payload.get('private') is False:
                    Message.objects.create(conversation=conv, sender='agent', text=content)
                    if conv.bot_active:
                        conv.bot_active = False
                        conv.save(update_fields=['bot_active'])
    except Exception:
        pass
    return Response({'status': 'ok'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_conversations(request):
    """Список розмов користувача з коротким станом."""
    convs = Conversation.objects.filter(user=request.user).order_by('-created_at')[:50]
    data = []
    for c in convs:
        data.append({
            'id': c.id,
            'created_at': c.created_at,
            'stage_index': c.stage_index,
            'question_index': c.question_index,
            'bot_active': c.bot_active,
            'message_count': c.messages.count(),
        })
    return Response(data)

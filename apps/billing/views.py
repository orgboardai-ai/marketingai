"""
Сторінка білінгу та API: checkout (WayForPay форма), webhook (підтвердження оплати).
Усі секрети з settings (env).
"""
import hashlib
import hmac
import json
import time
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import UserPlan
from .serializers import CheckoutSerializer

# Плани та ціни (євро)
PLAN_AMOUNTS = {'basic': 300, 'pro': 990}
PLAN_STEPS = {'free': 3, 'basic': 4, 'pro': 9}
PLAN_NAMES = {'basic': '4 КРОКИ', 'pro': '9 КРОКІВ'}


def _wayforpay_sign_request(params_list):
    """Підпис для запиту WayForPay: HMAC-MD5 від рядка з ;."""
    raw = ';'.join(str(p) for p in params_list)
    return hmac.new(
        settings.WAYFORPAY_MERCHANT_SECRET.encode('utf-8'),
        raw.encode('utf-8'),
        hashlib.md5,
    ).hexdigest()


def _wayforpay_sign_response(order_reference, status_val, time_val):
    """Підпис відповіді для serviceUrl: orderReference;status;time."""
    raw = f'{order_reference};{status_val};{time_val}'
    return hmac.new(
        settings.WAYFORPAY_MERCHANT_SECRET.encode('utf-8'),
        raw.encode('utf-8'),
        hashlib.md5,
    ).hexdigest()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkout(request):
    """
    Створити платіж WayForPay: повертаємо URL та дані форми,
    клієнт робить redirect на WayForPay або сабмітить форму.
    """
    if not settings.WAYFORPAY_MERCHANT_ACCOUNT or not settings.WAYFORPAY_MERCHANT_SECRET:
        return Response(
            {"detail": "WayForPay not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    ser = CheckoutSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    plan = ser.validated_data['plan']
    if plan not in PLAN_AMOUNTS:
        return Response({"detail": "Invalid plan."}, status=status.HTTP_400_BAD_REQUEST)

    user_plan, _ = UserPlan.objects.get_or_create(
        user=request.user,
        defaults={'plan': 'free', 'steps_limit': 3},
    )
    order_reference = f"ma-{request.user.id}-{plan}-{int(time.time())}"
    order_date = int(time.time())
    amount = PLAN_AMOUNTS[plan]
    currency = getattr(settings, 'WAYFORPAY_CURRENCY', 'EUR')
    product_name = f"MarketingAI {plan.upper()}"
    merchant_domain = request.get_host() or 'localhost'
    return_url = request.build_absolute_uri('/billing/')
    service_url = request.build_absolute_uri('/api/billing/webhook/')

    # Підпис: merchantAccount;merchantDomainName;orderReference;orderDate;amount;currency;productName;productCount;productPrice
    sign_params = [
        settings.WAYFORPAY_MERCHANT_ACCOUNT,
        merchant_domain,
        order_reference,
        order_date,
        amount,
        currency,
        product_name,
        1,
        amount,
    ]
    merchant_signature = _wayforpay_sign_request(sign_params)

    form_data = {
        'merchantAccount': settings.WAYFORPAY_MERCHANT_ACCOUNT,
        'merchantDomainName': merchant_domain,
        'merchantAuthType': 'simpleSignature',
        'orderReference': order_reference,
        'orderDate': order_date,
        'amount': amount,
        'currency': currency,
        'productName[]': product_name,
        'productCount[]': 1,
        'productPrice[]': amount,
        'returnUrl': return_url,
        'serviceUrl': service_url,
        'merchantSignature': merchant_signature,
        'clientEmail': getattr(request.user, 'email', '') or '',
    }
    # Зберігаємо order_reference у UserPlan для перевірки в webhook
    user_plan.wayforpay_order_id = order_reference
    user_plan.save(update_fields=['wayforpay_order_id'])

    return Response({
        'redirect_url': 'https://secure.wayforpay.com/pay',
        'form_data': form_data,
        'order_reference': order_reference,
    }, status=status.HTTP_200_OK)


@csrf_exempt
@require_POST
def webhook(request):
    """
    WayForPay надсилає сюди результат оплати (POST JSON).
    Перевіряємо merchantSignature, оновлюємо UserPlan при transactionStatus=Approved.
    Відповідь: {"orderReference":"...","status":"accept","time":...,"signature":"..."}
    """
    try:
        body = request.body.decode('utf-8')
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)

    order_reference = data.get('orderReference')
    merchant_sig = data.get('merchantSignature')
    transaction_status = data.get('transactionStatus')
    amount = data.get('amount')
    currency = data.get('currency', '')
    auth_code = data.get('authCode', '')
    card_pan = data.get('cardPan', '')
    reason_code = data.get('reasonCode', '')

    if not order_reference or not merchant_sig:
        return HttpResponse(status=400)

    # Перевірка підпису: merchantAccount;orderReference;amount;currency;authCode;cardPan;transactionStatus;reasonCode
    sign_string = ';'.join([
        str(data.get('merchantAccount', '')),
        order_reference,
        str(amount),
        currency,
        str(auth_code),
        str(card_pan),
        str(transaction_status),
        str(reason_code),
    ])
    expected_sig = hmac.new(
        settings.WAYFORPAY_MERCHANT_SECRET.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.md5,
    ).hexdigest()
    if expected_sig != merchant_sig:
        return HttpResponse(status=403)

    if transaction_status == 'Approved' and order_reference.startswith('ma-'):
        # Формат: ma-{user_id}-{plan}-{ts}
        parts = order_reference.split('-')
        if len(parts) >= 3:
            try:
                user_id = int(parts[1])
                plan = parts[2]
                if plan in ('basic', 'pro'):
                    UserPlan.objects.filter(user_id=user_id).update(
                        plan=plan,
                        steps_limit=PLAN_STEPS[plan],
                        wayforpay_order_id=order_reference,
                    )
            except (ValueError, IndexError):
                pass

    t = int(time.time())
    resp = {
        'orderReference': order_reference,
        'status': 'accept',
        'time': t,
        'signature': _wayforpay_sign_response(order_reference, 'accept', t),
    }
    return JsonResponse(resp)

"""
Сторінки: головна, ціни, дашборд, чат, логін, реєстрація, білінг.
"""
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods


def home(request):
    """Головна сторінка — лендінг."""
    return render(request, 'home.html')


def pricing(request):
    """Сторінка цін (для авторизованих передаємо поточний план для підсвітки картки)."""
    user_plan = None
    if request.user.is_authenticated:
        from apps.billing.models import UserPlan
        user_plan = getattr(request.user, 'user_plan', None) or UserPlan.objects.filter(
            user=request.user
        ).first()
    return render(request, 'pricing.html', {'user_plan': user_plan})


@require_http_methods(['GET', 'POST'])
def contacts(request):
    """Сторінка контактів і форма зворотного зв'язку (дизайн-система DS)."""
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        body = (request.POST.get('message') or '').strip()
        if not name or not email or not body:
            messages.error(request, 'Заповніть усі обовʼязкові поля.')
        elif '@' not in email:
            messages.error(request, 'Вкажіть коректну електронну адресу.')
        else:
            # Поки без збереження в БД — лише підтвердження для користувача
            messages.success(
                request,
                'Дякуємо! Ми отримали ваше повідомлення і звʼяжемося найближчим часом.',
            )
            return redirect('contacts')
    return render(request, 'contacts.html')


@login_required
def dashboard(request):
    """Дашборд після входу."""
    return render(request, 'dashboard.html')


@login_required
def chat_page(request):
    """Сторінка чату з AI."""
    return render(
        request,
        'chat.html',
        {'chat_allow_new_conversation': settings.CHAT_ALLOW_NEW_CONVERSATION},
    )


@login_required
def billing_page(request):
    """Сторінка білінгу / планів."""
    from apps.billing.models import UserPlan
    user_plan = getattr(request.user, 'user_plan', None) or UserPlan.objects.filter(user=request.user).first()
    return render(request, 'billing.html', {'user_plan': user_plan})


@require_http_methods(['GET', 'POST'])
def login_view(request):
    """Вхід у систему."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def register_view(request):
    """Реєстрація нового користувача."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            from apps.billing.models import UserPlan
            UserPlan.objects.get_or_create(user=user, defaults={'plan': 'free', 'steps_limit': 3})
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    """Вихід."""
    logout(request)
    return redirect('home')

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

@login_required
def dashboard_home(request):
    return render(request, 'dashboard/home.html')

@login_required
def dashboard_preferences(request):
    return render(request, 'dashboard/preferences.html')

@login_required
def dashboard_notification_history(request):
    return render(request, 'dashboard/notification_history.html')

@login_required
def dashboard_subscription(request):
    return render(request, 'dashboard/subscription.html')

@login_required
def pause_notifications(request):
    return JsonResponse({'status': 'paused'})

@login_required
def resume_notifications(request):
    return JsonResponse({'status': 'resumed'})

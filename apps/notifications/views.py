from django.shortcuts import render

def notification_list(request):
    return render(request, 'notifications/list.html')

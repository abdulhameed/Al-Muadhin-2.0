from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response

class NotificationsViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response([])

    def retrieve(self, request, pk=None):
        return Response({})

def notification_list(request):
    return render(request, 'notifications/list.html')

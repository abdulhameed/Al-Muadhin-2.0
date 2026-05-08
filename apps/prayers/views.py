from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response

class PrayerTimesViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response([])

    def retrieve(self, request, pk=None):
        return Response({})

def prayer_list(request):
    return render(request, 'prayers/list.html')

from django.shortcuts import render

def prayer_list(request):
    return render(request, 'prayers/list.html')

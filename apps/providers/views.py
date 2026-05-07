from django.shortcuts import render

def provider_list(request):
    return render(request, 'providers/list.html')

from django.http import HttpResponse
from django.shortcuts import render

def index(request):
    return HttpResponse('Imports index.')

def detail(request, import_id):
    return HttpResponse(f'Import detail #{import_id}.')

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from urllib.parse import urlparse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from esoft_utility import aws_config_utility,  utility


def home_page_view(request):
    """
    This is a home page view for the Insights App
    :return: html landing page
    """
    return render(request, "home.html")

def about_page(request):
    """
    This is an about page view for the Insights App
    :return: About page
    """
    return render(request, "aboutPage.html")

def services_page(request):
    """
    This is a services us page view for the Insights App
    :return: Services page
    """
    return render(request, "Services.html")

def contact_page(request):
    """
    This is a contact us page view for the Insights App
    :return: Contact page
    """
    return render(request, "contact.html")

class DataListView():
    def get(self, request, *args, **kwargs):
        data = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]
        return JsonResponse(data, safe=False)

from django.shortcuts import render


def upload(request):
    return render(request, 'upload.html')

def machine_learning(request):
    return render(request, 'upload_ml.html')

def advanced_analytics(request):
    return render(request, 'traditional_ml_hp.html')

def gen_ai_home(request):
    return render(request, 'gen_ai_home.html')

def business_insights(request):
    return render(request, 'business_insights.html')

def artificial_insights(request):
    return render(request, 'insights.html')




"""
URL configuration for esoftAnalytics project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from . import views
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.urls import path, include
from esoftAnalytics import views


from django.urls import path
from . import views

urlpatterns = [
    path('machine_learning/', views.machine_learning, name='machine_learning'),
    path('advanced_analytics/', views.advanced_analytics, name='advanced_analytics'),
    path('gen_ai_home/', views.gen_ai_home, name='gen_ai_home'),
    path('business_insights/', views.business_insights, name='business_insights'),
    path('artificial_insights/', views.artificial_insights, name='artificial_insights'),
    path('about_page/', views.about_page, name='about_page'),
    path('services_page/', views.services_page, name='services_page'),
    path('contact_page/', views.contact_page, name='contact_page'),
    path("", views.home_page_view, name='home'),  
    path("upload/", views.upload, name="upload"),
    path("", include('insights.urls')),
    path("", include('analytics.urls')),
    path("", include('dataEngineering.urls')), 
    path("", include('genAI.urls')),
    path("", include('comparative_analysis.urls')),
]

urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)

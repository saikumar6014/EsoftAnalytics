from django.urls import path
from . import views

# URL Configuration
urlpatterns = [
    path('api/upload_data_to_s3/', views.upload_data_to_s3, name='upload_data_to_s3'),

]

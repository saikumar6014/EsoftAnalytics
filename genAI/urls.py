from django.urls import path
from . import views, open_ai, open_source



urlpatterns = [
    path("gen_ai_home/", views.gen_ai_home_page, name='gen_ai_home'),
    path("gen_ai/", views.gen_ai, name='gen_ai_functionality'),
    path("gen_ai_open_source/", views.gen_ai_open_source),
    path('validate_api_key/', open_ai.validate_api_key, name='validate_api_key'),
    path('upload_documents/', open_ai.upload_documents, name='upload_documents'),
    path('chat/', open_ai.chat_view, name='chat'),

]
from django.shortcuts import render

def analytics_home_page(request):
    """
        This is a home page view for the Analytics App
        :return: html landing page
        """
    return render(request, "advanced_analytics_home.html")

def traditional_ml_home_page(request):
    """
        This is a home page view for the Traditional Model
        :return: html landing page
        """
    return render(request, "traditional_ml_hp.html")

def gen_ai_ml_home_page(request):
    """
        This is a home page view for the Gen AI model
        :return: html landing page
        """
    return render(request, "gen_ai.html")

def tml_wms_usecase_data(request):
    """
    This page is for wms use case data: return: wms webpage
    """
    return render(request, "tml_wms_usecase_data.html")

def ai_chatbot(request):
    """
    This page is AI chatbot integrated into Gen AI: return: Chatbot page
    """
    return render(request,"ai_chatbot.html")
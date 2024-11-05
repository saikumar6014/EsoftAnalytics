from django.shortcuts import render

def gen_ai_home_page(request):
    return render(request, "gen_ai_home.html")

def gen_ai(request):
    return render(request, "gen_ai.html")


def gen_ai_open_source(request):
    return render(request, "gen_ai_open_source.html")

def gen_ai_open_ai(request):
    return render(request, "open_ai.html")

def open_ai_chat(request):
    return render(request, "open_ai_chat.html")

def open_source_chat(request):
    return render(request, "open_source_chat.html")

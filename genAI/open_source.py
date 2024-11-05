from django.shortcuts import render
import requests, os
 
 
def open_source_api_view(question, model):
 
    url = "http://18.206.94.91:8080/open_source_api"
    payload = {  "model": model,  "prompt": question}
   
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json=payload, headers=headers)
    return response
 
def question_view_open_source(request):
    if request.method == 'POST':
        user_input = request.POST.get('user_input')
        model_name = request.POST.get('model_name')
        response = open_source_api_view(user_input, model_name)
        
        if not user_input or not model_name:
            return render(request, 'gen_ai_open_source.html', {
                'error': 'All fields are required.',
                'user_input': user_input,
                'model_name': model_name
            })
 
        try:
            answer = open_source_api_view(user_input, model_name)
        except Exception as e:
            answer = f"Error: {e}"
 
        return render(request, 'gen_ai_open_source.html', {
            'question': user_input,
            'answer': answer
        })
 
    return render(request, 'open_source_chat.html')
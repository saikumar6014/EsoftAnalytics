import os
from venv import logger
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import ChatMessage
from langchain.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from django.contrib import messages
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import openai
import logging
# from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
import sys

logger = logging.getLogger(__name__)

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)


@csrf_exempt
def validate_api_key(request):
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'OK'})
        response['Access-Control-Allow-Origin'] = '*'  # Allow all origins
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            api_key = data.get('apiKey', '')
            model_name = data.get('modelName', '')

            if not api_key or not model_name:
                return JsonResponse({'valid': False, 'error': 'API key and model name are required'}, status=400)

            headers = {
                'Authorization': f'Bearer {api_key}'
            }

            try:
                response = requests.get('https://api.openai.com/v1/models', headers=headers)
                response.raise_for_status()

            except requests.exceptions.RequestException as e:
                logger.error(f"Error making request to OpenAI API: {str(e)}")
                return JsonResponse({'valid': False, 'error': 'OpenAI server is down, please try again later.'},
                                    status=503)

            models = response.json().get('data', [])
            model_exists = any(model['id'] == model_name for model in models)

            if model_exists:
                request.session['api_key'] = api_key
                request.session['model_name'] = model_name
                return JsonResponse({'valid': True})
            else:
                return JsonResponse({'valid': False, 'error': 'Invalid model name'})

        except json.JSONDecodeError:
            logger.error("Invalid JSON received in request body")
            return JsonResponse({'valid': False, 'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return JsonResponse({'valid': False, 'error': 'Server error occurred'}, status=500)

    return JsonResponse({'valid': False, 'error': 'Invalid request method'}, status=405)


def pdf_text(files):
    text = ""
    for pdf in files:
        pdf_reader = ''
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    # print(chunks)
    return chunks


def get_vectorstore(chunks, apikey):
    try:
        embeddings = OpenAIEmbeddings(api_key=apikey)
        vectorstore = FAISS.from_texts(texts=chunks, embedding=embeddings)
    except Exception as e:
        print(str(e))
    return vectorstore


vector_db = {}


@csrf_exempt
def upload_documents(request):
    if request.method == 'POST':
        api_key = request.POST.get('apiKey')
        files = request.FILES.getlist('documents')

        if not files:
            return JsonResponse({'error': 'No files provided'}, status=400)

        file_names_list = [file.name for file in files]

        vector_key = ', '.join(file_names_list)

        vector_store = vector_db.get(vector_key)

        if not vector_store:
            text = pdf_text(files)
            chunks = text_chunks(text)
            vector_embedding = get_vectorstore(chunks, api_key)
            print(vector_embedding)
            vector_db[vector_key] = vector_embedding

        return JsonResponse({'message': 'Vector store created successfully', 'vectorStore_key': vector_key})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


messages_list = []


@csrf_exempt
def chat_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question', '')
            api_key = data.get('api_key', '')
            model_name = data.get('model_name', '')
            vector_key = data.get('vector_key', '')

            if not api_key or not model_name or not question:
                return JsonResponse({'error': 'API key, model name, and question are required'}, status=400)
            openai.api_key = api_key

            if not vector_key:
                messages_list.append({"role": "user", "content": question})
                response = openai.chat.completions.create(
                    model=model_name,
                    messages=messages_list
                    # messages=[
                    #     {"role": "system", "content": "You are a helpful assistant."},
                    #     {"role": "user", "content": question}

                    # ]
                )
            else:
                relevant_docs = vector_db[vector_key].similarity_search(question, k=3)  # Get top 3 relevant chunks
                relevant_text = " ".join([doc.page_content for doc in relevant_docs])
                messages_list.append(
                    {"role": "system", "content": "Consider the following document content: " + relevant_text})
                messages_list.append({"role": "user", "content": question})
                response = openai.chat.completions.create(
                    model=model_name,
                    messages=messages_list
                )

            message_content = response.choices[0].message.content.strip()
            messages_list.append({"role": "assistant", "content": message_content})
            print(messages_list)

            return JsonResponse({'answer': message_content})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


def open_ai_api_view(question, api_key, model):
    os.environ["OPENAI_API_KEY"] = api_key

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Please provide response to the user query in short response. Response should not be more than 50 characters. Also Summarize the response"),
        ("user", f"Question: {question}")
    ])

    llm = ChatOpenAI(model=model)
    output_parser = StrOutputParser()

    try:
        chain = prompt | llm | output_parser
        response = chain.invoke({'question': question})

        if isinstance(response, dict) and 'output' in response:
            return response['output']
        else:
            return f"{response}"

    except Exception as e:
        return f"Error invoking OpenAI API: {str(e)}"


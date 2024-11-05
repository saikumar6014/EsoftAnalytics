import json
from django.shortcuts import render
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from sqlalchemy import create_engine
from analytics.model_utilites import get_s3_models_from_bucket, models_upload_s3
from analytics.utilities import handle_file_request_s3, handle_file_request, get_dataframe
from analytics.utility_venv import check_installation_work
from esoft_utility import aws_config_utility
from esoft_utility import utility
from esoft_utility.utility import read_file_from_s3
from analytics.ai_models import PredictedModel
import traceback
from rest_framework.decorators import api_view
 
def batch_list_files(request):
    print(request, 'rr')
    return handle_file_request_s3(request, 'tml_batchdata.html')
 
 
def real_list_files(request):
    return handle_file_request_s3(request, 'tml_realtimedata.html',
                                  num_rows=10)  
 
 
def upload_ml(request):
    return render(request, 'upload_ml.html')
 
''' PredictModel view handles the request from batch or real time data selection,
    Sent to model for analysis and returns results back to user interface '''
@api_view(['POST'])
@csrf_exempt
def predictModel(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            selected_model = data.get('model')
            filename = data.get('filename')
            rows = data.get("rows", [])
            columns = data.get("columns", [])
           
            print(rows)
            if len(rows)==0 or len(columns) == 0:
                filename = data.get('filename', '')
                df = read_file_from_s3(filename)
            else:
                df = pd.DataFrame(rows, columns=columns)
            print(df)
 
            json_format = PredictedModel(df, selected_model)
            # predictedData_to_DB(df, selected_model)
            return JsonResponse({
            'data': json_format['Prediction'],
            'msg': 'Prediction Completed Successfully!',
            'score': json_format['Metric'],
            'key':json_format['key'],
            'MetricType':json_format['Metric Type'],
            'column' : json_format['column'],
                })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
 
 
@csrf_exempt
def getModelRespons(request):
    if request.method == 'POST':
        modelname = request.POST.get('modelName')
        category = request.POST.get('selectCategories')
        print(category)
        uploaded_files = request.FILES.getlist('files')
        file_paths = json.loads(request.POST.get('file_paths'))
        result = models_upload_s3(uploaded_files, modelname, category)
        return JsonResponse({'message':result})
    else:
        return JsonResponse({'error': 'No Models to be uploaded'}, status=400)
   
 
def listfiles(request):
    try:
        bucket_name = aws_config_utility.get_td_ai_data_storage_bucket_name()
        files = utility.get_s3_files_list(bucket_name)
        listmodel = get_s3_models_from_bucket()
        return JsonResponse({'files': files,'listmodels': listmodel})
       
    except Exception as e:
        return JsonResponse({'error': str(e), 'msg': 'Failed during listing files!'})
 
 
 
 
@csrf_exempt
def data_from_file(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            filename = body.get('filename')
            model_type = body.get('modeltype')
            print(f"Filename: {filename}, Model Type: {model_type}")
           
            df = utility.get_dataframe_data(filename)
            if model_type == 'RealTime':
                print('Processing RealTime data')
                df = df.head(10)  
           
            columns = df.columns.tolist()
            data = df.values.tolist()
            content = {
                'columns': columns,
                'data': data,
                'selected_file': filename
            }
            return JsonResponse(content)
        except Exception as e:
            return JsonResponse({'error': str(e), 'msg': 'Failed during Data Fetch'})
    return JsonResponse({'error': 'Invalid request method'}, status=405)
 
 
 
 
 
@csrf_exempt
def models_upload_s3_view(request):
    if request.method == 'POST':
        try:
            uploaded_files = request.FILES.getlist('files')
            modelname = request.POST.get('modelname')
            category = request.POST.get('category')

            if not uploaded_files or not modelname or not category:
                return JsonResponse({'error': 'Missing required fields', 'errorstatus': True}, status=400)

            response = models_upload_s3(uploaded_files, modelname, category)

            if isinstance(response, str):
                return JsonResponse({'error': response, 'errorstatus': True}, status=500)

            return JsonResponse(
                {'message': 'Model Uploaded Successfully! Sent for processing!', 'result': response.json(),
                 'errorstatus': False}, status=200)

        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({'error': str(e), 'errorstatus': True}, status=500)

    return JsonResponse({'error': 'Invalid request method', 'errorstatus': True}, status=405)
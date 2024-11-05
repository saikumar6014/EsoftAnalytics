import gzip, json
import io, os, pandas as pd
from django.shortcuts import render
from django.http import JsonResponse
from esoft_utility import aws_config_utility, utility
from dataEngineering.utility import read_dataset
from dataEngineering.database_views import connect_db
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def handle_uploaded_file(request, file, ai_model_type):
    try:
        s3 = aws_config_utility.get_s3_client()
        if ai_model_type == 'comparativeAnalysis':
            bucket_name = aws_config_utility.get_comparative_analysis_data_bucket_name()
        elif ai_model_type == "traditional":
            bucket_name = aws_config_utility.get_td_ai_data_storage_bucket_name()
        else:
            bucket_name = aws_config_utility.get_gen_ai_data_storage_bucket_name()
        filename = request.POST.get('filename')
        s3_file = filename + '.csv'
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
 
        if file_size <= 5:
            return JsonResponse({
                'error': 'The file you are trying to upload is empty. Please select a file with content and try again.',
                'status': 'error'
            }, status=400)
 
        files = utility.get_s3_files_list(bucket_name)
        if files is not None and s3_file in files:
            return JsonResponse({
                'message': f' {s3_file} already exists!',
                'status': 'error',
                'exists': True
            })
 
        response = read_and_process_file(file, s3_file, s3, bucket_name)
        if 'error' in response:
            return JsonResponse({'error': response['error'], 'status': 'error'}, status=500)
       
        return JsonResponse({
            'message': f"File {s3_file} uploaded successfully!",
            'status': 'success',
            'exists': False
        })
 
    except Exception as e:
        return JsonResponse({'error': str(e), 'status': 'error'}, status=500)
 
def read_and_process_file(file, s3_file, s3, bucket_name):
    try:
        compress_format = file.name.split(".")[-1]
        if compress_format == "gz":
            with gzip.GzipFile(fileobj=file) as dc_file:
                file_bytes = dc_file.read()
                file_obj = io.BytesIO(file_bytes)
                extension = file.name.split(".")[-2]
                response = read_dataset(file_obj, extension)
        else:
            extension = file.name.split(".")[-1]
            response = read_dataset(file, extension)
 
        if 'Error' in response:
            return {'error': response['Error']}
        elif isinstance(response, pd.DataFrame):
            return upload_dataframe_to_s3(response, s3_file, s3, bucket_name)
        else:
            return {'error': 'Invalid response from upload'}
 
    except Exception as e:
        return {'error': str(e)}
 
def upload_dataframe_to_s3(dataframe, s3_file, s3, bucket_name):
    try:
        csv_buffer = io.StringIO()
        dataframe.insert(0, 'esoft_ID', range(1, len(dataframe) + 1))
        dataframe.to_csv(csv_buffer, index=False)
        s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key=s3_file)
        return {'message': f'File {s3_file} uploaded successfully!!'}
 
    except Exception as e:
        return {'error': str(e)}
 
'''@csrf_exempt
def upload_data_to_s3(request):
    if request.method == 'POST':
        data = json.loads(request.body)
 
        selected_source = data.get('typeofdata')
        ai_model_type = data.get('aiModel')
       
        if selected_source == 'file':
            if 'file' not in request.FILES:
                return JsonResponse({'error': 'No file uploaded', 'status': 'error'}, status=400)
            uploaded_file = request.FILES['file']
            return handle_uploaded_file(request, uploaded_file, ai_model_type)
        elif selected_source == 'database':
            database_type = data.get('databasetype')
            filename = data.get('dbfilename')
            return database_data(request, database_type, filename, ai_model_type)
        elif 'cloud' in data:
            # Handle cloud upload
            pass
   
        return JsonResponse({'error': 'Invalid request', 'status': 'error'}, status=400)'''
 
@csrf_exempt
def upload_data_to_s3(request):
    if request.method == 'POST':
        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            ai_model_type = request.POST.get('aiModel')
            return handle_uploaded_file(request, uploaded_file, ai_model_type)
        else:
            try:
                data = json.loads(request.body.decode('utf-8'))
                selected_source = data.get('typeofdata')
                ai_model_type = data.get('aiModel')
 
                if selected_source == 'database':
                    database_type = data.get('databasetype')
                    filename = data.get('dbfilename')
                    return database_data(request, database_type, filename, ai_model_type)
                elif 'cloud' in data:
                    pass
                else:
                    return JsonResponse({'error': 'Invalid request source', 'status': 'error'}, status=400)
 
            except json.JSONDecodeError as e:
                return JsonResponse({'error': f'JSON decode error: {str(e)}', 'status': 'error'}, status=400)
            except Exception as e:
                return JsonResponse({'error': f'An error occurred: {str(e)}', 'status': 'error'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method', 'status': 'error'}, status=405)
 
@csrf_exempt
def database_data(request, db_type, filename, ai_model_type):
    try:
        s3 = aws_config_utility.get_s3_client()
        df = connect_db(request, db_type)
        if ai_model_type == "traditional":
            bucket_name = aws_config_utility.get_td_ai_data_storage_bucket_name()
        else:
            bucket_name = aws_config_utility.get_gen_ai_data_storage_bucket_name()
        s3_file = filename + '.csv'
        files = utility.get_s3_files_list(bucket_name)
        if files is not None and s3_file in files:
            return JsonResponse({
                'message': f'Filename {s3_file} already exists!',
                'status': 'error',
                'exists': True
            })
        else:
            response = upload_dataframe_to_s3(df, s3_file, s3, bucket_name)
            if 'error' in response:
                return JsonResponse({'error': response['error'], 'status': 'error'}, status=500)
            return JsonResponse({
                'message': f"File {s3_file} uploaded successfully!",
                'status': 'success',
                'exists': False
            })
 
    except Exception as e:
        exc = str(e)
        error_msg = ''
        if "Cannot open database" in exc or ("database" in exc and "does not exist" in exc) or "Unknown database" in exc:
            error_msg = "Invalid Database name"
        elif "Login failed for user" in exc or "authentication failed for user" in exc or "Access denied for user" in exc:
            error_msg = "Invalid login Credentials"
        elif "A network-related or instance-specific error" in exc or "No such host is known" in exc or "Connection refused" in exc or "Can't connect to MySQL server on" in exc:
            error_msg = "Invalid Server/Host name"
        elif "Invalid object name" in exc or ("Table" in exc and "doesn't exist" in exc) or "does not exist" in exc:
            error_msg = "Invalid Table name"
        else:
            error_msg = "Check connection string"
        return JsonResponse({'error': error_msg, 'status': 'error'}, status=500)
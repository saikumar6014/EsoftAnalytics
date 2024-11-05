import os
import json
import pandas as pd
from django.http import HttpResponseServerError, JsonResponse
from django.shortcuts import render
from esoft_utility import aws_config_utility,  utility
from analytics.model_utilites import get_s3_models_from_bucket
import numpy as np
import requests

''' This function  is used to get the folder_path of all 
    uploaded files from the local directory'''


def get_config():
    config_file_path = os.path.join('config.json')

    try:
        with open(config_file_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        raise ValueError(f"Error reading config file: {str(e)}")


def get_dataframe(filename):
    try:
        config = get_config()
        folder_path = config.get('folder_path')
        file_path = os.path.join(folder_path, filename)
        df = pd.read_csv(file_path, index_col=None)
        return df
    except Exception as e:
        return HttpResponseServerError("File not found or error while opening the file" + str(e))


''' This function  returns a response containing list of filenames and other 
    necessary data to the client side '''


def handle_file_request(request, template_name, default_file=None, num_rows=None):
    try:
        config = get_config()
        folder_path = config.get('folder_path')
        files = os.listdir(folder_path)

        if request.method == 'POST':
            filename = request.POST.get('filename', default_file)

            if template_name == 'tml_realtimedata.html':
                df = get_dataframe(filename)
                df = df.head(num_rows)
                columns = df.columns.tolist()
                data = df.values.tolist()
                show_table = True
                
                print(request, 'rr')
                content = {'columns': columns, 'data': data, 'files': files, 'show_table': show_table,
                           'selected_file': filename}
                return render(request, template_name, content)

            elif template_name == 'tml_batchdata.html':
                show_table = True
                content = {'files': files, 'show_table': show_table,
                           'selected_file': filename}
                return render(request, template_name, content)
            else:
                return HttpResponseServerError("Invalid Template Name.")
        else:
            show_table = False
            return render(request, template_name, {'files': files, 'show_table': show_table})
    except Exception as e:
        return JsonResponse({'error': str(e)})


def handle_file_request_s3(request, template_name, default_file=None, num_rows=None):
    try:
        bucket_name = aws_config_utility.get_td_ai_data_storage_bucket_name()
        files = utility.get_s3_files_list(bucket_name)
        listmodel = get_s3_models_from_bucket()
        if request.method == 'POST':
            filename = request.POST.get('filename')
            if template_name == 'tml_realtimedata.html':
                df = utility.get_dataframe_data(filename)
                df = df.head(num_rows)
                columns = df.columns.tolist()
                data = df.values.tolist()
                show_table = True
                print(data)
                content = {'columns': columns, 'data': data, 'files': files, 'show_table': show_table,
                           'selected_file': filename,'listmodels':listmodel}
                return render(request, template_name, content)
 
            elif template_name == 'tml_batchdata.html':
                show_table = True
                content = {'files': files, 'show_table': show_table,
                           'selected_file': filename,'listmodels':listmodel}
                return render(request, template_name, content)
            else:
                return HttpResponseServerError("Invalid Template Name.")
        else:
            show_table = False
            return render(request, template_name, {'files': files, 'show_table': show_table})                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
    except Exception as e:
        return JsonResponse({'error': str(e)})
    
def analyzeData(df,options):
    try:
        
        ''' By using numpy random and choice functions we can explicitly 
                 insert result column with True or False to dataset ''' 
        df['predicted_result'] = np.random.choice([True, False], size=len(df))

        if options == 'Model 1':
            displaydata = df.iloc[:, [0, 3, -1]]
        elif options == 'Model 2':
            displaydata = df.iloc[:, [0, 2, -1]]
        elif options == 'Model 3':
            displaydata = df.iloc[:, [0, 4, -1]]
        elif options == 'Model 4':
            displaydata = df.iloc[:, [0, 3, -1]]
        json_format = displaydata.to_json(orient='records')

        return json_format
    except Exception as e:
        return JsonResponse({'error': str(e), 'msg': 'Failed during analyzing data!'})
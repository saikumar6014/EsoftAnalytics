import json
import os
import pandas as pd
from django.http import HttpResponseBadRequest, HttpResponseServerError, JsonResponse
from django.shortcuts import render
from dataEngineering.models import UploadModel


def traditional_ml_home_page(request):
    return render(request, 'traditional_ml_hp.html')


def dataset(path):
    extension = path[path.rfind('.'):]
    try:
        if extension == ".csv":
            df = pd.read_csv(path)
        elif extension in [".xls", ".xlsx", ".xlsm", ".xlsb"]:
            df = pd.read_excel(path)
        elif extension == ".html":
            df = pd.read_html(path)
        elif extension == ".json":
            df = pd.read_json(path)
        else:
            return JsonResponse({'error': f'Unsupported file type: {extension}'}, status=400)
        return df

    except Exception as e:
        return JsonResponse({'Error': f'Unable to fetch File path: {str(e)}'})


def list_datasources(request):
    try:
        datasources = UploadModel.objects.values_list("dataSource", flat=True).distinct()
        return render(request, 'advanced_analytics_home.html', {'datasources': datasources})
    except Exception as e:
        return HttpResponseServerError(f'Unable to fetch datasources. Error: {str(e)}')


def list_files(request):
    try:
        datasourcename = request.GET.get('fileNameData')
        list_of_files = UploadModel.objects.filter(dataSource=datasourcename).values_list('filename', flat=True)
        files = []
        for i in list_of_files:
            files.append(i)
        return JsonResponse({'files': files})
    except Exception as e:
        return HttpResponseServerError(f'Unable to fetch list of files. Error:{str(e)}')


def getColumnList(request):
    try:
        filename = request.GET.get('fileNameData')
        file_path = UploadModel.objects.filter(filename=filename).first()
        file_path = file_path.filePath

        if not os.path.exists(file_path):
            return JsonResponse({'Error': 'File not found.'})
        try:
            df = dataset(file_path)
            columnList = df.columns.tolist()
            return JsonResponse({"columns": columnList})
        except Exception as e:
            return JsonResponse({'Error': f'Error fetching columns: {str(e)}'})
    except:
        return HttpResponseServerError(f'Unable to get response fileNameData. Error:{str(e)}')


def CreateDataFrame(request):
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            columns = data.get('columns')
            filename = data.get('filename')
            if not columns and not filename:
                return HttpResponseBadRequest("Invalid File or Column Name(s).")
            else:
                path = UploadModel.objects.filter(filename=filename).first()
                path = path.filePath
                df = dataset(path)
                newDf = df[columns]
                return render(request, 'insights.html', {"Dataframe": newDf})
        else:
            return HttpResponseServerError(f'Only POST requests are supported.')
    except Exception as e:
        return HttpResponseServerError(f'Unable to create DataFrame Error:{str(e)}')
import json
import numpy as np
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from dataEngineering import utility,views
from esoft_utility import aws_config_utility
from esoft_utility.utility import read_file_from_s3
 
def transformDataFrame(df: pd.DataFrame, dateTransformation: bool=False) -> pd.DataFrame:
       
    """
    Preprocesses the given DataFrame according to specified transformations.
 
    Args:
    df (pd.DataFrame): The DataFrame to be transformed.
    dateTransformation (bool): Whether to apply date and time transformations.
 
    Returns:
    pd.DataFrame: The transformed DataFrame."""
    try:
        df = df.drop_duplicates()
 
        df = df.dropna()

        if dateTransformation:
            df['begin_transaction_date'] = pd.to_datetime(df['begin_transaction_date'])
            df['end_transaction_date'] = pd.to_datetime(df['end_transaction_date'])
            df['begin_transaction_time'] = pd.to_datetime(df['begin_transaction_time'], format='%Y-%m-%d %H:%M:%S.%f')
            df['end_transaction_time'] = pd.to_datetime(df['end_transaction_time'], format='%Y-%m-%d %H:%M:%S.%f')
            df['begin_transaction_time'] = df['begin_transaction_time'].dt.strftime('%H:%M:%S.%f').str[:-3]
            df['end_transaction_time'] = df['end_transaction_time'].dt.strftime('%H:%M:%S.%f').str[:-3]
 
            df['begindatetime'] = pd.to_datetime(df['begin_transaction_date'].dt.date.astype(str) + ' ' + df['begin_transaction_time'].astype(str))
            df['enddatetime'] = pd.to_datetime(df['end_transaction_date'].dt.date.astype(str) + ' ' + df['end_transaction_time'].astype(str))
 
            df.drop(['begin_transaction_date','begin_transaction_time','end_transaction_date','end_transaction_time'],axis=1,inplace=True)
 
    except pd.errors.ParserError as e:
        print(f"ParserError: {e}. There was an issue with parsing the date or time format.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return df
 
#Get List of files from Comparative analysis bucket
@api_view(['GET'])
def getFilesList(request):
    if request.method == 'GET':
        try:
            s3 = aws_config_utility.get_s3_client()
 
            bucket_name = aws_config_utility.get_comparative_analysis_data_bucket_name()
 
            response = s3.list_objects_v2(Bucket=bucket_name)
            files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.csv')]
 
            return JsonResponse({"files": files})
 
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
 
#Get Dataframe from s3 or Files
def getDataframe(request):
    if request.method == 'POST':
        try:
            if 'filename' in request.POST:
                filename = request.POST['filename']
                df = read_file_from_s3(filename, process='comparative data')
                if df is None:
                    return JsonResponse({'error': 'Error reading file from S3'}, status=500)
                else:
                    return df
               
            else:
                return JsonResponse({'error': 'No file or filename provided'}, status=400)
        except Exception as e:
            return ({'error': str(e)})
 
 
#TransactionBenchMark
@api_view(['POST'])
@csrf_exempt
def TransactionBenchMark(request):
    try:
        if request.method == 'POST':
            period = request.POST.get('period')
            response = getDataframe(request)
            df = pd.DataFrame()
            if isinstance(response,JsonResponse):
                return response
            elif isinstance(response, pd.DataFrame):
                df = response
            required_columns = [
                'transaction_code', 'transaction_name', 'begin_transaction_date', 'begin_transaction_time',
                'end_transaction_date', 'end_transaction_time', 'warehouse_id', 'sku_number', 'employee_code'
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return JsonResponse({'error': f"Missing columns in the Dataset: {', '.join(missing_columns)}"})
           
            df = df[required_columns]
            df = transformDataFrame(df=df, dateTransformation=True)
 
            df['elaspedtime'] = (df['enddatetime'] - df['begindatetime']).dt.total_seconds()
            df['elaspedtime'] = df['elaspedtime'].apply(np.floor)
 
            if period == 'month':
                df['month'] = df['begindatetime'].dt.month
                benchmark_df = read_file_from_s3("Transaction BenchMark/monthly_benchmark.csv", process='comparative process')
            elif period == 'quarter':
                df['quarter'] = df['begindatetime'].dt.quarter
                benchmark_df = read_file_from_s3('Transaction BenchMark/quarterly_benchmark.csv', process='comparative process')
            elif period == 'year':
                df['year'] = df['begindatetime'].dt.year
                benchmark_df = read_file_from_s3("Transaction BenchMark/yearly_benchmark.csv", process='comparative process')
            else:
                return JsonResponse({'error': f"Invalid period specified: {period}. Choose 'month', 'quarter', or 'year'."})
 
            merged_df = pd.merge(df, benchmark_df, on=['transaction_code', period], suffixes=('', '_benchmark'))
            merged_df['meets_benchmark'] = np.where(merged_df['elaspedtime'] <= merged_df['transaction_duration'], True, False)
            merged_df['duration_difference'] = merged_df['elaspedtime'] - merged_df['transaction_duration']
            merged_df = merged_df[['transaction_code', 'sku_number', 'employee_code', 'elaspedtime', 'transaction_duration', 'meets_benchmark', 'duration_difference']]
 
            non_compliant_df = merged_df[~merged_df['meets_benchmark']]
            employee_non_compliance = non_compliant_df.groupby(['employee_code']).size().reset_index(name='count')
 
            top_5_employees = employee_non_compliance.sort_values(by='count', ascending=False).head(5)
            top_5_employees.columns=['Employee ID','Count of not meeting benchmark']
            json_format = top_5_employees.to_json(orient='records')
 
            return JsonResponse({'data': json_format,'message':'TOP 5 Employee who are not meeting Transaction Wise Benchmark'})    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
   
 
@api_view(['POST'])
@csrf_exempt
def LostAndFoundAnalysis(request):
    try:
        if request.method == 'POST':
            subtype = request.POST.get('subtype')
            response = getDataframe(request)
 
            if isinstance(response, JsonResponse):
                return response
            elif isinstance(response, pd.DataFrame):
                df = response
 
            required_columns = [
                'transaction_code', 'warehouse_id', 'begin_transaction_date', 'begin_transaction_time',
                'sku_number', 'employee_code', 'start_location_id', 'end_location_id', 'transaction_quantity'
            ]
 
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return JsonResponse({'error': f"Missing columns in the Dataset: {', '.join(missing_columns)}"})
 
            df = df[required_columns]
            df = transformDataFrame(df=df, dateTransformation=False)
 
            df['begin_transaction_date'] = pd.to_datetime(df['begin_transaction_date'])
 
            lost_items = df[df['transaction_code'] == 801]
            found_items = df[df['transaction_code'] == 802]
            if subtype == 'item':
                lost_found_merged = pd.merge(
                    lost_items[['sku_number', 'begin_transaction_date', 'transaction_quantity', 'start_location_id']],
                    found_items[['sku_number', 'begin_transaction_date', 'transaction_quantity', 'end_location_id']],
                    left_on=['sku_number', 'start_location_id'],
                    right_on=['sku_number', 'end_location_id'],
                    suffixes=('_lost', '_found'),
                    how='left'
                )
 
                lost_found_merged['days_between'] = (
                    lost_found_merged['begin_transaction_date_found'] - lost_found_merged['begin_transaction_date_lost']
                ).dt.days
 
                lost_found_merged['begin_transaction_date_found'] = lost_found_merged['begin_transaction_date_found'].fillna('')
                lost_found_merged['transaction_quantity_found'] = lost_found_merged['transaction_quantity_found'].fillna('N/A')
                lost_found_merged['end_location_id'] = lost_found_merged['end_location_id'].fillna('N/A')
                lost_found_merged['days_between'] = lost_found_merged['days_between'].fillna('N/A')
 
                lost_found_merged['begin_transaction_date_lost'] = lost_found_merged['begin_transaction_date_lost'].dt.date
                lost_found_merged['begin_transaction_date_found'] = lost_found_merged['begin_transaction_date_found'].apply(
                    lambda x: x if x == '' else x.date()
                )
 
                lost_found_merged.rename(columns={
                    'begin_transaction_date_lost': 'item_lost_date',
                    'transaction_quantity_lost': 'lost_quantity',
                    'start_location_id': 'lost_location',
                    'begin_transaction_date_found': 'item_found_date',
                    'transaction_quantity_found': 'found_quantity',
                    'end_location_id': 'found_location'
                }, inplace=True)
 
                result = lost_found_merged[
                    ['sku_number', 'item_lost_date', 'lost_quantity', 'lost_location',
                    'item_found_date', 'found_quantity', 'days_between']
                ]
 
                message = 'Lost and found item analysis'
            elif subtype == 'location':
                lost_data = lost_items[['sku_number', 'transaction_quantity', 'start_location_id']].rename(
                    columns={'start_location_id': 'lost_location_id', 'transaction_quantity': 'lost_quantity'}
                )
 
                found_data = found_items[['sku_number', 'transaction_quantity', 'start_location_id']].rename(
                    columns={'start_location_id': 'found_location_id', 'transaction_quantity': 'found_quantity'}
                )
 
                location_status = pd.merge(
                    lost_data,
                    found_data,
                    on='sku_number',
                    how='left'
                )
 
                location_status['found_quantity'] = location_status['found_quantity'].fillna(0)
                location_status['found_location_id'] = location_status['found_location_id'].fillna('Not Found')
 
                result = location_status[['lost_location_id', 'lost_quantity', 'sku_number', 'found_location_id', 'found_quantity']]
                message = 'Location analysis'
 
            else:
                return JsonResponse({'error': f"Invalid subtype specified: {subtype}. Choose 'item' or 'location'."})
            result = result.fillna('Item Not Found!')
 
            result = result.head(10)
           
            result = result.to_dict(orient='records')
 
            return JsonResponse({'data': result, 'message': message})
 
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
   
 
 
@api_view(['POST'])
@csrf_exempt
def uniqueItemByMonth(request):
    try:
         if request.method == 'POST':
            sku_number = request.POST.get('sku_number')
            response = getDataframe(request)
            df = pd.DataFrame()
            if isinstance(response,JsonResponse):
                return response
            elif isinstance(response, pd.DataFrame):
                df = response
            print(df)
            required_columns = ['transaction_code', 'transaction_name','begin_transaction_date','warehouse_id','sku_number']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return JsonResponse({'error': f"Missing columns in the Dataset: {', '.join(missing_columns)}"})
           
            df =df[df['transaction_code']==151]
           
            df = df[required_columns]
            if sku_number not in df['sku_number'].unique():
                return JsonResponse({'error': f"SKU number {sku_number} has no records in the dataset."})
           
            df = transformDataFrame(df=df, dateTransformation=False)
 
            df['begin_transaction_date'] = pd.to_datetime(df['begin_transaction_date'])
            df['sku_number'] = df['sku_number'].astype(str)
 
            df['month'] = df['begin_transaction_date'].dt.strftime('%Y-%m')
 
            UniqueItemList = df.groupby(['month', 'warehouse_id'])['sku_number'].agg(lambda x: list(set(x))).reset_index()
            UniqueItemList.columns = ['Month', 'Warehouse_ID', 'Unique_SKUs_Received']
 
            UniqueItemList['Month'] = pd.to_datetime(UniqueItemList['Month'])
            UniqueItemList = UniqueItemList.sort_values('Month').tail(12)
 
            UniqueItemList['SKU_Number_Present'] = UniqueItemList['Unique_SKUs_Received'].apply(lambda x: sku_number in x)
            UniqueItemList['SKU_Number_Present'] = UniqueItemList['SKU_Number_Present'].apply(lambda x: 'Purchase Order Placed' if x else 'Purchase Order Not Placed')
 
            UniqueItemList['Month'] = UniqueItemList['Month'].dt.strftime('%Y-%m')
 
            result_df = UniqueItemList[['Month', 'SKU_Number_Present']]
 
            first_month = result_df['Month'].min()
            last_month = result_df['Month'].max()
            message = f"From the selected data, We have past months data from {first_month} to {last_month}."
            result_df = result_df.to_dict(orient='records')
            response_data = {
                'message': message,
                'data': result_df
            }
 
            return JsonResponse(response_data)
 
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
 
 
 
@api_view(['POST'])
@csrf_exempt
def ComparisionOfPRPS(request):
    try:
        if request.method != 'POST':
            return JsonResponse({'message': 'Invalid request method'}, status=400)
 
        params = {
            'month': request.POST.get('month'),
            'tran_type': request.POST.get('tran_type'),
            'analysis_type': request.POST.get('analysis_type'),
            'item_number': request.POST.get('item_number'),
            'supplier_id': request.POST.get('supplier_id'),
            'start_hour': request.POST.get('start_hour'),
            'end_hour': request.POST.get('end_hour'),
        }
 
        response = getDataframe(request)
 
        if isinstance(response, JsonResponse):
            return response
        elif isinstance(response, pd.DataFrame):
            df = response
            df_copy = df.copy()
        else:
            return JsonResponse({'error': 'Invalid response type'}, status=500)
 
        required_columns = [
                'tran_type', 'employee_id', 'receipt_id', 'item_number',
                'ordered_qty', 'received_qty', 'shipped_qty', 'HU_id', 'wh_id', 'Lot Number', 'supplier_id', 'start_tran_datetime', 'end_tran_datetime'
            ]
        missing_columns = [col for col in required_columns if col not in df_copy.columns]
        if missing_columns:
            return JsonResponse({'error': f"Columns required for this analysis: {', '.join(missing_columns)}"})
        
        if not params['analysis_type']:
            return JsonResponse({'error': 'Analysis type is required'})
       
        if ((params['month'] == '') or (params['month'] == None)) or ((params['tran_type'] == '') or (params['tran_type'] == None)):
            return JsonResponse({'error' : 'Either Month or Tran type required.'});
 
        df_copy['transaction_month'] = pd.to_datetime(df_copy['start_tran_datetime']).dt.month
 
        def filter_dataframe(df, **filters):
            for key, value in filters.items():
                if value is not None:
                    df = df[df[key] == (int(value) if key in ['transaction_month', 'item_number'] else value)]
            return df.head(15)
 
        def month_valid(df, month):
            return df['transaction_month'].isin([int(month)]).any() if month else True
 
        if params['month'] and not month_valid(df_copy, params['month']):
            return JsonResponse({'error': f'Month {params["month"]} transactions do not exist in the dataset.'})
       
        if params['analysis_type'] == 'Transaction_analysis':
            filters = {}
            if params['month']:
                filters['transaction_month'] = int(params['month'])
            if params.get('tran_type'):
                filters['tran_type'] = params['tran_type']
 
            df_filtered = filter_dataframe(df_copy, **filters)
            if df_filtered.empty:
                return JsonResponse({'error': 'No transactions found for the given parameters.'})
            aggregated_df = df_filtered.groupby(['transaction_month', 'tran_type'], as_index=False)['ordered_qty'].sum().sort_values(by='ordered_qty', ascending=False)
            if params['tran_type'] == 'Receipt':
                aggregated_df = aggregated_df.rename(columns={'ordered_qty': 'Received_qty'})
            else:
                aggregated_df = aggregated_df.rename(columns={'ordered_qty': 'Shipment_qty'})
 
        elif params['analysis_type'] == 'Item_analysis':
            filters = {'tran_type': params['tran_type']}
            if params['item_number']:
                item_number = int(params['item_number'])
                if not df_copy['item_number'].isin([item_number]).any():
                    return JsonResponse({'error': f'Item number {item_number} does not exist in the dataset.'})
                filters['item_number'] = item_number
            if params['month']:
                filters['transaction_month'] = int(params['month'])
            df_filtered = filter_dataframe(df_copy, **filters)
            if df_filtered.empty:
                return JsonResponse({'error': 'No transactions found for the given parameters.'})
            aggregated_df = df_filtered.groupby(['item_number', 'tran_type', 'start_tran_datetime', 'end_tran_datetime'], as_index=False)['ordered_qty'].sum().sort_values(by='ordered_qty', ascending=False)
            if params['tran_type'] == 'Receipt':
                aggregated_df = aggregated_df.rename(columns={'ordered_qty': 'Received_qty'})
            else:
                aggregated_df = aggregated_df.rename(columns={'ordered_qty': 'Shipment_qty'})
 
        elif params['analysis_type'] == 'Supplier_analysis':
            errors = []
            if params['supplier_id']:
                if not df_copy['supplier_id'].isin([params['supplier_id']]).any():
                    errors.append(f'Supplier ID {params["supplier_id"]} does not exist in the dataset.')
            if params['item_number']:
                item_number = int(params['item_number'])
                if not df_copy['item_number'].isin([item_number]).any():
                    errors.append(f'Item Number {item_number} does not exist in the dataset.')
            if errors:
                return JsonResponse({'error': ' '.join(errors)})
 
            filters = {'tran_type': params['tran_type']}
            if params['month']:
                filters['transaction_month'] = int(params['month'])
            if params['item_number']:
                filters['item_number'] = int(params['item_number'])
            if params['supplier_id']:
                filters['supplier_id'] = params['supplier_id']
            df_filtered = filter_dataframe(df_copy, **filters)
            if df_filtered.empty:
                return JsonResponse({'error': 'No transactions found for the given parameters.'})
            aggregated_df = df_filtered.groupby(['supplier_id', 'tran_type', 'item_number'], as_index=False)['ordered_qty'].sum().sort_values(by='ordered_qty', ascending=False)
            if params['tran_type'] == 'Receipt':
                aggregated_df = aggregated_df.rename(columns={'ordered_qty': 'Received_qty'})
            else:
                aggregated_df = aggregated_df.rename(columns={'ordered_qty': 'Shipment_qty'})
 
        elif params['analysis_type'] == 'Time_analysis':
            filters = {'tran_type': params['tran_type']}
            if params['month']:
                filters['transaction_month'] = int(params['month'])
            if params['item_number']:
                filters['item_number'] = int(params['item_number'])
            df_filtered = filter_dataframe(df_copy, **filters)
            if df_filtered.empty:
                return JsonResponse({'error': 'No transactions found for the given parameters.'})
 
            if params['start_hour'] and params['end_hour']:
                start_time = int(params['start_hour'])
                end_time = int(params['end_hour'])
                df_filtered = df_filtered[(pd.to_datetime(df_filtered['start_tran_datetime']).dt.hour >= start_time) & (pd.to_datetime(df_filtered['end_tran_datetime']).dt.hour <= end_time)]
            else:
                hour = int(params['start_hour'] or params['end_hour'])
                df_filtered = df_filtered[(pd.to_datetime(df_filtered['start_tran_datetime']).dt.hour == hour) | (pd.to_datetime(df_filtered['end_tran_datetime']).dt.hour == hour)]
 
            if df_filtered.empty:
                return JsonResponse({'error': 'No transactions found for the given parameters.'})
            aggregated_df = df_filtered.groupby(['transaction_month', 'tran_type', 'item_number', 'start_tran_datetime', 'end_tran_datetime'], as_index=False)['ordered_qty'].sum().sort_values(by='ordered_qty', ascending=False)
            if params['tran_type'] == 'Receipt':
                aggregated_df = aggregated_df.rename(columns={'ordered_qty': 'Received_qty'})
            else:
                aggregated_df = aggregated_df.rename(columns={'ordered_qty': 'Shipment_qty'})
        elif params['analysis_type'] == 'Discrepancy_analysis':
            filters = {'tran_type': params['tran_type']}
            if params['month']:
                filters['transaction_month'] = int(params['month'])
            if params['item_number']:
                filters['item_number'] = int(params['item_number'])
            df_filtered = filter_dataframe(df_copy, **filters)
            if df_filtered.empty:
                return JsonResponse({'error': 'No transactions found for the given parameters.'})
 
            if params['tran_type'] == 'Receipt':
                df_discrepancy = df_filtered[(df_filtered['tran_type'] == 'Receipt') & (df_filtered['ordered_qty'] != df_filtered['received_qty'])]
            elif params['tran_type'] == 'Shipment':
                df_discrepancy = df_filtered[(df_filtered['tran_type'] == 'Shipment') & (df_filtered['shipped_qty'] != df_filtered['received_qty'])]
            else:
                df_discrepancy = df_filtered[((df_filtered['tran_type'] == 'Receipt') & (df_filtered['ordered_qty'] != df_filtered['received_qty'])) | ((df_filtered['tran_type'] == 'Shipment') & (df_filtered['shipped_qty'] != df_filtered['received_qty']))]
 
            if df_discrepancy.empty:
                return JsonResponse({'error': 'No discrepancies found for the given parameters.'})
            if 'Receipt' in df_discrepancy['tran_type'].values:
                df_discrepancy.loc[df_discrepancy['tran_type'] == 'Receipt', 'discrepancy'] = \
                    df_discrepancy['ordered_qty'] - df_discrepancy['received_qty']
            if 'Shipment' in df_discrepancy['tran_type'].values:
                df_discrepancy.loc[df_discrepancy['tran_type'] == 'Shipment', 'discrepancy'] = \
                    df_discrepancy['received_qty'] - df_discrepancy['shipped_qty']
            aggregated_df = df_discrepancy.groupby(['transaction_month', 'tran_type', 'item_number', 'ordered_qty', 'received_qty', 'shipped_qty'], as_index=False)['discrepancy'].sum().sort_values(by='discrepancy', ascending=False)
 
        else:
            return JsonResponse({'error': 'Invalid analysis type'})
 
        result = aggregated_df.to_json(orient='records')
        return JsonResponse({'data': result}, status=200)
 
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
@csrf_exempt
def damageProducts(request):
    try:
        if request.method == 'POST':
            analysis_categories = request.POST.get('analysis_categories',[])  
            analysis_categories = [category.strip() for category in analysis_categories.split(',') if category.strip()]
 
            analysis_type = request.POST.get('analysis_type')  
 
            response = getDataframe(request)
            df = pd.DataFrame()
            if isinstance(response, JsonResponse):
                return response
            elif isinstance(response, pd.DataFrame):
                df = response
 
            if df.empty or not analysis_categories or not analysis_type:
                return JsonResponse({'error': "Invalid input data, analysis categories, or analysis type missing"}, status=400)
           
            required_columns = ['transaction_log_id', 'transaction_code', 'transaction_name', 'warehouse_id', 'employee_code', 'sku_number', 'transaction_quantity', 'end_location_id', 'reason_id']
            missing_columns = [col for col in required_columns if col not in df.columns]
           
            if missing_columns:
                return JsonResponse({'error': f"Missing columns in the Dataset: {''.join(missing_columns)}"}, status=400)
           
            df = df.drop(columns=['transaction_log_id'])
 
            if not ((df['transaction_code'] == 151).all() and (df['transaction_name'] == 'Staged Receipt (Rcpt)').all() and (df['reason_id'] == 3).all()):
                return JsonResponse({'error': "Transaction code, name, or reason ID is incorrect."}, status=400)
           
            category_columns = [
                'Employee Code',
                'Item Number',
                'Equipment ID'
            ]
           
            invalid_categories = [category for category in analysis_categories if category in category_columns]
 
            if len(invalid_categories) == 0:
                return JsonResponse({'error': f"Invalid analysis category(ies): {''.join(invalid_categories)}"}, status=400)
 
            if not analysis_categories or not analysis_type:
                return JsonResponse({'error': "Invalid input data, analysis categories, or analysis type missing"}, status=400)
           
           
            category_column_mapping = {
                'Employee Code': 'employee_code',
                'Item Number': 'sku_number',
                'Equipment ID': 'end_location_id'
            }
 
            selected_columns = [category_column_mapping[category] for category in invalid_categories]
 
            if analysis_type == 'Total Damage Quantity':
                try:
                    result_df = df.groupby(selected_columns)['transaction_quantity'].sum().reset_index().sort_values(by='transaction_quantity', ascending=False)
                    result_df.columns = [category.replace('_', ' ').title() for category in selected_columns] + ['Total Damaged Quantity']
                except KeyError as e:
                    return JsonResponse({'error': f"Column missing in DataFrame: {str(e)}"}, status=400)
                except Exception as e:
                    return JsonResponse({'error': f"An error occurred during analysis: {str(e)}"}, status=500)
               
            elif analysis_type == 'Total Damage Count':
                try:
                    result_df = df.groupby(selected_columns).size().reset_index(name='damage_count').sort_values(by='damage_count', ascending=False)
                    result_df.columns = [category.replace('_', ' ').title() for category in selected_columns] + ['Damage Count']
                except KeyError as e:
                    return JsonResponse({'error': f"Column missing in DataFrame: {str(e)}"}, status=400)
                except Exception as e:
                    return JsonResponse({'error': f"An error occurred during analysis: {str(e)}"}, status=500)
 
            else:
                return JsonResponse({'error': "Invalid analysis type provided"}, status=400)
 
            message = f"Damaged Products Report"
 
            result_dict = result_df.head(10).to_dict(orient='records')
            key_mapping = {
                "Sku Number": "Item Number",
                "Employee Code": "Employee Code",  
                "End Location Id": "Equipment ID",
                "Total Damaged Quantity": "Total Damaged Quantity"  
            }
 
            renamed_result_dict = [
                {key_mapping.get(key, key): value for key, value in record.items()}
                for record in result_dict
            ]
 
            response_data = {
                'message': message,
                'data': renamed_result_dict
            }
            return JsonResponse(response_data)
 
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)   
 
 
@api_view(['POST'])
@csrf_exempt
def ShortShippedOrderAnalysis(request):
    try:
        if request.method == 'POST':
            month = request.POST.get('month')
            year = request.POST.get('year')
            analysis_type = request.POST.get('analysis_type')
            
            response = getDataframe(request)
            df = pd.DataFrame()
            if isinstance(response,JsonResponse):
                return response
            elif isinstance(response, pd.DataFrame):
                df = response
            def filtered_dataframe(df, **filters):
                for key, value in filters.items():
                    print(key,value)
                    if value is not None:
                        df = df[df[key] == (int(value) if key in ['month', 'year'] else value)]
                    
                return df
            required_columns = ['OrderId', 'SKU_Number', 'CustomerId', 'Ordered_Quantity','Shipped_Quantity', 'inventory_Quantity_before_order', 'Ordered_date']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return JsonResponse({'error': f"Missing columns in the Dataset: {', '.join(missing_columns)}"})
            filters = {}
            df['Ordered_date'] = pd.to_datetime(df['Ordered_date'], errors='coerce')
 
            df['month'] = df['Ordered_date'].dt.month
            df['year'] = df['Ordered_date'].dt.year
            df['month_year'] = df['Ordered_date'].dt.to_period('M').astype(str)
           
            if month != '' or year != '':
                if month !='' and year=='':
                    return JsonResponse({'error': "Year is mandatory if month is provided."})
 
                if month !='':
                    filters['month'] = int(month)
                if year !='':
                    filters['year'] = int(year)
 
                df = filtered_dataframe(df, **filters)
 
            if df.empty:
                return JsonResponse({'error': f"There are no ShortShipped Orders in {month if month else ''} {year if year else ''}"})
 
            df['Short_Shipped_Quantity'] = df['Ordered_Quantity'] - df['Shipped_Quantity']
            df = df[df['Short_Shipped_Quantity'] > 0]
            if month =='' and year =='':
                group_by_columns = ['SKU_Number', 'month_year'] if analysis_type == 'item' else ['CustomerId', 'month_year']

                result = df.groupby(group_by_columns)['Short_Shipped_Quantity'].sum().reset_index()

                result = result.sort_values(by=['Short_Shipped_Quantity', 'month_year'], ascending=[False, True])
            elif month != '' and year != '':
                group_by_columns = ['SKU_Number'] if analysis_type == 'item' else ['CustomerId']

                result = df.groupby(group_by_columns)['Short_Shipped_Quantity'].sum().reset_index()

                result = result.sort_values(by='Short_Shipped_Quantity', ascending=False)
            elif year != '':
                group_by_columns = ['SKU_Number', 'year'] if analysis_type == 'item' else ['CustomerId', 'year']

                result = df.groupby(group_by_columns)['Short_Shipped_Quantity'].sum().reset_index()

                result = result.sort_values(by=['Short_Shipped_Quantity', 'year'], ascending=[False, True])
 
            if month is not None and year is not None:
                if analysis_type == 'item':
                    result_df = result.loc[:, ['SKU_Number', 'Short_Shipped_Quantity']]
                    message = f'ShortShipped Orders in {month} - {year} Based on Items '
                elif analysis_type == 'customer':
                    result_df = result.loc[:, ['CustomerId', 'Short_Shipped_Quantity']]
                    message = f'ShortShipped Orders in {month} - {year} Based on Customer'
            else:
                if analysis_type == 'item':
                    result_df = result.loc[:, ['SKU_Number', 'month_year', 'Short_Shipped_Quantity']]
                    message = 'ShortShipped Orders Based on Items'
                elif analysis_type == 'customer':
                    result_df = result.loc[:, ['CustomerId', 'month_year', 'Short_Shipped_Quantity']]
                    message = 'ShortShipped Orders Based on Customer'
            response_data = {
                'message': message,
                'data': result_df.to_json(orient='records')
            }
            return JsonResponse(response_data)
    except Exception as e:
        print(e)
        return JsonResponse({'error': "internal server error"}, status=500)
import boto3
import requests
import nbformat
from esoft_utility import aws_config_utility
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import ClientError
from django.http import JsonResponse

def extract_model_and_check_requirements(s3_bucket, key_prefix, category):
    """
    Extract model directory from S3 and check if requirements.txt file exists.
    If the file exists, print a message that the model is sent for processing.
    If the file does not exist, create a requirements.txt file in the model folder
    and update it with dependencies extracted from Python files.

    Args:
    - s3_bucket (str): The name of the S3 bucket.
    - key_prefix (str): The key prefix (directory path) of the model directory in the S3 bucket.
    - category(str): Model Category
    """
    try:
        # Create a session using your AWS credentials
        session = boto3.Session(
            aws_access_key_id=aws_config_utility.get_aws_access_key_id(),
            aws_secret_access_key=aws_config_utility.get_aws_secret_access_key()
        )

        # Create an S3 resource using the session
        s3_resource = session.resource('s3')
        # Check if requirements.txt file exists in the S3 bucket
        requirements_file_key = f"{key_prefix}/requirements.txt"
        requirements_file_exists = False
        for obj in s3_resource.Bucket(s3_bucket).objects.filter(Prefix=requirements_file_key):
            if obj.key == requirements_file_key:
                requirements_file_exists = True
                break
        if requirements_file_exists:
            print(f"{key_prefix} Model is sent for processing. requirements.txt file exists.")
            model_resp = send_model_for_processing(key_prefix, s3_bucket, category)
            return model_resp
        else:
            # Create requirements.txt file from Python files in the model directory
            result = create_requirements_file(s3_bucket, key_prefix)
            if result:
                model_resp = send_model_for_processing(key_prefix, s3_bucket, category)
                print(model_resp)
                return model_resp
    except NoCredentialsError:
        print("AWS credentials not available. Make sure to provide AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.")
    except Exception as e:
        return f"An error occurred: {str(e)}"

def send_model_for_processing(model_name, bucket, category):
    url = "http://esoft-uat-1681494035.us-east-1.elb.amazonaws.com:8089/store_data"
    pay_laod = {
        "model_name": model_name,
        "bucket_name": bucket,
        "category": category,
        "folder_name": model_name
    }
    print(pay_laod)
    try:
        response = requests.post(url, json=pay_laod)
        response.raise_for_status() 
        if 'Error' in response.text:
            return response.text
        return response;
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: {e}")
        return None

def create_requirements_file(s3_bucket, key_prefix):
    """
    Create a requirements.txt file in the model directory in S3
    and update it with dependencies extracted from Python files.

    Args:
    - s3_bucket (str): The name of the S3 bucket.
    - key_prefix (str): The key prefix (directory path) of the model directory in the S3 bucket.
    """
    try:
        
        s3_client = aws_config_utility.get_s3_client()
        python_files = []
        notebook_files = []
        python_dependencies = ['pandas','numpy','matplotlib','nltk','scikit-learn','tensorflow','seaborn']
        for obj in s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=key_prefix)['Contents']:
            if obj['Key'].endswith('.py'):
                python_files.append(obj['Key'])
            elif obj['Key'].endswith('.ipynb'):
                notebook_files.append(obj['Key'])
        if len(python_files) == 0 and len(notebook_files) == 0:
            return "No .py and .ipynb file found in uploaded folder"
        requirements_file_content = ''
        for python_file in python_files:
            obj = s3_client.get_object(Bucket=s3_bucket, Key=python_file)
            body = obj['Body'].read().decode('utf-8')
            data = body.split('\n')
            dependencies = extract_python_dependencies(data)
            python_dependencies.extend(dependencies)

        for notebook_file in notebook_files:
            obj = s3_client.get_object(Bucket=s3_bucket, Key=notebook_file)
            body = obj['Body'].read().decode('utf-8')
            nb = nbformat.reads(body, as_version=4)
            exporter = PythonExporter()
            python_script, _ = exporter.from_notebook_node(nb)
            data = python_script.split('\n')
            dependencies = extract_python_dependencies(data)
            python_dependencies.extend(dependencies)
        requirements_file_content = '\n'.join(list(set(python_dependencies)))
        requirements_file_key = f"{key_prefix}/requirements.txt"
        s3_client.put_object(Bucket=s3_bucket, Key=requirements_file_key, Body=requirements_file_content.encode('utf-8'))
        return True
    except Exception as e:
        return f"An error occurred: {str(e)}"
        print(f"An error occurred while creating requirements.txt: {e}")

def extract_python_dependencies(data):
    """
    Extract Python dependencies from import statements.

    Args:
    - imports (list): List of import statements.

    Returns:
    - list: List of Python dependencies.
    """

    '''standard_libraries.txt file contains most used libraries in ML
    to compare with exctraceted ones and eclude local libraries'''
    with open("analytics/standard_libraries.txt", 'r') as f:
        required_libraries = [line.strip().lower() for line in f]
    python_dependencies = []
    for line in data:
        if line.startswith('import'):
            package_name = line.split()[1].split('.')[0]
            if(package_name.lower()=='sklearn'):
                package_name =  'scikit-learn'
            if package_name.lower() in required_libraries:  
                python_dependencies.append(package_name)
        elif line.startswith('from'):
            package_name = line.split()[1].split('.')[0]
            if(package_name.lower()=='sklearn'):
                package_name =  'scikit-learn'
            if package_name.lower() in required_libraries:
                python_dependencies.append(package_name)
            if ' as ' in line:
                alias_name = line.split(' as ')[1].split()[0]
                if(alias_name.lower()=='sklearn'):
                    alias_name =  'scikit-learn'
                if alias_name.lower() in required_libraries:
                    python_dependencies.append(alias_name)
    return python_dependencies


def models_upload_s3(uploaded_files, modelname, category):
    try:
        s3 = aws_config_utility.get_s3_client()
        bucket_name=aws_config_utility.get_models_bucket_name()
        create_model_directory_if_not_exists(s3, bucket_name, modelname)
        for uploaded_file in uploaded_files:
            try:
                filee_key = modelname + '/' + uploaded_file.name
                s3.upload_fileobj(uploaded_file, bucket_name, filee_key)
            except ClientError as e:
                return JsonResponse({'error': f"Failed to upload file {uploaded_file.name} to S3: {e}"}, status=500)
        return extract_model_and_check_requirements(bucket_name,modelname,category)
    except ClientError as e:
        return f'Model unable to Upload Server issue {str(e)}'


def create_model_directory_if_not_exists(s3, bucket_name, folder_name):

    try:
        s3.head_object(Bucket=bucket_name, Key=folder_name + '/')
        print(f"Folder '{folder_name}' already exists in bucket '{bucket_name}'.")
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            s3.put_object(Bucket=bucket_name, Key=folder_name + '/')
            print(f"Folder '{folder_name}' created in bucket '{bucket_name}'.")
        else:
            print(f"Error: {e}")

def get_s3_models_from_bucket():
    try:
        s3 = aws_config_utility.get_s3_client()
        bucket_name = 'eslplt-data-models'
        response = s3.list_objects_v2(Bucket=bucket_name, Delimiter='/')
        all_folders = [prefix.get('Prefix')[:-1] for prefix in response.get('CommonPrefixes', [])]
        listModels = list(all_folders)
        return listModels
    except Exception as e:
        print(str(e))
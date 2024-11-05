import subprocess
import os
import shutil
from esoft_utility import aws_config_utility
def create_venv(venv_name):
    subprocess.run(["python", "-m", "venv", venv_name+"_venv"], check=True)

def activate_venv(venv_name):
    if os.name == 'posix': 
        activate_cmd = f"{venv_name}/bin/python"
    elif os.name == 'nt': 
        activate_cmd = f"{venv_name}\\Scripts\\python.exe"
    else:
        raise OSError("Unsupported operating system")
    return activate_cmd

def install_requirements(venv_name,requirements_file):
    venv_python = activate_venv(venv_name)
    subprocess.run([venv_python, "-m", "pip", "install", "-r", requirements_file], check=True)

def run_python_file(venv_name):
    activate_cmd = activate_venv(venv_name)
    subprocess.run([activate_cmd,"manage.py","runserver"])

def uninstall_requirements(venv_name, requirements_file):
    venv_python = activate_venv(venv_name)
    subprocess.run([venv_python, "-m", "pip", "uninstall", "-r", requirements_file, "-y"], check=True)


def delete_venv(venv_path):
    shutil.rmtree(venv_path)

''' 
method to install the requirements from s3 bucket
'''
def check_installation_work(model_name,bucket_name):
    try:
        create_venv(model_name)
        print("virtual environment created")
        file_name='requirements.txt'
        object_key = f"{model_name}/{file_name}"
        s3 = aws_config_utility.get_s3_client()
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        
        
        file_content = response['Body'].read().decode('utf-8') 
        if file_content:
            dependencies = file_content.split('\n')
        print(dependencies)
        virtualname=model_name+"_venv"
        pip_path=f"{virtualname}/bin/pip" if os.name == 'posix' else f"{virtualname}\\Scripts\\pip"
        
        for dependency in dependencies:
            if dependency.strip(): 
                print(dependency)
                subprocess.run([pip_path, 'install', dependency.strip()], shell=True)
    except Exception as e:
        print(str(e))
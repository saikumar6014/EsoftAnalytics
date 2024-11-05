import requests
import json
import pandas as pd
from requests.exceptions import RequestException
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")


def model_score(experiment_name):
    print('Experiment Name:', experiment_name)
    try:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            print(f"Experiment '{experiment_name}' not found.")
            return None, None
        experiment_id = experiment.experiment_id
    except Exception as e:
        print('Error retrieving experiment:', str(e))
        return None, None

    print('Experiment ID:', experiment_id)

    # Define the request payload
    payload = {
        "experiment_ids": [experiment_id]
    }

    headers = {
        'Content-Type': 'application/json'
    }

    try:
        # Make the request
        response = requests.post("http://localhost:5000/api/2.0/mlflow/runs/search", json=payload, headers=headers)
        response.raise_for_status()  # Raises HTTPError for bad responses
    except RequestException as e:
        print('Request Error:', str(e))
        return None, None

    # Parse the response
    if response.status_code == 200:
        try:
            runs = response.json().get('runs', [])
            score = None
            metric_type = None

            for run_info in runs:
                metrics = run_info['data'].get('metrics', [])

                for metric in metrics:
                    key = metric['key']
                    value = metric['value']

                    if key == 'r2_score':
                        score = value
                        metric_type = 'continuous'
                    elif key == 'accuracy':
                        score = value
                        metric_type = 'categorical'
                    elif key == 'silhouette_score' or key == 'inertia':
                        score = value
                        metric_type = 'clustering'

            if score is not None:
                print(f"Selected Metric: {key}, Score: {score}, Metric Type: {metric_type}")
                return score, metric_type, key
            else:
                print("No relevant metrics found.")
                return None, None

        except KeyError as e:
            print(f"Error parsing JSON response: {e}")
            return None, None
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None, None


def PredictedModel(df, model, url="http://esoft-demo-2144439465.us-east-1.elb.amazonaws.com:8080/"):
    """Sends a DataFrame to a specified model endpoint for prediction."""
    try:
        df_id = df['esoft_ID'].copy()
        df.drop(columns='esoft_ID', inplace=True)

        full_url = url + model
        print('Full URL:', full_url)

        score, metric_type, key = model_score(model)
        if score is None or metric_type is None:
            print("Error: No valid metric found for the model.")
            return None

        # Adjust score based on metric type
        if metric_type == 'continuous' or metric_type == 'categorical':
            metric = int(score * 100)
        elif metric_type == 'clustering':
            metric = score  # Assuming silhouette or inertia score is already in a useful format
        else:
            print("Error: Unrecognized metric type.")
            return None

        if len(df.columns) > 1:
            payload = df.to_dict(orient='records')
        else:
            payload = {"texts": df.iloc[:, 0].to_list()}

        headers = {'Content-Type': 'application/json'}
        response = requests.post(full_url, json=payload, headers=headers)

        if response.ok:
            try:
                model_data = response.json().get("results", [])
                column = response.json().get('column')
                df_result = pd.DataFrame(model_data)

                if len(df.columns) > 1:
                    if column is None:
                        df_result.columns = ['predictedResult']
                        column = 'predictedResult'
                    else:
                        df_result.columns = [column]
                df.insert(0, 'esoft_ID', df_id)

                combined_df = pd.concat([df, df_result], axis=1)
                combined_df = combined_df[df.columns.tolist() + df_result.columns.tolist()]

                combined_df_resp = combined_df.to_json(orient='records')
                print('Combined DataFrame:', combined_df_resp)
                dict = {'Prediction': combined_df_resp, 'Metric Type': metric_type, "Metric": metric, 'key': key,
                        'column': column}
                print(dict)
                return dict
            except Exception as e:
                print("Error processing API response:", e)
                return None
        else:
            print("POST request failed with status code:", response.status_code)
            return None
    except Exception as e:
        print(e)
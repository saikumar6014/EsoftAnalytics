from django.http import HttpResponse
import boto3
import pandas as pd
from sqlalchemy import create_engine
# from cassandra.cluster import Cluster
from pymongo import MongoClient
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

def connect_db(request, db_type):
    if db_type == 'MySQL':
        connection_string = request.POST.get('mysql_connection_string')
        table_name = request.POST.get('mysql_tablename')
        df = connect_and_query_sqlalchemy(connection_string, table_name)
    elif db_type == 'PostgreSQL':
        connection_string = request.POST.get('postgresql_connection_string')
        table_name = request.POST.get('postgresql_tablename')
        df = connect_and_query_sqlalchemy(connection_string, table_name)
    elif db_type == 'SQLite':
        file_path = request.POST.get('sqlite_file_path')
        table_name = request.POST.get('sqlite_tablename')
        connection_string = f'sqlite:///{file_path}'
        df = connect_and_query_sqlalchemy(connection_string, table_name)
    elif db_type == 'Oracle':
        connection_string = request.POST.get('oracle_connection_string')
        table_name = request.POST.get('oracle_tablename')
        df = connect_and_query_sqlalchemy(connection_string, table_name)
    elif db_type == 'Microsoft SQL Server':
        connection_string = request.POST.get('mssql_connection_string')
        table_name = request.POST.get('postgresql_tablename')
        df = connect_and_query_sqlalchemy(connection_string, table_name)
    elif db_type == 'Cassandra':
        contact_points = request.POST.get('cassandra_contact_points').split(',')
        port = int(request.POST.get('cassandraPort'))
        keyspace = request.POST.get('cassandraPort')
        table_name = request.POST.get('cassandra_tablename')
        df = connect_and_query_cassandra(contact_points, port, keyspace, table_name)
    elif db_type == 'DynamoDB':
        table_name = request.POST.get('dynamodb_tablename')
        df = connect_and_query_dynamodb(table_name)
    elif db_type == 'MonogDB':
        connection_string = request.POST.get('mongodb_connection_string')
        collection_name = request.POST.get('mongodb_collectionname')
        df = connect_and_query_mongodb(connection_string, collection_name)
    else:
        return HttpResponse("Invalid database type selected.")

    if df is not None:
        return HttpResponse(df.to_html())
    else:
        return HttpResponse("No data returned or an error occurred.")


def connect_and_query_sqlalchemy(connection_string, table_name):
    try:
        engine = create_engine(connection_string)
        with engine.connect() as connection:
            query = f'SELECT * FROM {table_name}'
            df = pd.read_sql_query(query, connection)
        return df
    except Exception as e:
        print(f"Error: {e}")
        return None

def connect_and_query_cassandra(contact_points, port, keyspace, table_name):
    try:
        cluster = Cluster(contact_points=contact_points, port=port)
        session = cluster.connect(keyspace)
        query = f'SELECT * FROM {table_name}'
        rows = session.execute(query)
        df = pd.DataFrame(rows)
        return df
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        if cluster:
            cluster.shutdown()


def connect_and_query_dynamodb(table_name):
    try:
        session = boto3.Session()
        dynamodb = session.resource('dynamodb')
        table = dynamodb.Table(table_name)
        response = table.scan()
        items = response.get('Items', [])
        df = pd.DataFrame(items)
        return df
    except (NoCredentialsError, PartialCredentialsError) as e:
        print(f"Credentials error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def connect_and_query_mongodb(connection_string, collection_name):
    try:
        client = MongoClient(connection_string)
        db = client.get_database()
        collection = db.get_collection(collection_name)
        cursor = collection.find({})
        df = pd.DataFrame(list(cursor))
        return df
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        if client:
            client.close()

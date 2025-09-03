import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import io
import logging
import csv

logger = logging.getLogger(__name__)

def get_s3_client():
    try:
        s3_client = boto3.client('s3')
        return s3_client
    except NoCredentialsError:
        print("Credentials not available.")
        return None
    except ClientError as e:
        print(f"Error creating S3 client: {e}")
        return None
    
def upload_file(file_obj, bucket_name, object_name):
    s3_client = get_s3_client()
    if s3_client is None:
        return False

    try:
        s3_client.upload_fileobj(file_obj, bucket_name, object_name)
        print(f"File uploaded to {bucket_name}/{object_name}")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"Bucket {bucket_name} not found.")
            return "BucketNotFound"
        print(f"Error uploading file: {e}")
        return "ClientError"

def download_file(bucket_name, object_name):
    s3_client = get_s3_client()
    if s3_client is None:
        return None

    
    try:
        file_obj = io.BytesIO()
        logger.debug(f'object_name in download file is: {object_name}')
        s3_client.download_fileobj(bucket_name, object_name, file_obj)
        file_obj.seek(0)  # Volver al inicio del archivo
        
        return  file_obj 
    except ClientError as e:
        print(f"Error downloading file: {e}")
        return None
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

r2 = boto3.client(
    's3',
    endpoint_url='https://f76d2ce8d05a169a24d24d6895c13dd7.r2.cloudflarestorage.com',
    aws_access_key_id='8a88c9ea5c1eab615f51fc6d339e5550',
    aws_secret_access_key='0dab2a649eef436523a727b883ef8267731187d906f196e8d47990ea5c012057',
    region_name='auto'
)

BUCKET_VIDEOS  = 'sportsai-videos'
BUCKET_OUTPUTS = 'sportsai-outputs'
BUCKET_MODELS  = 'sportsai-models'

def upload_video(file_path, filename):
    r2.upload_file(file_path, BUCKET_VIDEOS, filename)
    print(f"Uploaded {filename} to sportsai-videos")

def download_video(filename, save_path):
    r2.download_file(BUCKET_VIDEOS, filename, save_path)
    print(f"Downloaded {filename} to {save_path}")

def upload_output(file_path, filename):
    r2.upload_file(file_path, BUCKET_OUTPUTS, filename)
    print(f"Uploaded {filename} to sportsai-outputs")

def download_output(filename, save_path):
    r2.download_file(BUCKET_OUTPUTS, filename, save_path)
    print(f"Downloaded {filename} to {save_path}")

def upload_model(file_path, model_name):
    r2.upload_file(file_path, BUCKET_MODELS, model_name)
    print(f"Uploaded model {model_name} to sportsai-models")

def download_model(model_name, save_path):
    r2.download_file(BUCKET_MODELS, model_name, save_path)
    print(f"Downloaded model {model_name} to {save_path}")

def list_videos():
    response = r2.list_objects_v2(Bucket=BUCKET_VIDEOS)
    return [obj['Key'] for obj in response.get('Contents', [])]

def list_outputs():
    response = r2.list_objects_v2(Bucket=BUCKET_OUTPUTS)
    return [obj['Key'] for obj in response.get('Contents', [])]

def delete_video(filename):
    r2.delete_object(Bucket=BUCKET_VIDEOS, Key=filename)
    print(f"Deleted {filename} from sportsai-videos")
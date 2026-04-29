import boto3

r2 = boto3.client(
    's3',
    endpoint_url='https://f76d2ce8d05a169a24d24d6895c13dd7.r2.cloudflarestorage.com',
    aws_access_key_id='8a88c9ea5c1eab615f51fc6d339e5550',
    aws_secret_access_key='0dab2a649eef436523a727b883ef8267731187d906f196e8d47990ea5c012057',
    region_name='auto'
)

try:
    response = r2.list_objects_v2(Bucket='sportsai-videos')
    print("Connected to R2 successfully!")
    print(f"Files in sportsai-videos: {response.get('KeyCount', 0)}")
except Exception as e:
    print(f"Connection failed: {e}")
FROM python:3.11-slim 
WORKDIR /app 
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 ffmpeg && rm -rf /var/lib/apt/lists/* 
COPY requirements_worker.txt . 
RUN pip install --no-cache-dir -r requirements_worker.txt 
COPY r2_storage.py . 
COPY worker.py . 
CMD ["python", "worker.py"] 

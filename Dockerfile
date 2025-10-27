FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir pillow exifread
COPY sync.py run.sh ./
RUN chmod +x /app/run.sh

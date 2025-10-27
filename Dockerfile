FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir pillow exifread tqdm

COPY sync.py run.sh ./
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]

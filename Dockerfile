FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir pillow exifread

COPY sync.py /app/sync.py
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]

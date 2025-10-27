FROM python:3.11-slim

WORKDIR /app

# Устанавливаем tqdm (опционально, если будешь использовать)
RUN pip install --no-cache-dir tqdm

COPY sync.py /app/sync.py
COPY run.sh /app/run.sh

RUN chmod +x /app/run.sh

ENV PYTHONUNBUFFERED=1

CMD ["/app/run.sh"]

FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir pillow exifread tqdm

# Копируем файлы
COPY sync.py run.sh ./

RUN chmod +x /app/run.sh

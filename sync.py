import os
import hashlib
import shutil
import exifread
import json
import time
from datetime import datetime
from tqdm import tqdm
import logging
import sys

# === Константы ===
SORTED_DIR = "/sorted"
DUPLICATES_DIR = "/duplicates"
LOG_DIR = "/logs"
CACHE_FILE = os.path.join(LOG_DIR, "hash_cache.json")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"sync_{datetime.now():%Y%m%d_%H%M%S}.log")

# === Настройка логов ===
logger = logging.getLogger("photo_sync")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S")
fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
ch = logging.StreamHandler(sys.stdout)
fh.setFormatter(fmt)
ch.setFormatter(fmt)
logger.addHandler(fh)
logger.addHandler(ch)

HEARTBEAT_INTERVAL = 60  # сек между сообщениями “ещё жив”


def hash_file(path):
    """Вычисляет MD5-хэш файла"""
    try:
        with open(path, "rb") as f:
            h = hashlib.md5()
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def get_date_taken(path):
    """Пытается извлечь дату съёмки из EXIF"""
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
        date_str = str(tags.get("EXIF DateTimeOriginal"))
        if date_str:
            return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S").strftime("%Y/%m/%d")
    except Exception:
        pass
    return "unknown"


def build_hash_map(base_path):
    """Создаёт карту {hash: relative_path} с кэшем"""
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            logger.warning("⚠️ Повреждён кэш, пересчитываю с нуля.")
            cache = {}

    file_map = {}
    files = [
        os.path.join(root, f)
        for root, _, fs in os.walk(base_path)
        for f in fs
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov"))
    ]

    last_beat = time.time()
    for i, full_path in enumerate(tqdm(files, desc=f"Hashing {base_path}", unit="file")):
        try:
            mtime = os.path.getmtime(full_path)
            key = f"{full_path}:{mtime}"
            if key in cache:
                h = cache[key]
            else:
                h = hash_file(full_path)
                cache[key] = h
            if h:
                file_map[h] = os.path.relpath(full_path, base_path)
        except Exception:
            continue

        # heartbeat каждые 60 с
        if time.time() - last_beat >= HEARTBEAT_INTERVAL:
            pct = (i + 1) / len(files) * 100 if files else 0
            logger.info(f"💓 Hashing progress: {i+1}/{len(files)} ({pct:.2f}%)")
            last_beat = time.time()

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    return file_map


def main():
    logger.info("🔍 Сканирую каталог /sorted (это может занять время)...")
    sorted_map = build_hash_map(SORTED_DIR)
    logger.info(f"✅ Найдено {len(sorted_map)} уникальных файлов в sorted.")

    logger.info("📁 Сканирую каталог /duplicates ...")
    dup_files = [
        os.path.join(root, f)
        for root, _, files in os.walk(DUPLICATES_DIR)
        for f in files
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov"))
    ]
    logger.info(f"🧩 Найдено {len(dup_files)} файлов в duplicates.")

    moved_count = skipped = errors = 0
    last_beat = time.time()

    for i, f in enumerate(tqdm(dup_files, desc="Processing duplicates", unit="file")):
        try:
            h = hash_file(f)
            if not h:
                continue
            if h in sorted_map:
                logger.info(f"[SKIPPED] {f} (duplicate)")
                skipped += 1
                continue

            date_path = get_date_taken(f)
            dest_dir = os.path.join(SORTED_DIR, date_path)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, os.path.basename(f))

            shutil.move(f, dest_path)
            logger.info(f"[MOVED] {f} -> {dest_path}")
            moved_count += 1

        except Exception as e:
            logger.error(f"[ERROR] {f}: {e}")
            errors += 1

        # heartbeat каждые 60 с
        if time.time() - last_beat >= HEARTBEAT_INTERVAL:
            pct = (i + 1) / len(dup_files) * 100 if dup_files else 0
            logger.info(f"💓 Still running... processed {i+1}/{len(dup_files)} ({pct:.2f}%)")
            last_beat = time.time()

    logger.info("✅ Синхронизация завершена.")
    logger.info(f"📦 Перемещено: {moved_count}, 🧩 Пропущено: {skipped}, ⚠️ Ошибок: {errors}")
    logger.info(f"📄 Лог сохранён: {LOG_FILE}")


if __name__ == "__main__":
    main()

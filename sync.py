#!/usr/bin/env python3
import os
import hashlib
import json
import time
import shutil
import sys
from datetime import datetime

# ---------- Конфигурация ----------
HASH_FILE = "/app/hash_cache.json"
LOG_FILE = "/sorted/sync.log"

ALGO = os.getenv("HASH_ALGO", "md5")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
MODE = os.getenv("MODE", "move").lower()        # "move" или "copy"
STRUCTURE = os.getenv("STRUCTURE", "true").lower() == "true"  # true → /YYYY/MM/
IGNORE_DIRS = [x.strip() for x in os.getenv("IGNORE_DIRS", "@eaDir,tmp,cache").split(",")]
PROGRESS_INTERVAL = int(os.getenv("PROGRESS_INTERVAL", "10000"))

SRC = "/duplicates"
DST = "/sorted"

# ---------- Цвета ----------
class C:
    RESET = "\033[0m"
    GRAY = "\033[90m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"

# ---------- Логирование ----------
def log(message, color=None):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {message}"
    if color:
        print(color + line + C.RESET)
    else:
        print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ---------- Хэширование ----------
def file_hash(path):
    h = hashlib.new(ALGO)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def load_cache():
    if os.path.exists(HASH_FILE):
        try:
            with open(HASH_FILE, "r") as f:
                return json.load(f)
        except:
            log("[WARN] Corrupted hash cache, rebuilding...", C.YELLOW)
    return {}

def save_cache(cache):
    with open(HASH_FILE, "w") as f:
        json.dump(cache, f)

# ---------- Индексация ----------
def collect_hashes(base):
    cache = load_cache()
    hashes = {}
    total = 0
    start = time.time()

    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not any(ign.lower() in d.lower() for ign in IGNORE_DIRS)]
        for file in files:
            path = os.path.join(root, file)
            if not os.path.isfile(path):
                continue
            try:
                h = cache.get(path)
                if not h:
                    h = file_hash(path)
                    cache[path] = h
                hashes[h] = path
            except Exception as e:
                log(f"[WARN] Failed: {path} ({e})", C.YELLOW)

            total += 1
            if total % PROGRESS_INTERVAL == 0:
                elapsed = time.time() - start
                rate = total / elapsed
                log(f"[INFO] {total} scanned ({rate:.1f} f/s)", C.GRAY)

    save_cache(cache)
    log(f"[DONE] Indexed {total} files from {base}", C.BLUE)
    return hashes

# ---------- Структура пути ----------
def make_structured_path(base, src_path):
    """Возвращает путь назначения /sorted/YYYY/MM/filename"""
    mtime = os.path.getmtime(src_path)
    dt = datetime.fromtimestamp(mtime)
    subdir = f"{dt.year}/{dt.month:02d}"
    return os.path.join(base, subdir, os.path.basename(src_path))

# ---------- Основной процесс ----------
def main():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log("🔄 Starting photo sync...", C.BLUE)
    t0 = time.time()

    dst_hashes = collect_hashes(DST)
    src_hashes = collect_hashes(SRC)

    new_files = [path for h, path in src_hashes.items() if h not in dst_hashes]
    log(f"🆕 Found {len(new_files)} new files to sync.", C.GREEN)

    for path in new_files:
        if STRUCTURE:
            dest = make_structured_path(DST, path)
        else:
            rel = os.path.relpath(path, SRC)
            dest = os.path.join(DST, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        if DRY_RUN:
            log(f"[DRY_RUN] Would {MODE}: {path} -> {dest}", C.YELLOW)
        else:
            try:
                if MODE == "move":
                    shutil.move(path, dest)
                else:
                    shutil.copy2(path, dest)
                log(f"[OK] {MODE.upper()}: {path} -> {dest}", C.GREEN)
            except Exception as e:
                log(f"[ERROR] Failed to {MODE} {path}: {e}", C.RED)

    elapsed = time.time() - t0
    log(f"✅ Sync completed in {elapsed/60:.1f} minutes", C.BLUE)

if __name__ == "__main__":
    main()

import os
import hashlib
import json
import time
import shutil
import sys

HASH_FILE = "/app/hash_cache.json"
LOG_FILE = "/sorted/sync.log"

ALGO = os.getenv("HASH_ALGO", "md5")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
IGNORE_DIRS = [x.strip() for x in os.getenv("IGNORE_DIRS", "@eaDir,tmp,cache").split(",")]
PROGRESS_INTERVAL = int(os.getenv("PROGRESS_INTERVAL", "10000"))

SRC = "/duplicates"
DST = "/sorted"

# ---------- Logging ----------
def log(message):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {message}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ---------- Hashing ----------
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
            log("[WARN] Corrupted hash cache, rebuilding...")
    return {}

def save_cache(cache):
    with open(HASH_FILE, "w") as f:
        json.dump(cache, f)

# ---------- Main Process ----------
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
                log(f"[WARN] Failed: {path} ({e})")

            total += 1
            if total % PROGRESS_INTERVAL == 0:
                elapsed = time.time() - start
                rate = total / elapsed
                eta = (350000 - total) / rate if rate > 0 else 0
                log(f"[INFO] {total} scanned | {rate:.1f} f/s | ETA ~ {eta/60:.1f} min")

    save_cache(cache)
    log(f"[DONE] Indexed {total} files from {base}")
    return hashes

def main():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log("🔄 Starting photo sync...")
    t0 = time.time()

    dst_hashes = collect_hashes(DST)
    src_hashes = collect_hashes(SRC)

    new_files = [path for h, path in src_hashes.items() if h not in dst_hashes]
    log(f"🆕 Found {len(new_files)} new files to sync.")

    for path in new_files:
        rel = os.path.relpath(path, SRC)
        dest = os.path.join(DST, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        if DRY_RUN:
            log(f"[DRY_RUN] Would move: {path} -> {dest}")
        else:
            shutil.move(path, dest)
            log(f"[OK] Moved: {path} -> {dest}")

    elapsed = time.time() - t0
    log(f"✅ Sync completed in {elapsed/60:.1f} minutes")

if __name__ == "__main__":
    main()

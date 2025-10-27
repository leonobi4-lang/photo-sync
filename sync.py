import os
import hashlib
import shutil
from tqdm import tqdm

DUPLICATES_DIR = "/duplicates"
SORTED_DIR = "/sorted"
LOG_FILE = "/sorted/sync.log"

def hash_file(path):
    """Вычисляет MD5-хэш файла"""
    try:
        with open(path, "rb") as f:
            h = hashlib.md5()
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return None

def build_hash_map(base_path):
    """Создаёт карту {hash: relative_path} для всех файлов"""
    file_map = {}
    for root, _, files in os.walk(base_path):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, base_path)
            h = hash_file(full_path)
            if h:
                file_map[h] = rel_path
    return file_map

def main():
    print("🔍 Scanning sorted directory...")
    sorted_map = build_hash_map(SORTED_DIR)
    print(f"✅ Found {len(sorted_map)} unique files in sorted folder.")

    print("📁 Scanning duplicates directory...")
    dup_files = []
    for root, _, files in os.walk(DUPLICATES_DIR):
        for f in files:
            dup_files.append(os.path.join(root, f))

    print(f"🧩 Found {len(dup_files)} files in duplicates folder.")
    moved_count = 0

    with open(LOG_FILE, "w", encoding="utf-8") as log:
        for f in tqdm(dup_files, desc="Processing", unit="file"):
            h = hash_file(f)
            if not h:
                continue
            if h not in sorted_map:
                rel_path = os.path.relpath(f, DUPLICATES_DIR)
                dest_path = os.path.join(SORTED_DIR, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.move(f, dest_path)
                log.write(f"[MOVED] {f} -> {dest_path}\n")
                moved_count += 1
            else:
                log.write(f"[SKIPPED] {f} (duplicate)\n")

    print(f"✅ Sync complete. Moved {moved_count} new files.")
    print(f"📄 Log saved to: {LOG_FILE}")

if __name__ == "__main__":
    main()

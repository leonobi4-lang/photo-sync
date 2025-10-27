import os
import hashlib
import shutil
import exifread
from datetime import datetime
from tqdm import tqdm
import argparse

SORTED_DIR = "/sorted"
DUPLICATES_DIR = "/duplicates"
LOG_DIR = "/logs"
LOG_FILE = os.path.join(LOG_DIR, f"sync_{datetime.now():%Y%m%d_%H%M%S}.log")

os.makedirs(LOG_DIR, exist_ok=True)


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
    """Извлекает дату съёмки из EXIF (если есть)"""
    try:
        with open(path, 'rb') as f:
            tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
        date_str = str(tags.get("EXIF DateTimeOriginal"))
        if date_str:
            return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S").strftime("%Y/%m/%d")
    except Exception:
        pass
    return "unknown"


def build_hash_map(base_path):
    """Создаёт карту {hash: relative_path}"""
    file_map = {}
    for root, _, files in os.walk(base_path):
        for f in files:
            full_path = os.path.join(root, f)
            h = hash_file(full_path)
            if h:
                file_map[h] = os.path.relpath(full_path, base_path)
    return file_map


def main(dry_run=False):
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
    skipped = 0
    errors = 0

    with open(LOG_FILE, "w", encoding="utf-8") as log:
        for f in tqdm(dup_files, desc="Processing", unit="file"):
            try:
                h = hash_file(f)
                if not h:
                    continue

                if h in sorted_map:
                    log.write(f"[SKIPPED] {f} (duplicate)\n")
                    skipped += 1
                    continue

                date_path = get_date_taken(f)
                dest_dir = os.path.join(SORTED_DIR, date_path)
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, os.path.basename(f))

                if dry_run:
                    log.write(f"[DRY-RUN] Would move {f} -> {dest_path}\n")
                else:
                    shutil.move(f, dest_path)
                    log.write(f"[MOVED] {f} -> {dest_path}\n")
                    moved_count += 1

            except Exception as e:
                log.write(f"[ERROR] {f}: {e}\n")
                errors += 1

    print("✅ Sync complete.")
    print(f"📦 Moved: {moved_count}, 🧩 Skipped: {skipped}, ⚠️ Errors: {errors}")
    print(f"📄 Log saved to: {LOG_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Photo synchronization tool")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sync without moving files")
    args = parser.parse_args()

    main(dry_run=args.dry_run)

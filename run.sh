#!/bin/bash
echo "🚀 Starting photo sync at $(date '+%Y-%m-%d %H:%M:%S')"
python3 /app/sync.py "$@"
echo "✅ Photo sync finished at $(date '+%Y-%m-%d %H:%M:%S')"

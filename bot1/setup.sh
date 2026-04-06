#!/usr/bin/env bash
# setup.sh — Jalankan SEKALI untuk setup awal bot agen otonom
# Usage: bash setup.sh

set -e

echo "=== Setup Bot Agen Otonom ==="
echo "Direktori: $(pwd)"

# 1. Pastikan kita di folder bot1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
echo "[1/5] Bekerja di: $SCRIPT_DIR"

# 2. Aktifkan venv (asumsi sudah ada dari instalasi smolagents)
if [ -d "env" ]; then
    source env/bin/activate
    echo "[2/5] venv aktif: env/"
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
    echo "[2/5] venv aktif: ../venv"
else
    echo "[2/5] Membuat venv baru..."
    python3 -m venv env
    source env/bin/activate
fi

# 3. Upgrade pip dan install dependensi dasar
echo "[3/5] Install dependensi dasar..."
pip install -q --upgrade pip
pip install -q \
    smolagents \
    huggingface_hub \
    duckduckgo_search \
    requests \
    beautifulsoup4 \
    "pymupdf>=1.24" \
    gitpython \
    rich \
    python-dotenv \
    litellm

# 4. Buat folder workspace
mkdir -p workspace
echo "[4/5] Folder workspace/ siap."

# 5. Buat .env jika belum ada
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[5/5] File .env dibuat dari template."
    echo ""
    echo "⚠  PENTING: Buka dan isi file .env sebelum menjalankan bot!"
    echo "   nano .env"
else
    echo "[5/5] .env sudah ada."
fi

echo ""
echo "✅ Setup selesai!"
echo ""
echo "Langkah berikutnya:"
echo "  1. nano .env          → isi OPENROUTER_KEY atau HF_TOKEN"
echo "  2. python bot1.py     → jalankan bot interaktif"
echo "  3. python bot1.py --task 'cari berita AI hari ini dan simpan ke workspace/'"
echo "  4. python bot1.py --daemon  → jalankan semua task di tasks.json"
echo ""
echo "Untuk backup OneDrive (opsional):"
echo "  rclone config         → pilih Microsoft OneDrive, nama remote: onedrive"


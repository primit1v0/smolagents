"""
telegram_bot.py — Remote control via Telegram
Jalankan BERSAMAAN dengan bot1.py (terminal berbeda):
  Terminal 1: python bot1.py
  Terminal 2: python telegram_bot.py

Atau jalankan sendiri (agen dibuat di sini juga):
  python telegram_bot.py
"""

import os
import sys
import json
import asyncio
import datetime
import subprocess
import importlib
from pathlib import Path

# ─── Path sama dengan bot1.py ────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent.resolve()
WORKSPACE = BASE_DIR / "workspace"
LOG_FILE  = BASE_DIR / "agent_log.json"
ENV_FILE  = BASE_DIR / ".env"
WORKSPACE.mkdir(exist_ok=True)

# ─── Muat .env ───────────────────────────────────────────────────────────────
def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

load_env()

# ─── Auto-install python-telegram-bot ────────────────────────────────────────
try:
    import telegram
except ImportError:
    print("[install] python-telegram-bot ...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "python-telegram-bot==20.7"], check=True)

try:
    from smolagents import CodeAgent, DuckDuckGoSearchTool, tool
    from smolagents import InferenceClientModel, LiteLLMModel
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "smolagents"])
    from smolagents import CodeAgent, DuckDuckGoSearchTool, tool
    from smolagents import InferenceClientModel, LiteLLMModel

from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from telegram.constants import ParseMode

# ─── Konfigurasi ─────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
ALLOWED_USER_IDS = os.environ.get("TELEGRAM_ALLOWED_IDS", "")  # "123456,789012"

# Parse allowed IDs
ALLOWED = set()
if ALLOWED_USER_IDS:
    for uid in ALLOWED_USER_IDS.split(","):
        uid = uid.strip()
        if uid.isdigit():
            ALLOWED.add(int(uid))

# ─── Logger ──────────────────────────────────────────────────────────────────
def log(event: str, detail: str = ""):
    entry = {
        "time": datetime.datetime.now().isoformat(),
        "event": f"telegram:{event}",
        "detail": detail,
    }
    logs = []
    if LOG_FILE.exists():
        try:
            logs = json.loads(LOG_FILE.read_text())
        except Exception:
            logs = []
    logs.append(entry)
    LOG_FILE.write_text(json.dumps(logs[-500:], indent=2, ensure_ascii=False))

# ─── Tools (sama dengan bot1.py) ─────────────────────────────────────────────
@tool
def install_package(package_name: str) -> str:
    """Install paket Python baru ke dalam venv aktif.
    Args:
        package_name: Nama paket PyPI, contoh 'pandas'.
    Returns:
        Pesan sukses atau error.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", package_name],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            log("install_package", package_name)
            return f"✅ {package_name} berhasil diinstall."
        return f"❌ Gagal: {result.stderr[:200]}"
    except Exception as e:
        return f"❌ Error: {e}"

@tool
def run_shell(command: str) -> str:
    """Jalankan perintah shell di dalam workspace.
    Args:
        command: Perintah bash.
    Returns:
        Output stdout/stderr.
    """
    forbidden = ["..", "/root", "/etc", "/usr", "/bin", "sudo", "rm -rf /"]
    for f in forbidden:
        if f in command:
            return f"⛔ Diblokir: mengandung '{f}'"
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=60, cwd=str(WORKSPACE)
        )
        output = (result.stdout + result.stderr).strip()
        log("run_shell", command[:80])
        return output[:2000] if output else "(tidak ada output)"
    except subprocess.TimeoutExpired:
        return "⏰ Timeout 60 detik."
    except Exception as e:
        return f"❌ Error: {e}"

@tool
def write_file(filename: str, content: str) -> str:
    """Tulis teks ke file di workspace.
    Args:
        filename: Nama file.
        content: Isi file.
    Returns:
        Path file.
    """
    target = WORKSPACE / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    log("write_file", filename)
    return f"✅ Disimpan: {target}"

@tool
def read_file(filename: str) -> str:
    """Baca isi file dari workspace.
    Args:
        filename: Nama file.
    Returns:
        Isi file.
    """
    target = WORKSPACE / filename
    if not target.exists():
        return f"❌ Tidak ditemukan: {filename}"
    return target.read_text(encoding="utf-8")[:4000]

@tool
def browse_web(url: str) -> str:
    """Ambil teks dari halaman web.
    Args:
        url: URL lengkap.
    Returns:
        Teks halaman.
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        teks = soup.get_text(separator="\n", strip=True)
        log("browse_web", url[:60])
        return teks[:4000]
    except Exception as e:
        return f"❌ Gagal: {e}"

@tool
def read_pdf(path_or_url: str, max_pages: int = 8) -> str:
    """Baca teks dari file PDF lokal atau URL.
    Args:
        path_or_url: Path lokal atau URL PDF.
        max_pages: Maksimum halaman.
    Returns:
        Teks PDF.
    """
    try:
        import fitz
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pymupdf"])
        import fitz
    if path_or_url.startswith("http"):
        import requests, tempfile
        r = requests.get(path_or_url, timeout=30)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(r.content); tmp.close()
        path_or_url = tmp.name
    doc = fitz.open(path_or_url)
    teks = [f"--- Hal {i+1} ---\n{p.get_text()}"
            for i, p in enumerate(doc) if i < max_pages]
    doc.close()
    return "\n".join(teks)[:6000]

# ─── Model LLM dengan fallback ───────────────────────────────────────────────
def get_model():
    groq_key = os.environ.get("GROQ_API_KEY", "")
    or_key   = os.environ.get("OPENROUTER_KEY", "")
    hf_token = os.environ.get("HF_TOKEN", "")

    providers = []
    if groq_key:
        providers.append(("Groq llama-3.3-70b", lambda: LiteLLMModel(
            model_id="groq/llama-3.3-70b-versatile", api_key=groq_key)))
    if or_key:
        providers.append(("OpenRouter llama-3.3-70b", lambda: LiteLLMModel(
            model_id="openrouter/meta-llama/llama-3.3-70b-instruct:free",
            api_key=or_key, api_base="https://openrouter.ai/api/v1")))
    if hf_token:
        providers.append(("HuggingFace Qwen2.5-72B", lambda: InferenceClientModel(
            model_id="Qwen/Qwen2.5-72B-Instruct", token=hf_token)))

    for name, factory in providers:
        try:
            m = factory()
            print(f"✅ Model aktif: {name}")
            return m
        except Exception as e:
            print(f"⚠ {name} gagal: {e}")
    raise RuntimeError("Semua provider LLM gagal. Cek .env")

# ─── Buat agen ───────────────────────────────────────────────────────────────
def create_agent():
    return CodeAgent(
        tools=[
            DuckDuckGoSearchTool(),
            install_package,
            run_shell,
            write_file,
            read_file,
            browse_web,
            read_pdf,
        ],
        model=get_model(),
        max_steps=20,
        verbosity_level=0,
        additional_authorized_imports=[
            "os", "sys", "pathlib", "json", "datetime",
            "requests", "bs4", "fitz", "subprocess",
            "re", "math", "statistics", "csv", "io",
            "urllib", "hashlib", "base64", "shutil", "glob",
        ],
    )

# ─── Guard: cek apakah user diizinkan ────────────────────────────────────────
def is_allowed(user_id: int) -> bool:
    if not ALLOWED:
        return True  # kalau belum diset, izinkan semua (setup awal)
    return user_id in ALLOWED

# ─── Handler Telegram ─────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        await update.message.reply_text("⛔ Akses ditolak.")
        return
    await update.message.reply_text(
        "🤖 *Bot Agen Otonom aktif!*\n\n"
        "Kirim perintah apapun dan agen akan mengerjakannya.\n\n"
        "*Perintah cepat:*\n"
        "/status — cek status agen\n"
        "/files — lihat file di workspace\n"
        "/log — lihat 5 aktivitas terakhir\n"
        "/bersihkan — hapus semua file workspace\n\n"
        "Contoh:\n"
        "• _cari berita AI terbaru dan simpan ke berita.md_\n"
        "• _baca file laporan.md_\n"
        "• _buat script python hitung fibonacci_",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    files = list(WORKSPACE.rglob("*"))
    file_count = sum(1 for f in files if f.is_file())
    size = sum(f.stat().st_size for f in files if f.is_file())
    await update.message.reply_text(
        f"📊 *Status Agen*\n\n"
        f"📁 Workspace: `{WORKSPACE}`\n"
        f"📄 Jumlah file: {file_count}\n"
        f"💾 Total ukuran: {size // 1024} KB\n"
        f"⏰ Waktu: {datetime.datetime.now().strftime('%H:%M:%S')}",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_files(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    files = [f for f in WORKSPACE.rglob("*") if f.is_file()]
    if not files:
        await update.message.reply_text("📂 Workspace kosong.")
        return
    daftar = "\n".join(
        f"• `{f.relative_to(WORKSPACE)}` ({f.stat().st_size // 1024} KB)"
        for f in sorted(files)[:20]
    )
    await update.message.reply_text(
        f"📂 *File di workspace:*\n\n{daftar}",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_log(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    if not LOG_FILE.exists():
        await update.message.reply_text("📋 Belum ada log.")
        return
    logs = json.loads(LOG_FILE.read_text())
    entri = logs[-5:]
    teks = "\n".join(
        f"• `{e['time'][11:19]}` {e['event']}: {e['detail'][:50]}"
        for e in entri
    )
    await update.message.reply_text(
        f"📋 *5 Aktivitas Terakhir:*\n\n{teks}",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_bersihkan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    import shutil
    count = 0
    for f in WORKSPACE.glob("*"):
        if f.is_file():
            f.unlink()
            count += 1
        elif f.is_dir() and f.name != "git_backup":
            shutil.rmtree(f)
            count += 1
    log("bersihkan", f"{count} item dihapus")
    await update.message.reply_text(f"🗑 Workspace dibersihkan ({count} item dihapus).")

async def cmd_myid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Bantu user temukan Telegram ID mereka"""
    uid = update.effective_user.id
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👤 Halo {name}!\n"
        f"Telegram ID kamu: `{uid}`\n\n"
        f"Tambahkan ID ini ke `.env`:\n"
        f"`TELEGRAM_ALLOWED_IDS={uid}`",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_pesan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handler utama: teruskan pesan ke agen AI"""
    uid = update.effective_user.id
    if not is_allowed(uid):
        await update.message.reply_text("⛔ Akses ditolak. Kirim /myid untuk cek ID kamu.")
        return

    teks = update.message.text.strip()
    if not teks:
        return

    # Kirim pesan "sedang diproses"
    thinking = await update.message.reply_text("🤔 Agen sedang mengerjakan...")
    log("pesan_masuk", teks[:80])

    try:
        # Jalankan agen di thread terpisah agar tidak blokir event loop
        loop = asyncio.get_event_loop()
        agent = ctx.bot_data.get("agent")
        if not agent:
            ctx.bot_data["agent"] = create_agent()
            agent = ctx.bot_data["agent"]

        result = await loop.run_in_executor(None, agent.run, teks)
        hasil = str(result).strip()

        # Telegram max 4096 karakter per pesan
        if len(hasil) > 4000:
            # Kirim sebagai file kalau terlalu panjang
            tmp = WORKSPACE / "_telegram_hasil.txt"
            tmp.write_text(hasil, encoding="utf-8")
            await thinking.delete()
            await update.message.reply_document(
                document=open(tmp, "rb"),
                filename="hasil.txt",
                caption="✅ Selesai! Hasil terlalu panjang, dikirim sebagai file."
            )
        else:
            await thinking.edit_text(
                f"✅ *Selesai!*\n\n{hasil}",
                parse_mode=ParseMode.MARKDOWN
            )
        log("selesai", teks[:60])

    except Exception as e:
        await thinking.edit_text(f"❌ Error: {str(e)[:500]}")
        log("error", str(e)[:100])

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN belum diisi di .env")
        print("")
        print("Cara membuat bot Telegram:")
        print("1. Buka Telegram, cari @BotFather")
        print("2. Kirim: /newbot")
        print("3. Ikuti instruksi, dapatkan token")
        print("4. Isi di .env: TELEGRAM_TOKEN=123456:ABCdef...")
        print("")
        print("Cara cari Telegram ID kamu:")
        print("1. Jalankan bot dulu tanpa TELEGRAM_ALLOWED_IDS")
        print("2. Kirim /myid ke bot kamu")
        print("3. Salin ID ke .env: TELEGRAM_ALLOWED_IDS=123456789")
        sys.exit(1)

    if not ALLOWED:
        print("⚠  TELEGRAM_ALLOWED_IDS belum diset!")
        print("   Bot terbuka untuk siapa saja sementara ini.")
        print("   Kirim /myid ke bot untuk dapat ID kamu, lalu isi .env")

    print(f"🤖 Bot Telegram aktif...")
    print(f"   Token: {TELEGRAM_TOKEN[:10]}...")
    print(f"   Allowed IDs: {ALLOWED if ALLOWED else 'semua (belum dibatasi)'}")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Daftarkan commands
    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("status",     cmd_status))
    app.add_handler(CommandHandler("files",      cmd_files))
    app.add_handler(CommandHandler("log",        cmd_log))
    app.add_handler(CommandHandler("bersihkan",  cmd_bersihkan))
    app.add_handler(CommandHandler("myid",       cmd_myid))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pesan))

    # Set daftar command di menu Telegram
    async def post_init(application):
        await application.bot.set_my_commands([
            BotCommand("start",     "Mulai bot"),
            BotCommand("status",    "Status agen & workspace"),
            BotCommand("files",     "Daftar file di workspace"),
            BotCommand("log",       "5 aktivitas terakhir"),
            BotCommand("bersihkan", "Hapus semua file workspace"),
            BotCommand("myid",      "Lihat Telegram ID kamu"),
        ])

    app.post_init = post_init
    print("✅ Siap menerima perintah dari Telegram!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
  

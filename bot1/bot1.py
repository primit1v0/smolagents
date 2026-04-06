"""
Bot Agen Otonom - bot1.py
Jalankan: python bot1.py
Atau mode daemon: python bot1.py --daemon
"""

import os
import sys
import json
import subprocess
import importlib
import datetime
import argparse
from pathlib import Path

# ─── Lokasi aman: semua file di dalam ~/bot1 ─────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
WORKSPACE = BASE_DIR / "workspace"
LOG_FILE  = BASE_DIR / "agent_log.json"
ENV_FILE  = BASE_DIR / ".env"

WORKSPACE.mkdir(exist_ok=True)
os.chdir(BASE_DIR)

# ─── Muat variabel lingkungan dari .env ──────────────────────────────────────
def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

load_env()

# ─── Auto-install package yang belum ada ─────────────────────────────────────
REQUIRED = [
    "smolagents",
    "huggingface_hub",
    "duckduckgo_search",
    "requests",
    "beautifulsoup4",
    "pypdf2",
    "pymupdf",          # fitz - baca PDF lebih lengkap
    "rclone-python",
    "gitpython",
    "rich",
    "python-dotenv",
]

def ensure_packages(packages: list[str]):
    for pkg in packages:
        import_name = pkg.split("[")[0].replace("-", "_").replace("rclone_python", "rclone")
        try:
            importlib.import_module(import_name)
        except ImportError:
            print(f"[install] {pkg} ...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", pkg],
                check=True
            )

ensure_packages(REQUIRED)

# ─── Import setelah pastikan terinstall ──────────────────────────────────────
from smolagents import CodeAgent, DuckDuckGoSearchTool, tool
from smolagents import HfApiModel
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

# ─── Logger sederhana ────────────────────────────────────────────────────────
def log(event: str, detail: str = ""):
    entry = {
        "time": datetime.datetime.now().isoformat(),
        "event": event,
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

# ─── Tool: install package baru saat runtime ─────────────────────────────────
@tool
def install_package(package_name: str) -> str:
    """
    Install paket Python baru ke dalam venv aktif.
    Args:
        package_name: Nama paket PyPI, contoh 'pandas' atau 'pillow'.
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
        return f"❌ Gagal install {package_name}: {result.stderr[:300]}"
    except Exception as e:
        return f"❌ Error: {e}"

# ─── Tool: jalankan shell command (dibatasi di workspace) ────────────────────
@tool
def run_shell(command: str) -> str:
    """
    Jalankan perintah shell. Hanya boleh beroperasi di dalam ~/bot1/workspace.
    Args:
        command: Perintah bash, contoh 'ls workspace' atau 'cat workspace/hasil.txt'.
    Returns:
        Output stdout/stderr.
    """
    # Blokir akses keluar dari BASE_DIR
    forbidden = ["..", "/root", "/etc", "/usr", "/bin", "sudo", "rm -rf /"]
    for f in forbidden:
        if f in command:
            return f"⛔ Perintah diblokir demi keamanan: mengandung '{f}'"
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=60, cwd=str(WORKSPACE)
        )
        output = (result.stdout + result.stderr).strip()
        log("run_shell", command[:80])
        return output[:2000] if output else "(tidak ada output)"
    except subprocess.TimeoutExpired:
        return "⏰ Timeout setelah 60 detik."
    except Exception as e:
        return f"❌ Error: {e}"

# ─── Tool: tulis file ke workspace ──────────────────────────────────────────
@tool
def write_file(filename: str, content: str) -> str:
    """
    Tulis teks ke dalam file di workspace agen.
    Args:
        filename: Nama file, contoh 'laporan.md' atau 'data/output.json'.
        content: Isi file yang ingin ditulis.
    Returns:
        Path file yang ditulis.
    """
    target = WORKSPACE / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    log("write_file", str(target))
    return f"✅ File disimpan: {target}"

# ─── Tool: baca file dari workspace ─────────────────────────────────────────
@tool
def read_file(filename: str) -> str:
    """
    Baca isi file dari workspace agen.
    Args:
        filename: Nama file, contoh 'laporan.md'.
    Returns:
        Isi file sebagai teks.
    """
    target = WORKSPACE / filename
    if not target.exists():
        return f"❌ File tidak ditemukan: {filename}"
    return target.read_text(encoding="utf-8")[:5000]

# ─── Tool: baca dan ringkas PDF ──────────────────────────────────────────────
@tool
def read_pdf(path_or_url: str, max_pages: int = 10) -> str:
    """
    Baca teks dari file PDF (path lokal atau URL) dan kembalikan isinya.
    Args:
        path_or_url: Path lokal atau URL ke file PDF.
        max_pages: Maksimum halaman yang dibaca (default 10).
    Returns:
        Teks isi PDF.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pymupdf"])
        import fitz

    # Download jika URL
    if path_or_url.startswith("http"):
        import requests, tempfile
        r = requests.get(path_or_url, timeout=30)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(r.content)
        tmp.close()
        path_or_url = tmp.name

    doc = fitz.open(path_or_url)
    teks = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        teks.append(f"--- Halaman {i+1} ---\n{page.get_text()}")
    doc.close()
    result = "\n".join(teks)[:8000]
    log("read_pdf", path_or_url[:80])
    return result

# ─── Tool: browsing web ──────────────────────────────────────────────────────
@tool
def browse_web(url: str) -> str:
    """
    Ambil teks dari halaman web.
    Args:
        url: URL lengkap, contoh 'https://example.com'.
    Returns:
        Teks halaman web (bersih dari HTML).
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        teks = soup.get_text(separator="\n", strip=True)
        log("browse_web", url)
        return teks[:5000]
    except Exception as e:
        return f"❌ Gagal browse {url}: {e}"

# ─── Tool: backup ke GitHub ──────────────────────────────────────────────────
@tool
def backup_to_github(commit_message: str = "auto backup") -> str:
    """
    Commit dan push semua file workspace ke GitHub.
    Butuh GITHUB_REPO di .env sudah dikonfigurasi.
    Args:
        commit_message: Pesan commit.
    Returns:
        Status push.
    """
    repo_url = os.environ.get("GITHUB_REPO", "")
    if not repo_url:
        return "❌ GITHUB_REPO belum diset di file .env"
    try:
        import git
        repo_path = WORKSPACE / "git_backup"
        if not (repo_path / ".git").exists():
            repo_path.mkdir(exist_ok=True)
            repo = git.Repo.init(repo_path)
            repo.create_remote("origin", repo_url)
        else:
            repo = git.Repo(repo_path)
        # Salin file workspace ke git_backup
        import shutil
        for f in WORKSPACE.glob("*"):
            if f.name != "git_backup" and f.is_file():
                shutil.copy2(f, repo_path / f.name)
        repo.git.add("--all")
        repo.index.commit(commit_message)
        repo.remotes.origin.push()
        log("backup_github", commit_message)
        return f"✅ Backup ke GitHub berhasil: {commit_message}"
    except Exception as e:
        return f"❌ Gagal backup GitHub: {e}"

# ─── Tool: sync ke OneDrive via rclone ──────────────────────────────────────
@tool
def sync_to_onedrive(remote_path: str = "bot1_backup") -> str:
    """
    Sinkronisasi workspace ke OneDrive menggunakan rclone.
    Butuh rclone sudah dikonfigurasi dengan remote bernama 'onedrive'.
    Args:
        remote_path: Folder tujuan di OneDrive.
    Returns:
        Status sinkronisasi.
    """
    try:
        result = subprocess.run(
            ["rclone", "sync", str(WORKSPACE), f"onedrive:{remote_path}",
             "--progress", "--log-level", "ERROR"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            log("sync_onedrive", remote_path)
            return f"✅ Sinkronisasi ke OneDrive/{remote_path} berhasil."
        return f"❌ rclone error: {result.stderr[:300]}"
    except FileNotFoundError:
        return "❌ rclone tidak ditemukan. Install dengan: pkg install rclone"
    except Exception as e:
        return f"❌ Error: {e}"

# ─── Pilih model LLM ─────────────────────────────────────────────────────────
def get_model():
    """
    Prioritas: OpenRouter > HuggingFace API > lokal jika ada.
    Set HF_TOKEN atau OPENROUTER_KEY di .env
    """
    hf_token  = os.environ.get("HF_TOKEN", "")
    or_key    = os.environ.get("OPENROUTER_KEY", "")

    if or_key:
        # Pakai OpenRouter (akses GPT-4o, Claude, Gemini, dll gratis/murah)
        from smolagents import LiteLLMModel
        return LiteLLMModel(
            model_id="openrouter/meta-llama/llama-3.3-70b-instruct:free",
            api_key=or_key,
            api_base="https://openrouter.ai/api/v1",
        )
    elif hf_token:
        return HfApiModel(
            model_id="Qwen/Qwen2.5-72B-Instruct",
            token=hf_token,
        )
    else:
        console.print("[yellow]⚠ Tidak ada API key. Set HF_TOKEN atau OPENROUTER_KEY di .env[/]")
        console.print("[dim]Mendaftarlah gratis di: https://openrouter.ai atau https://huggingface.co[/]")
        sys.exit(1)

# ─── Buat agen ───────────────────────────────────────────────────────────────
def create_agent():
    model = get_model()
    agent = CodeAgent(
        tools=[
            DuckDuckGoSearchTool(),
            install_package,
            run_shell,
            write_file,
            read_file,
            read_pdf,
            browse_web,
            backup_to_github,
            sync_to_onedrive,
        ],
        model=model,
        max_steps=20,
        verbosity_level=1,
        additional_authorized_imports=[
            "os", "sys", "pathlib", "json", "datetime",
            "requests", "bs4", "fitz", "git", "subprocess",
            "re", "math", "statistics", "csv", "io",
            "urllib", "hashlib", "base64", "shutil", "glob",
        ],
    )
    return agent

# ─── Main loop ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Bot Agen Otonom")
    parser.add_argument("--daemon", action="store_true", help="Mode non-interaktif (baca task dari tasks.json)")
    parser.add_argument("--task", type=str, help="Jalankan satu task langsung")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold purple]🤖 Bot Agen Otonom[/]\n"
        f"[dim]Workspace: {WORKSPACE}[/]\n"
        "[dim]Ketik 'exit' untuk keluar, 'log' untuk lihat riwayat[/]",
        border_style="purple"
    ))

    agent = create_agent()

    # Mode: satu task via argumen
    if args.task:
        console.print(f"[cyan]Task:[/] {args.task}")
        result = agent.run(args.task)
        console.print(Panel(str(result), title="Hasil", border_style="green"))
        log("task_done", args.task[:100])
        return

    # Mode daemon: baca dari tasks.json
    if args.daemon:
        tasks_file = BASE_DIR / "tasks.json"
        if not tasks_file.exists():
            console.print("[red]tasks.json tidak ditemukan.[/]")
            return
        tasks = json.loads(tasks_file.read_text())
        for t in tasks:
            if t.get("status") == "pending":
                console.print(f"[cyan]Mengerjakan:[/] {t['task']}")
                try:
                    result = agent.run(t["task"])
                    t["status"] = "done"
                    t["result"] = str(result)[:500]
                    log("daemon_task", t["task"][:80])
                except Exception as e:
                    t["status"] = "error"
                    t["error"] = str(e)
        tasks_file.write_text(json.dumps(tasks, indent=2, ensure_ascii=False))
        console.print("[green]✅ Semua task selesai.[/]")
        return

    # Mode interaktif
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]Anda[/]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Sampai jumpa![/]")
            break

        if user_input.strip().lower() in ("exit", "quit", "keluar"):
            console.print("[dim]Sampai jumpa![/]")
            break

        if user_input.strip().lower() == "log":
            if LOG_FILE.exists():
                logs = json.loads(LOG_FILE.read_text())
                for entry in logs[-10:]:
                    console.print(f"[dim]{entry['time']}[/] {entry['event']}: {entry['detail']}")
            continue

        if not user_input.strip():
            continue

        try:
            console.print("[dim]🤔 Agen sedang berpikir...[/]")
            result = agent.run(user_input)
            console.print(Panel(str(result), title="[green]Agen[/]", border_style="green"))
            log("chat", user_input[:80])
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
            log("error", str(e)[:100])

if __name__ == "__main__":
    main()
    

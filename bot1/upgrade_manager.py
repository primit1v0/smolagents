"""
upgrade_manager.py — Sistem permintaan upgrade agen
Agen mengusulkan, Anda memutuskan.

Cara pakai:
  python upgrade_manager.py          → lihat semua permintaan
  python upgrade_manager.py apply 3  → terapkan permintaan #3
  python upgrade_manager.py reject 3 → tolak permintaan #3
  python upgrade_manager.py clear    → hapus semua yang sudah selesai
"""

import os
import sys
import json
import datetime
import subprocess
from pathlib import Path

BASE_DIR     = Path(__file__).parent.resolve()
REQUEST_FILE = BASE_DIR / "upgrade_requests.json"
ENV_FILE     = BASE_DIR / ".env"
LOG_FILE     = BASE_DIR / "agent_log.json"

# ─── Warna terminal ──────────────────────────────────────────────────────────
R = "\033[91m"; G = "\033[92m"; Y = "\033[93m"
B = "\033[94m"; M = "\033[95m"; C = "\033[96m"
W = "\033[97m"; D = "\033[2m";  X = "\033[0m"

def log(event, detail=""):
    entry = {"time": datetime.datetime.now().isoformat(),
             "event": f"upgrade:{event}", "detail": detail}
    logs = []
    if LOG_FILE.exists():
        try: logs = json.loads(LOG_FILE.read_text())
        except: logs = []
    logs.append(entry)
    LOG_FILE.write_text(json.dumps(logs[-500:], indent=2, ensure_ascii=False))

def load_requests() -> list:
    if not REQUEST_FILE.exists():
        return []
    try:
        return json.loads(REQUEST_FILE.read_text())
    except:
        return []

def save_requests(data: list):
    REQUEST_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def next_id(data: list) -> int:
    if not data:
        return 1
    return max(r.get("id", 0) for r in data) + 1

# ─── Tool yang dipanggil agen ────────────────────────────────────────────────
def ajukan_permintaan(judul: str, jenis: str, deskripsi: str, kode_atau_nilai: str = "") -> str:
    """
    Dipanggil oleh agen untuk mengajukan permintaan upgrade.
    judul            : Judul singkat permintaan
    jenis            : 'tool_baru' | 'env_config' | 'package' | 'script' | 'lainnya'
    deskripsi        : Penjelasan lengkap mengapa dibutuhkan
    kode_atau_nilai  : Kode Python atau nilai konfigurasi yang diusulkan
    """
    data = load_requests()
    entry = {
        "id":             next_id(data),
        "judul":          judul,
        "jenis":          jenis,
        "deskripsi":      deskripsi,
        "kode_atau_nilai": kode_atau_nilai,
        "status":         "pending",
        "waktu_ajukan":   datetime.datetime.now().isoformat(),
        "waktu_selesai":  None,
        "catatan_pemilik": "",
    }
    data.append(entry)
    save_requests(data)
    log("ajukan", f"#{entry['id']} {judul}")
    return (f"✅ Permintaan #{entry['id']} dicatat: '{judul}'\n"
            f"   Menunggu persetujuan pemilik.")

# ─── Tampilan ─────────────────────────────────────────────────────────────────
JENIS_LABEL = {
    "tool_baru":  f"{M}🔧 Tool baru{X}",
    "env_config": f"{C}⚙️  Konfigurasi{X}",
    "package":    f"{B}📦 Package{X}",
    "script":     f"{Y}📝 Script{X}",
    "lainnya":    f"{D}📌 Lainnya{X}",
}

STATUS_LABEL = {
    "pending":  f"{Y}⏳ Menunggu{X}",
    "approved": f"{G}✅ Disetujui{X}",
    "rejected": f"{R}❌ Ditolak{X}",
    "applied":  f"{G}🚀 Diterapkan{X}",
}

def tampilkan_semua():
    data = load_requests()
    if not data:
        print(f"\n{D}Belum ada permintaan upgrade.{X}\n")
        return

    pending   = [r for r in data if r["status"] == "pending"]
    approved  = [r for r in data if r["status"] == "approved"]
    applied   = [r for r in data if r["status"] == "applied"]
    rejected  = [r for r in data if r["status"] == "rejected"]

    print(f"\n{W}{'═'*60}{X}")
    print(f"{W}  📋 DAFTAR PERMINTAAN UPGRADE AGEN{X}")
    print(f"{W}{'═'*60}{X}")
    print(f"  {Y}⏳ Pending: {len(pending)}{X}  "
          f"{G}✅ Disetujui: {len(approved)}{X}  "
          f"{G}🚀 Diterapkan: {len(applied)}{X}  "
          f"{R}❌ Ditolak: {len(rejected)}{X}")
    print(f"{W}{'─'*60}{X}\n")

    # Tampilkan pending dulu
    for r in sorted(data, key=lambda x: (
        {"pending":0,"approved":1,"applied":2,"rejected":3}.get(x["status"],9),
        x["id"]
    )):
        status = STATUS_LABEL.get(r["status"], r["status"])
        jenis  = JENIS_LABEL.get(r["jenis"], r["jenis"])
        waktu  = r["waktu_ajukan"][:16].replace("T", " ")

        print(f"  {W}#{r['id']:03d}{X} {status}  {jenis}")
        print(f"  {W}{r['judul']}{X}")
        print(f"  {D}{waktu}{X}")
        print(f"  {r['deskripsi'][:120]}{'...' if len(r['deskripsi'])>120 else ''}")

        if r.get("kode_atau_nilai"):
            preview = r["kode_atau_nilai"][:200]
            print(f"\n  {D}┌── Kode/Nilai yang diusulkan ──{X}")
            for line in preview.splitlines()[:8]:
                print(f"  {D}│{X} {line}")
            if len(r["kode_atau_nilai"]) > 200:
                print(f"  {D}│ ... (truncated){X}")
            print(f"  {D}└─────────────────────────────{X}")

        if r.get("catatan_pemilik"):
            print(f"  {C}💬 Catatan: {r['catatan_pemilik']}{X}")

        if r["waktu_selesai"]:
            print(f"  {D}Selesai: {r['waktu_selesai'][:16].replace('T',' ')}{X}")

        print(f"  {D}{'─'*56}{X}\n")

    print(f"{W}Perintah:{X}")
    print(f"  {G}python upgrade_manager.py apply <id>{X}   → terapkan")
    print(f"  {R}python upgrade_manager.py reject <id>{X}  → tolak")
    print(f"  {Y}python upgrade_manager.py detail <id>{X}  → lihat detail penuh")
    print(f"  {D}python upgrade_manager.py clear{X}        → hapus selesai\n")

def tampilkan_detail(req_id: int):
    data = load_requests()
    r = next((x for x in data if x["id"] == req_id), None)
    if not r:
        print(f"{R}Permintaan #{req_id} tidak ditemukan.{X}")
        return

    status = STATUS_LABEL.get(r["status"], r["status"])
    jenis  = JENIS_LABEL.get(r["jenis"], r["jenis"])

    print(f"\n{W}{'═'*60}{X}")
    print(f"{W}  DETAIL PERMINTAAN #{r['id']}{X}")
    print(f"{W}{'═'*60}{X}")
    print(f"  Judul   : {W}{r['judul']}{X}")
    print(f"  Jenis   : {jenis}")
    print(f"  Status  : {status}")
    print(f"  Diajukan: {r['waktu_ajukan'][:16].replace('T',' ')}")
    print(f"\n  {W}Deskripsi:{X}")
    for line in r["deskripsi"].splitlines():
        print(f"    {line}")

    if r.get("kode_atau_nilai"):
        print(f"\n  {W}Kode / Nilai yang diusulkan:{X}")
        print(f"  {D}{'─'*56}{X}")
        for line in r["kode_atau_nilai"].splitlines():
            print(f"  {line}")
        print(f"  {D}{'─'*56}{X}")

    if r.get("catatan_pemilik"):
        print(f"\n  {C}Catatan pemilik: {r['catatan_pemilik']}{X}")
    print()

def apply_permintaan(req_id: int):
    data = load_requests()
    r = next((x for x in data if x["id"] == req_id), None)
    if not r:
        print(f"{R}Permintaan #{req_id} tidak ditemukan.{X}")
        return
    if r["status"] in ("applied", "rejected"):
        print(f"{Y}Permintaan #{req_id} sudah {r['status']}.{X}")
        return

    print(f"\n{W}Menerapkan permintaan #{req_id}: {r['judul']}{X}")

    jenis = r["jenis"]

    # ── Package: langsung pip install ──
    if jenis == "package":
        pkg = r["kode_atau_nilai"].strip()
        print(f"  📦 pip install {pkg} ...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  {G}✅ Package '{pkg}' berhasil diinstall.{X}")
            r["status"] = "applied"
        else:
            print(f"  {R}❌ Gagal: {result.stderr[:200]}{X}")
            return

    # ── Env config: tambahkan ke .env ──
    elif jenis == "env_config":
        nilai = r["kode_atau_nilai"].strip()
        print(f"  ⚙️  Menambahkan ke .env: {nilai[:60]}")
        with open(ENV_FILE, "a") as f:
            f.write(f"\n# Ditambahkan upgrade #{req_id} - {datetime.datetime.now():%Y-%m-%d}\n")
            f.write(nilai + "\n")
        print(f"  {G}✅ Konfigurasi ditambahkan ke .env{X}")
        r["status"] = "applied"

    # ── Script: simpan ke workspace ──
    elif jenis == "script":
        nama_file = f"upgrade_{req_id}_{r['judul'][:20].replace(' ','_')}.py"
        target = BASE_DIR / "workspace" / nama_file
        target.write_text(r["kode_atau_nilai"], encoding="utf-8")
        print(f"  {G}✅ Script disimpan: workspace/{nama_file}{X}")
        r["status"] = "applied"

    # ── Tool baru / lainnya: tampilkan kode untuk ditempel manual ──
    elif jenis in ("tool_baru", "lainnya"):
        print(f"\n  {Y}Jenis ini memerlukan penambahan manual ke bot1.py atau telegram_bot.py.{X}")
        print(f"  {W}Kode yang perlu ditambahkan:{X}\n")
        print(r.get("kode_atau_nilai", "(tidak ada kode)"))
        print(f"\n  {C}Tambahkan kode di atas ke file yang sesuai, lalu restart bot.{X}")
        konfirmasi = input(f"\n  Sudah ditambahkan manual? (y/n): ").strip().lower()
        if konfirmasi == "y":
            r["status"] = "applied"
            print(f"  {G}✅ Ditandai sebagai diterapkan.{X}")
        else:
            print(f"  {Y}Dibatalkan. Permintaan tetap pending.{X}")
            return

    r["waktu_selesai"] = datetime.datetime.now().isoformat()
    save_requests(data)
    log("apply", f"#{req_id} {r['judul']}")
    print(f"\n{G}✅ Permintaan #{req_id} berhasil diterapkan!{X}\n")

def reject_permintaan(req_id: int):
    data = load_requests()
    r = next((x for x in data if x["id"] == req_id), None)
    if not r:
        print(f"{R}Permintaan #{req_id} tidak ditemukan.{X}")
        return
    if r["status"] in ("applied", "rejected"):
        print(f"{Y}Sudah {r['status']}.{X}")
        return

    catatan = input(f"Catatan penolakan (opsional): ").strip()
    r["status"]          = "rejected"
    r["catatan_pemilik"] = catatan
    r["waktu_selesai"]   = datetime.datetime.now().isoformat()
    save_requests(data)
    log("reject", f"#{req_id} {r['judul']}")
    print(f"{R}❌ Permintaan #{req_id} ditolak.{X}\n")

def clear_selesai():
    data = load_requests()
    before = len(data)
    data = [r for r in data if r["status"] == "pending"]
    save_requests(data)
    hapus = before - len(data)
    log("clear", f"{hapus} item dihapus")
    print(f"{G}✅ {hapus} permintaan selesai dihapus. Sisa: {len(data)} pending.{X}\n")

# ─── Tool untuk ditambahkan ke telegram_bot.py & bot1.py ─────────────────────
TOOL_CODE = '''
# ── Tambahkan tool ini ke telegram_bot.py dan bot1.py ──────────────────────
# Import di bagian atas:
#   from upgrade_manager import ajukan_permintaan as _ajukan

@tool
def ajukan_upgrade(judul: str, jenis: str, deskripsi: str, kode_atau_nilai: str = "") -> str:
    """
    Ajukan permintaan upgrade kepada pemilik bot.
    Gunakan ini ketika butuh tool baru, package baru, atau perubahan konfigurasi.
    Args:
        judul           : Judul singkat, contoh 'Tool kirim email'
        jenis           : Salah satu dari: tool_baru, env_config, package, script, lainnya
        deskripsi       : Penjelasan mengapa dibutuhkan
        kode_atau_nilai : Kode Python yang diusulkan atau nilai konfigurasi
    Returns:
        Konfirmasi permintaan tercatat.
    """
    from upgrade_manager import ajukan_permintaan
    return ajukan_permintaan(judul, jenis, deskripsi, kode_atau_nilai)
'''

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]

    if not args:
        tampilkan_semua()
        return

    cmd = args[0].lower()

    if cmd == "apply" and len(args) == 2:
        apply_permintaan(int(args[1]))

    elif cmd == "reject" and len(args) == 2:
        reject_permintaan(int(args[1]))

    elif cmd == "detail" and len(args) == 2:
        tampilkan_detail(int(args[1]))

    elif cmd == "clear":
        clear_selesai()

    elif cmd == "tool-code":
        print(TOOL_CODE)

    elif cmd == "test":
        # Buat contoh permintaan untuk demo
        print("Membuat contoh permintaan demo...")
        ajukan_permintaan(
            judul="Tool kirim notifikasi email",
            jenis="tool_baru",
            deskripsi="Agen butuh tool untuk kirim email notifikasi ketika task selesai. "
                      "Berguna untuk laporan harian otomatis.",
            kode_atau_nilai="""@tool
def kirim_email(tujuan: str, subjek: str, isi: str) -> str:
    import smtplib
    from email.mime.text import MIMEText
    # implementasi menggunakan SMTP_HOST dari .env
    return "Email terkirim"
"""
        )
        ajukan_permintaan(
            judul="Install pandas untuk analisis data",
            jenis="package",
            deskripsi="Butuh pandas untuk memproses file CSV dan membuat laporan statistik.",
            kode_atau_nilai="pandas"
        )
        ajukan_permintaan(
            judul="Tambah SMTP config untuk email",
            jenis="env_config",
            deskripsi="Konfigurasi server email untuk fitur notifikasi.",
            kode_atau_nilai="SMTP_HOST=smtp.gmail.com\nSMTP_PORT=587\nSMTP_USER=\nSMTP_PASS="
        )
        print("✅ 3 contoh permintaan dibuat. Jalankan: python upgrade_manager.py")

    else:
        print(f"""
{W}upgrade_manager.py — Kelola permintaan upgrade agen{X}

Penggunaan:
  {G}python upgrade_manager.py{X}              → lihat semua permintaan
  {G}python upgrade_manager.py detail <id>{X}  → detail lengkap
  {G}python upgrade_manager.py apply <id>{X}   → terapkan permintaan
  {R}python upgrade_manager.py reject <id>{X}  → tolak permintaan
  {D}python upgrade_manager.py clear{X}        → hapus yang sudah selesai
  {D}python upgrade_manager.py test{X}         → buat contoh demo
  {D}python upgrade_manager.py tool-code{X}    → tampilkan kode tool untuk bot
""")

if __name__ == "__main__":
    main()
      

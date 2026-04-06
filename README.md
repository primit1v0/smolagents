# 🤖 Bot Agen Otonom

Bot AI otonom berbasis **smolagents** yang berjalan di Termux/Void Linux.  
Beroperasi sepenuhnya di dalam folder `~/bot1` — tidak pernah menyentuh root sistem.

---

## 🚀 Cara Mulai

```bash
# 1. Jalankan setup (sekali saja)
bash setup.sh

# 2. Isi API key
nano .env

# 3. Aktifkan venv lalu jalankan
source env/bin/activate
python bot1.py
```

---

## 🔑 API Key (pilih salah satu, keduanya GRATIS)

### Opsi A: OpenRouter (Rekomendasi)
- Daftar di https://openrouter.ai
- Dapatkan key → isi di `.env`: `OPENROUTER_KEY=sk-or-...`
- Akses model gratis: Llama 3.3 70B, Gemma 2, Mistral, dll

### Opsi B: HuggingFace
- Daftar di https://huggingface.co
- Settings → Access Tokens → New Token
- Isi di `.env`: `HF_TOKEN=hf_...`

---

## 💬 Cara Pakai

### Mode interaktif (ngobrol langsung)
```bash
python bot1.py
```
Contoh perintah ke agen:
- `carikan berita teknologi terbaru dan simpan ke workspace/berita.md`
- `baca PDF di workspace/dokumen.pdf dan buat ringkasannya`
- `cari repo Python terbaik untuk scraping di GitHub`
- `backup semua file workspace ke GitHub`
- `sync workspace ke OneDrive`

### Mode satu task
```bash
python bot1.py --task "ringkas 5 berita AI terbaru dan simpan ke workspace/ringkasan.md"
```

### Mode daemon (otomatis dari daftar task)
Edit `tasks.json`, tambahkan task, lalu:
```bash
python bot1.py --daemon
```

---

## 🛠️ Kemampuan Agen

| Kemampuan | Detail |
|---|---|
| 🔍 Pencarian web | DuckDuckGo, tidak butuh API key |
| 🌐 Browse halaman | Ambil teks dari URL apapun |
| 📄 Baca PDF | Lokal atau dari URL |
| 💾 Tulis/baca file | Hanya di `workspace/` |
| ⚙️ Jalankan shell | Terbatas di `workspace/`, tidak bisa keluar |
| 📦 Install package | `pip install` otomatis saat butuh |
| ☁️ Backup GitHub | Commit + push otomatis |
| ☁️ Sync OneDrive | Via rclone |

---

## ☁️ Setup Backup (Opsional)

### GitHub
```bash
# Di .env:
GITHUB_REPO=https://username:TOKEN@github.com/username/nama-repo.git
```
Token: GitHub → Settings → Developer settings → Personal access tokens

### OneDrive
```bash
rclone config
# Pilih: New remote → Microsoft OneDrive
# Nama remote HARUS: onedrive
# Ikuti panduan OAuth (buka link di browser HP)
```

---

## 📂 Struktur Folder

```
~/bot1/
├── bot1.py          ← agen utama
├── setup.sh         ← setup awal
├── tasks.json       ← daftar task untuk mode daemon
├── agent_log.json   ← riwayat aktivitas agen
├── .env             ← API key (JANGAN dishare)
├── .env.example     ← template .env
├── env/             ← virtual environment Python
└── workspace/       ← semua file hasil kerja agen
    ├── berita.md
    ├── ringkasan.txt
    └── git_backup/  ← untuk backup GitHub
```

---

## ⚠️ Catatan Keamanan

- Agen **tidak bisa** keluar dari folder `~/bot1`
- Shell command yang mengandung `..`, `/root`, `/etc`, `sudo`, `rm -rf /` otomatis diblokir
- Semua aktivitas dicatat di `agent_log.json`
- API key tersimpan lokal di `.env`, tidak pernah dikirim ke luar kecuali ke provider LLM

---

## 🔄 Otomatis Harian (Cron)

```bash
# Jalankan bot setiap jam 7 pagi
crontab -e

# Tambahkan baris:
0 7 * * * cd ~/bot1 && source env/bin/activate && python bot1.py --daemon
```


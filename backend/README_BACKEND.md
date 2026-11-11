# Backend Human GVC (FastAPI + PostgreSQL)

Mengimplementasikan kontrak `frontend/docs/API_CONTRACT.md`: UC-01 s.d. UC-07, BR-01..BR-08, FR-13 (log akses).
Arsitektur mengikuti Desain Modular: **API** (`app/routers`), **Job Manager + Workflow Engine** (`app/pipeline.py`), **Database** (`database/01_schema.sql`), **Storage** (folder `STORAGE_DIR`).

## Menjalankan
```bash
# 1. Database (sekali saja)
psql -U postgres -c "CREATE DATABASE human_gvc;"
psql -U postgres -d human_gvc -v ON_ERROR_STOP=1 -f database/01_schema.sql
psql -U postgres -d human_gvc -v ON_ERROR_STOP=1 -f database/02_seed_awal.sql   # akun + referensi bawaan
psql -U postgres -d human_gvc -v ON_ERROR_STOP=1 -f database/03_akun_verifikasi.sql   # registrasi, verifikasi email, reset sandi

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env                                       # isi DATABASE_URL dan SECRET_KEY
uvicorn app.main:app --reload --port 8000
```
Cek: http://localhost:8000/api/health dan http://localhost:8000/docs (dokumentasi interaktif semua endpoint).

Akun awal (dari `02_seed_awal.sql`, **ganti sebelum dipakai sungguhan**):
`rakahendrawan@ipb.ac.id / Admin#123` (administrator), `peneliti@ipb.ac.id / Peneliti#123`.

## Akun: registrasi, verifikasi email, lupa kata sandi
Alur: Daftar → akun dibuat *belum terverifikasi* (tidak bisa login) → email berisi tautan `APP_URL/verifikasi?token=...` → klik → akun aktif.
Lupa kata sandi memakai mekanisme token yang sama (`/reset-sandi?token=...`, berlaku 60 menit, sekali pakai). Pendaftar mandiri selalu berperan `peneliti`.

**Mode pengembangan (tanpa email asli):** biarkan `SMTP_HOST` kosong. Saat mendaftar, lihat **terminal tempat uvicorn berjalan**: baris `[EMAIL-DEV]` memuat tautan verifikasi; salin ke browser.

**Memakai Gmail SMTP:**
1. Akun Google → Keamanan → aktifkan **Verifikasi 2 Langkah**.
2. Buka https://myaccount.google.com/apppasswords, buat App Password (16 karakter).
3. Isi `backend/.env`:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alamatanda@gmail.com
SMTP_PASSWORD=abcdefghijklmnop      # App Password, bukan kata sandi Gmail
SMTP_FROM=alamatanda@gmail.com
APP_URL=http://localhost:3000
```
4. Restart uvicorn, daftar dengan email lain yang bisa Anda buka, lalu cek kotak masuk (dan folder spam).
Catatan: Gmail membatasi jumlah email per hari untuk akun biasa; untuk produksi gunakan layanan email transaksional. **Pengiriman lewat Gmail SMTP belum diuji pada pengembangan ini** (yang diuji: seluruh alur memakai mode pengembangan). Jangan commit `.env` ke Git.

## Mode pipeline
- `simulasi` (default): tiap tahap menunggu `SIM_DETIK_PER_TAHAP` detik lalu membangkitkan varian acak yang tetap mematuhi parameter (min depth, min QUAL). Nama sampel berisi "gagal" memicu kegagalan di Alignment.
- `nyata`: `fastp` (QC+trimming) → `bwa mem` → `samtools sort/index` → `bcftools mpileup|call` → `bcftools view` (filter) → `bcftools annotate`.
  Pasang: `conda install -c bioconda -c conda-forge fastp bwa samtools bcftools` (Windows: WSL).
  Letakkan `GRCh38.fasta` dan `dbSNP_v155.vcf.gz` di `storage/references/` (sesuai `referensi.lokasi_berkas`). Anotasi GTF/GFF dilewati (hanya VCF).
  **Mode nyata belum dijalankan terhadap data sekuens sungguhan** (hanya parser VCF yang diuji). Coba dengan FASTQ kecil dulu.

## Tes otomatis
```bash
pip install -r requirements-dev.txt
psql -U postgres -c "CREATE DATABASE human_gvc_test;"      # lalu jalankan 01 dan 02 pada database ini
export TEST_DATABASE_URL=postgresql://postgres:PASSWORD@localhost:5432/human_gvc_test
python -m pytest -q
```
15 tes menjalankan alur lengkap pada PostgreSQL asli (aturan bisnis, hak akses, jejak akses). **Jangan arahkan ke database dev**: tes mengosongkan tabel data.

## Keputusan dan batasan
- Hash kata sandi memakai `pgcrypto` (bcrypt) di SQL, kompatibel dengan `Insert_Select_Dummy.sql`. Token HMAC berlaku 12 jam.
- Batas percobaan (daftar, kirim ulang, lupa sandi, login) disimpan di memori proses: hilang saat restart dan tidak dibagi antar-instance.
- Setelah kata sandi di-reset, sesi login lama masih berlaku sampai tokennya kedaluwarsa (12 jam); token tidak disimpan di server.
- BR-08: analisis lewat masa retensi tidak ditampilkan/diakses; data belum dihapus fisik.
- Setelah server restart, analisis `menunggu/berjalan` ditandai `gagal` (progres tidak bisa dilanjutkan).
- NFR "data genomik terenkripsi": belum ada enkripsi at-rest; gunakan enkripsi disk/bucket saat deployment.
- `MAX_UPLOAD_MB` adalah asumsi (SKPL hanya menyebut "ukuran wajar"). Unggahan diproses sinkron di request.

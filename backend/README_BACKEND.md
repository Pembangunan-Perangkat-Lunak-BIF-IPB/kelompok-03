# Backend Human GVC (FastAPI + PostgreSQL)

Mengimplementasikan kontrak `frontend/docs/API_CONTRACT.md`: UC-01 s.d. UC-07, BR-01..BR-08, FR-13 (log akses).
Arsitektur mengikuti Desain Modular: **API** (`app/routers`), **Job Manager + Workflow Engine** (`app/pipeline.py`), **Database** (`database/01_schema.sql`), **Storage** (folder `STORAGE_DIR`).

## Menjalankan
```bash
# 1. Database (sekali saja)
psql -U postgres -c "CREATE DATABASE human_gvc;"
psql -U postgres -d human_gvc -v ON_ERROR_STOP=1 -f database/01_schema.sql
psql -U postgres -d human_gvc -v ON_ERROR_STOP=1 -f database/02_seed_awal.sql   # akun + referensi bawaan

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
8 tes menjalankan alur lengkap pada PostgreSQL asli (aturan bisnis, hak akses, jejak akses). **Jangan arahkan ke database dev**: tes mengosongkan tabel data.

## Keputusan dan batasan
- Hash kata sandi memakai `pgcrypto` (bcrypt) di SQL, kompatibel dengan `Insert_Select_Dummy.sql`. Token HMAC berlaku 12 jam.
- BR-08: analisis lewat masa retensi tidak ditampilkan/diakses; data belum dihapus fisik.
- Setelah server restart, analisis `menunggu/berjalan` ditandai `gagal` (progres tidak bisa dilanjutkan).
- NFR "data genomik terenkripsi": belum ada enkripsi at-rest; gunakan enkripsi disk/bucket saat deployment.
- `MAX_UPLOAD_MB` adalah asumsi (SKPL hanya menyebut "ukuran wajar"). Unggahan diproses sinkron di request.

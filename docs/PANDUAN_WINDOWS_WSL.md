# Panduan Menjalankan Human GVC di Windows (WSL2 Ubuntu)

> **Untuk Anggota Tim Pengguna Windows (Human GVC, Kelompok GenoSys)**  
> Disusun oleh: **Dhafin Fasya Arifin (Project Manager)**  
> Target: Memastikan seluruh komponen (Frontend Next.js, Backend FastAPI, PostgreSQL, dan Pipeline Nyata Bioinformatika) dapat berjalan mulus di laptop Windows tanpa kendala.

---

## DAFTAR ISI
1. [Prinsip Penting: Kenapa Harus WSL2?](#1-prinsip-penting-kenapa-harus-wsl2)
2. [Langkah 1: Mengaktifkan dan Memasang WSL2 (Ubuntu)](#langkah-1-mengaktifkan-dan-memasang-wsl2-ubuntu)
3. [Langkah 2: Menaruh Repositori di Filesystem Linux (Wajib)](#langkah-2-menaruh-repositori-di-filesystem-linux-wajib)
4. [Langkah 3: Memasang Miniforge (Conda) & Tools Bioinformatika](#langkah-3-memasang-miniforge-conda--tools-bioinformatika)
5. [Langkah 4: Memasang dan Menyiapkan PostgreSQL di WSL2](#langkah-4-memasang-dan-menyiapkan-postgresql-di-wsl2)
6. [Langkah 5: Menyiapkan dan Menjalankan Backend (FastAPI)](#langkah-5-menyiapkan-dan-menjalankan-backend-fastapi)
7. [Langkah 6: Menyiapkan dan Menjalankan Frontend (Next.js)](#langkah-6-menyiapkan-dan-menjalankan-frontend-nextjs)
8. [Langkah 7: Menjalankan Pipeline Nyata dengan Data Uji Cepat](#langkah-7-menjalankan-pipeline-nyata-dengan-data-uji-cepat)
9. [Troubleshooting & Masalah Umum di Windows/WSL2](#troubleshooting--masalah-umum-di-windowswsl2)

---

## 1. Prinsip Penting: Kenapa Harus WSL2?

Alat bioinformatika inti (`bwa`, `samtools`, `bcftools`) **tidak memiliki binary native untuk Command Prompt / PowerShell Windows**. Oleh karena itu, kita menjalankan seluruh server (Backend, Bio-tools, Database, Frontend) di dalam **WSL2 (Windows Subsystem for Linux)** dengan distro **Ubuntu**.

> [!IMPORTANT]
> Browser Anda tetap menggunakan Google Chrome / Edge bawaan Windows seperti biasa melalui alamat `http://localhost:3000`. Windows 10/11 secara otomatis meneruskan (*forward*) port dari WSL2 ke Windows host.

---

## Langkah 1: Mengaktifkan dan Memasang WSL2 (Ubuntu)

1. Buka **PowerShell** di Windows dengan mode **Run as Administrator** (Klik kanan icon Windows $\rightarrow$ Terminal / PowerShell (Admin)).
2. Jalankan perintah instalasi otomatis:
   ```powershell
   wsl --install -d Ubuntu-22.04
   ```
3. Jika komputer meminta restart, lakukan **Restart Laptop**.
4. Setelah restart, jendela terminal hitam Ubuntu akan terbuka otomatis. Tunggu beberapa detik hingga diminta membuat username dan password:
   * **Enter new UNIX username:** (masukkan nama panggilan tanpa spasi, misal `fattha` atau `abid`)
   * **New password:** (ketik password Anda — *karakter memang tidak muncul di layar demi keamanan*, lalu tekan Enter).
5. Perbarui paket Ubuntu di dalam terminal tersebut:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y build-essential curl wget git unzip
   ```

---

## Langkah 2: Menaruh Repositori di Filesystem Linux (Wajib)

> [!WARNING]
> **JANGAN** menaruh folder proyek di `/mnt/c/...` (folder C: Windows)!  
> Mengakses filesystem Windows dari WSL2 memperlambat proses bioinformatika (I/O disk) hingga **10x–50x lebih lambat**. Taruhlah selalu di direktori home Linux (`~`).

Di dalam terminal Ubuntu WSL2:
1. Pastikan Anda berada di direktori home Linux:
   ```bash
   cd ~
   pwd
   # Hasilnya harus: /home/username_anda
   ```
2. Clone repositori proyek (atau salin folder proyek ke sini):
   ```bash
   git clone https://github.com/Pembangunan-Perangkat-Lunak-BIF-IPB/kelompok-03.git human-gvc
   cd human-gvc
   ```
   *(Tips: Jika Anda ingin membuka folder ini di File Explorer Windows, cukup ketik `explorer.exe .` di terminal Ubuntu).*

---

## Langkah 3: Memasang Miniforge (Conda) & Tools Bioinformatika

Perangkat `fastp`, `bwa`, `samtools`, `bcftools`, dan `wgsim` dipasang melalui Conda agar versinya seragam dengan Mac dan Linux server.

1. Unduh dan pasang Miniforge di Ubuntu WSL2:
   ```bash
   curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
   bash Miniforge3-Linux-x86_64.sh -b
   ~/miniforge3/bin/conda init bash
   source ~/.bashrc
   ```
2. Dari root folder repositori `human-gvc/`, buat environment `human-gvc` dari berkas `environment.yml`:
   ```bash
   conda env create -f environment.yml
   conda activate human-gvc
   ```
3. **Uji Verifikasi**: Pastikan seluruh perkakas bioinformatika aktif:
   ```bash
   fastp --version
   bwa 2>&1 | head -n 3
   samtools --version | head -n 2
   bcftools --version | head -n 2
   which wgsim
   ```
   *(Semua perintah di atas harus menampilkan versi tanpa error `command not found`).*

---

## Langkah 4: Memasang dan Menyiapkan PostgreSQL di WSL2

1. Pasang PostgreSQL di Ubuntu:
   ```bash
   sudo apt install -y postgresql postgresql-contrib
   ```
2. Jalankan dan pastikan service PostgreSQL aktif:
   ```bash
   sudo service postgresql start
   sudo service postgresql status
   ```
3. Set password untuk user bawaan `postgres`:
   ```bash
   sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
   ```
4. Buat database dan jalankan migrasi database berurutan:
   ```bash
   # Buat database
   sudo -u postgres psql -c "CREATE DATABASE human_gvc;"

   # Jalankan skrip skema, seed, dan migrasi (dari root folder proyek)
   sudo -u postgres psql -d human_gvc -f database/01_schema.sql
   sudo -u postgres psql -d human_gvc -f database/02_seed_awal.sql
   sudo -u postgres psql -d human_gvc -f database/03_akun_verifikasi.sql
   sudo -u postgres psql -d human_gvc -f database/04_ringkasan_analisis.sql
   ```

---

## Langkah 5: Menyiapkan dan Menjalankan Backend (FastAPI)

1. Pastikan environment conda `human-gvc` aktif:
   ```bash
   conda activate human-gvc
   ```
2. Masuk ke folder `backend/`:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. Buat file `.env` dari template `env.example`:
   ```bash
   cp env.example .env
   ```
4. Periksa isi `backend/.env`:
   * Pastikan `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/human_gvc`
   * Pastikan `PIPELINE_MODE=nyata`
   * Pastikan `PIPELINE_THREADS=4` (atau `2` jika laptop Anda hemat daya)
   * Pastikan `PIPELINE_WORKERS=1`
5. Jalankan server backend:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
6. Buka browser di Windows, cek:
   * `http://localhost:8000/api/health` $\rightarrow$ harus menampilkan status `"api": "ok"`, `"database": "terhubung"`, dan daftar versi perangkat bioinformatika.

---

## Langkah 6: Menyiapkan dan Menjalankan Frontend (Next.js)

Buka **jendela terminal WSL2 kedua** (biarkan backend tetap berjalan di terminal pertama):

1. Pasang Node.js LTS (rekomendasi Node.js v18 atau v20):
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
   sudo apt install -y nodejs
   node -v && npm -v
   ```
2. Masuk ke folder `frontend/`:
   ```bash
   cd ~/human-gvc/frontend
   ```
3. Buat berkas `.env.local`:
   ```bash
   cp .env.local.example .env.local
   ```
   *Buka `.env.local` dan pastikan isinya:*
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_USE_MOCK=false
   ```
4. Pasang dependensi dan jalankan frontend:
   ```bash
   npm install
   npm run dev
   ```
5. Buka browser di Windows:
   Buka `http://localhost:3000` $\rightarrow$ Antarmuka Human GVC akan terbuka!
   * Akun awal: `peneliti@ipb.ac.id` / `Peneliti#123` (atau `rakahendrawan@ipb.ac.id` / `Admin#123`).

---

## Langkah 7: Menjalankan Pipeline Nyata dengan Data Uji Cepat

> [!CAUTION]
> **JANGAN mengunggah genom referensi GRCh38 penuh (3.1 GB) di laptop!**  
> `bwa index` untuk genom 3.1 GB membutuhkan waktu lebih dari 1 jam di 1 core CPU. Gunakan **data uji mini (10 Kb)** yang selesai dalam **5 detik**!

1. Buat data uji mini deterministik (dari root folder proyek):
   ```bash
   python3 tools/buat_data_uji.py --outdir data_uji --panjang 10000 --nsnp 20
   ```
2. Masuk ke antarmuka web `http://localhost:3000`:
   * **Langkah A (Unggah Data):** Unggah sampel FASTQ paired-end menggunakan file:
     * Read 1: `data_uji/sample_R1.fastq.gz`
     * Read 2: `data_uji/sample_R2.fastq.gz`
   * **Langkah B (Pengaturan):**
     * Klik tombol **Unggah Referensi Baru** $\rightarrow$ unggah `data_uji/ref.fa` (pilih jenis: *Genom Referensi*).
     * Unggah referensi anotasi $\rightarrow$ pilih `data_uji/anotasi_dbsnp.vcf.gz` (pilih jenis: *Anotasi Varian*).
     * Simpan pengaturan dan konfirmasi.
   * **Langkah C (Eksekusi):** Klik **Jalankan Analisis**.
3. Buka menu **Status & Log**:
   * Perhatikan progres 0% $\rightarrow$ 100% bergerak melewati 6 tahap secara nyata.
4. Buka menu **Hasil Analisis**:
   * Tabel kandidat varian akan tampil.
   * Kartu metrik **QC & Trimming (FR-14)** dan **Alignment (FR-15)** akan muncul lengkap dengan angka persentase teralign.

---

## Troubleshooting & Masalah Umum di Windows/WSL2

### 1. `Preflight pipeline nyata gagal: Perangkat belum terpasang di server`
* **Penyebab:** Backend dijalankan di terminal yang belum mengaktifkan conda environment `human-gvc`.
* **Solusi:** Di terminal backend, jalankan `conda activate human-gvc`, pastikan `which bwa` menampilkan path, lalu restart uvicorn.

### 2. `psql: error: connection to server on socket ... failed`
* **Penyebab:** Layanan PostgreSQL di Ubuntu WSL2 belum dinyalakan (WSL2 tidak selalu menyalakan service otomatis saat startup).
* **Solusi:** Jalankan perintah:
  ```bash
  sudo service postgresql start
  ```

### 3. Browser Windows tidak bisa membuka `http://localhost:3000` atau `:8000`
* **Penyebab:** Host binding backend/frontend hanya mendengarkan di IP internal loopback.
* **Solusi:** 
  * Untuk backend, jalankan selalu dengan flag `--host 0.0.0.0`:
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
  * Jika masih terkendala, cari IP internal WSL dengan `hostname -I` di terminal Ubuntu (misal `172.x.x.x`), lalu buka `http://172.x.x.x:3000` di Windows.

### 4. RAM Laptop Penuh saat WSL2 Berjalan
* **Penyebab:** WSL2 secara bawaan dapat menggunakan hingga 50%–80% dari total RAM Windows.
* **Solusi:** Di Windows, buka Notepad, buat file `C:\Users\<Username_Windows>\.wslconfig`:
  ```ini
  [wsl2]
  memory=4GB
  processors=4
  ```
  Lalu di PowerShell Windows jalankan `wsl --shutdown` dan buka kembali Ubuntu WSL2.


# Panduan Lingkungan — Human GVC (Pipeline Nyata)

> Ditulis oleh: Dhafin (WP-2). Terakhir diperbarui: 2026-11-09.
> Berlaku untuk: macOS Apple Silicon (arm64), macOS Intel (x86_64), WSL2 Ubuntu.

## Prasyarat

| Kebutuhan | Versi minimum | Catatan |
|---|---|---|
| Conda | 23.x+ | Miniconda atau Anaconda; `conda --version` untuk cek |
| PostgreSQL | 14+ | Sudah berjalan untuk backend |
| Node.js | 18+ | Untuk frontend Next.js |

> **Windows:** gunakan **WSL2 (Ubuntu 22.04)**, bukan PowerShell/CMD. Semua perintah di bawah dijalankan di dalam WSL2.

---

## Langkah 1 — Buat environment conda

```bash
# dari root repositori
conda env create -f environment.yml
```

Jika sudah ada environment lama dan ingin memperbarui:
```bash
conda env update -f environment.yml --prune
```

---

## Langkah 2 — Aktifkan environment

```bash
conda activate human-gvc
```

---

## Langkah 3 — Verifikasi semua tool terpasang

Jalankan perintah berikut satu per satu dan catat versinya:

```bash
fastp --version
bwa 2>&1 | head -3
samtools --version | head -1
bcftools --version | head -1
wgsim 2>&1 | head -3
```

Keluaran yang diharapkan (versi bisa sedikit berbeda):

```
fastp 0.23.4
...
bwa
Program: bwa (alignment via Burrows-Wheeler Alginment)
Version: 0.7.18-r1243-dirty
...
samtools 1.21
...
bcftools 1.21
...
```

---

## Langkah 4 — Variabel lingkungan backend

Salin `backend/env.example` ke `backend/.env` dan sesuaikan:

```bash
cp backend/env.example backend/.env
```

Untuk mengaktifkan mode pipeline nyata (bukan simulasi), tambahkan baris berikut di `backend/.env`:

```
PIPELINE_MODE=nyata
PIPELINE_WORKERS=1
PIPELINE_THREADS=4
```

> **Catatan:** `PIPELINE_WORKERS=1` direkomendasikan untuk laptop agar tidak kehabisan RAM/CPU saat menjalankan analisis nyata.

---

## Catatan per OS

### macOS Apple Silicon (arm64)

Semua package bioconda (`fastp`, `bwa`, `samtools`, `bcftools`, `wgsim`) tersedia untuk `osx-arm64`. Tidak perlu Rosetta.

Jika conda lambat saat solve dependencies, pertimbangkan menginstal **mamba** dan ganti `conda` dengan `mamba`:
```bash
conda install -n base -c conda-forge mamba
mamba env create -f environment.yml
```

### macOS Intel (x86_64)

Sama seperti arm64. Pastikan `conda config --show subdir` menampilkan `osx-64`.

### WSL2 Ubuntu (Windows)

1. Pastikan WSL2 sudah terinstal: `wsl --install` di PowerShell sebagai Administrator.
2. Gunakan distribusi Ubuntu 22.04.
3. Instal Miniconda di dalam WSL2:
   ```bash
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
   bash Miniconda3-latest-Linux-x86_64.sh
   ```
4. Lanjutkan dari Langkah 1 di atas.

---

## Matriks Verifikasi Anggota

Isi baris milikmu setelah berhasil menjalankan Langkah 3:

| Nama | OS | Arsitektur | Conda | fastp | bwa | samtools | bcftools | Berhasil? |
|---|---|---|---|---|---|---|---|---|
| Dhafin | macOS | arm64 | 26.9.3 | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` |
| Rakazaki | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` |
| Yafits | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` |
| Abid | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` |
| Fattha | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` | `[ISI]` |

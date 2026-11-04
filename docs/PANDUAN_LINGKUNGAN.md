# Panduan Penyiapan Lingkungan Bioinformatika (Human GVC)

Disusun oleh: **Dhafin Fasya Arifin (Project Manager, WP-2)**  
Target: Memenuhi Gerbang M0 dan Kriteria K8 (Standarisasi Lingkungan Perangkat Pipeline Nyata).

---

## 1. Daftar Perangkat yang Dibutuhkan
Pipeline nyata membutuhkan 5 perkakas bioinformatika utama:
1. `fastp` (QC & Read Trimming)
2. `bwa` (Burrows-Wheeler Aligner / Alignment ke Referensi)
3. `samtools` (Pengurutan, konversi format SAM/BAM, indexing, statistik BAM)
4. `bcftools` (Variant Calling, filtering VCF, anotasi VCF)
5. `wgsim` (Simulator data sekuens untuk WP-5 / data uji)

---

## 2. Petunjuk Instalasi Berdasarkan Sistem Operasi

### A. macOS (Apple Silicon M1/M2/M3/M4 & Intel)

#### 1. Pasang Miniforge (Rekomendasi Utama Conda untuk Mac)
Jika belum memiliki conda di laptop Anda, gunakan Homebrew:
```bash
brew install --cask miniforge
```
Setelah instalasi selesai, inisialisasi conda untuk zsh:
```bash
conda init zsh
```
*Tutup dan buka kembali terminal Anda.*

#### 2. Buat dan Aktifkan Environment
Dari root repositori `human-gvc-fullstack-akun/`:
```bash
conda env create -f environment.yml
conda activate human-gvc
```

#### Alternatif Cepat macOS via Homebrew (Tanpa Conda):
Jika Anda lebih nyaman tanpa Conda, perangkat bioinformatika juga dapat dipasang via brew:
```bash
brew install fastp bwa samtools bcftools
```
*(Catatan: `wgsim` umumnya lebih mudah didapat melalui bioconda).*

---

### B. Windows (Menggunakan WSL2 Ubuntu)

> **PENTING:** Perangkat bioinformatika seperti BWA dan Samtools tidak berjalan secara native di Windows command prompt biasa. Semua anggota tim pengguna Windows **wajib memakai WSL2 (Windows Subsystem for Linux)**.

1. Buka PowerShell (Run as Administrator):
   ```powershell
   wsl --install -d Ubuntu-22.04
   ```
2. Restart laptop jika diminta, lalu buka aplikasi Ubuntu terminal.
3. Di dalam terminal Ubuntu, pasang Miniforge:
   ```bash
   curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
   bash Miniforge3-Linux-x86_64.sh
   source ~/.bashrc
   ```
4. Masuk ke folder proyek dan buat environment:
   ```bash
   conda env create -f environment.yml
   conda activate human-gvc
   ```

---

### C. Linux (Ubuntu / Debian Native)

1. Unduh dan pasang Miniforge:
   ```bash
   curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
   bash Miniforge3-Linux-x86_64.sh
   source ~/.bashrc
   ```
2. Buat environment:
   ```bash
   conda env create -f environment.yml
   conda activate human-gvc
   ```

---

## 3. Uji Verifikasi Lingkungan

Setelah mengaktifkan environment (`conda activate human-gvc`), jalankan perintah berikut untuk memastikan semua perangkat siap digunakan:

```bash
fastp --version
bwa 2>&1 | head -n 4
samtools --version | head -n 2
bcftools --version | head -n 2
which wgsim
```

Jika kelima perintah di atas menampilkan versi tanpa pesan `command not found`, lingkungan bioinformatika laptop Anda telah siap 100%!


# Dokumen Spesifikasi Pemetaan Parameter Bioinformatika (Human GVC)

Disusun oleh: **Yafits (System Analyst, WP-3)**  
Status: Final untuk Minggu 9 (Memenuhi BR-04, FR-05, FR-06, FR-16, dan Gerbang M0/K4)

---

## 1. Latar Belakang & Prinsip Biologis

Aplikasi Human GVC melakukan identifikasi varian germline manusia (*germline variant calling*) dari data sekuensing DNA (FASTQ) dengan genom referensi GRCh38. Untuk memastikan varian yang dihasilkan memiliki akurasi biologis tinggi dan minim galat teknis (*false positives*), parameter yang dimasukkan pengguna pada antarmuka web (SKPL BR-04) dipetakan secara ketat ke flag perkakas bioinformatika standar emas (*gold standard*).

---

## 2. Tabel Pemetaan Parameter Pengguna ke Perangkat

| Parameter Pengguna (SKPL BR-04) | Bawaan (Default) | Rentang Valid | Perangkat | Flag / Ekspresi Perangkat | Alasan Teknis & Biologis |
|---|---|---|---|---|---|
| **Batas Kualitas Pemangkasan (Min Quality)** | 20 (Q20 = akurasi 99%) | 0 – 40 | `fastp` | `--cut_right --cut_right_window_size 4 --cut_right_mean_quality <val> --cut_tail --cut_tail_mean_quality <val> -q <val>` | Pemangkasan jendela geser (*sliding window*) dari ujung 3' membaca rata-rata Phred score. Basa dengan error tinggi dipangkas tanpa membuang read secara prematur (K4/R1). |
| **Kedalaman Minimal (Min Depth)** | 10x | 1 – 1000 | `bcftools view` | `FMT/DP >= <val>` | Menjamin posisi varian didukung oleh kedalaman pembacaan yang cukup untuk membedakan variasi biologis nyata vs galat PCR/sekuensing. Dipetakan ke tag per-sampel `FMT/DP`. |
| **Batas QUAL Filtering (Min QUAL)** | 30 (Q30 = 99.9% probabilitas varian benar) | 0 – 1000 | `bcftools view` | `QUAL >= <val>` | Phred-scaled probability bahwa posisi tersebut benar-benar polimorfik. Ambang ≥ 30 adalah batas standar germline variant filtering. |

---

## 3. Resolusi Masalah Bioinformatika Khusus

### 3.1 Normalisasi Alel Majemuk & Indel (Mengatasi Risiko R9)
* **Masalah:** Fungsi `parse_vcf` pada modul database membaca alel ALT pertama. Jika terdapat situs multi-alelik (misal `REF: A, ALT: C,G`), varian alternatif kedua (`G`) akan hilang.
* **Solusi WP-3:** Setelah tahap `bcftools call`, jalankan normalisasi `bcftools norm -m- -f <referensi>`:
  * `-m-`: Memecah rekaman multi-alelik menjadi rekaman bi-alelik terpisah sehingga seluruh alel varian tersimpan utuh di basis data.
  * `-f <referensi>`: Melakukan *left-alignment* dan normalisasi indel agar representasi varian konsisten sesuai format standar VCF.

### 3.2 Pemetaan Format Kromosom Anotasi (Mengatasi Risiko R10)
* **Masalah:** Sumber referensi sering kali menggunakan konvensi penamaan kontig yang berbeda dengan basis data anotasi (misal genom referensi menggunakan prefix `chr1`, sedangkan dbSNP menggunakan `1`, atau sebaliknya). Jika nama kontig tidak cocok, `bcftools annotate` akan melewati varian tanpa memberi tahu kesalahan.
* **Solusi WP-3:**
  1. Modul anotasi mendeteksi gaya penamaan kontig antara berkas VCF sampel dan berkas VCF anotasi.
  2. Jika terjadi ketidakcocokan prefix `chr` (contoh `chr1..22` vs `1..22`), modul membuat tabel translasi kontig sementara dan menerapkan flag `--rename-chrs` atau konversi nama kontig secara otomatis.
  3. Mencatat jumlah varian yang berhasil teranotasi ke `log_proses`.

### 3.3 Penanganan Format Anotasi Non-VCF (Keputusan K5)
* Sesuai kesepakatan tim pada Keputusan K5, dukungan format GTF/GFF berada di luar cakupan Minggu 9.
* Jika pengguna mengunggah berkas anotasi berformat non-VCF (misal `.gtf` atau `.gff`), tahap anotasi akan menandai status `dilewati` secara anggun (*graceful*) dengan keterangan jelas di log proses.


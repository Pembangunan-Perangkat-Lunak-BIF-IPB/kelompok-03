# Dokumentasi Data Uji, Truth Set, & Validasi Akurasi (Human GVC)

Disusun oleh: **Fattha (Tester, WP-5)**  
Target: Memenuhi Gerbang Penerimaan G3, G6, dan Pembuktian Akurasi Biologis Pipeline.

---

## 1. Spesifikasi Referensi & Data Uji Sintetis

Untuk menghindari beban komputasi berlebih pada laptop pengembang (GRCh38 penuh berukuran ~3.2 Gb dan membutuhkan waktu indeks berjam-jam), tim menyepakati **Keputusan K1**: menggunakan kontig genom mini sintetis terkontrol.

* **Nama Kontig:** `chr21`
* **Panjang:** 10.000 bp (10 Kb)
* **Kandungan GC:** ~42% (merefleksikan genom manusia)
* **Jumlah Mutasi Disisipkan (Truth Set):** 20 SNP (Single Nucleotide Polymorphisms)
* **Kedalaman Pembacaan (Coverage):** $\ge 35\times$
* **Tipe Bacaan:**
  * Paired-end: 100 bp read length, insert size ~250–320 bp (`sample_R1.fastq.gz`, `sample_R2.fastq.gz`)
  * Single-end: 100 bp read length (`sample_single.fastq.gz`)
* **Basis Data Anotasi Uji:**
  * `anotasi_dbsnp.vcf.gz`: Berisi ID `rs1000..rs1019` dan simbol gen (`BRCA1`, `TP53`, `EGFR`, `KRAS`, `PTEN`, `CFTR`).
  * `anotasi_beda_kontig.vcf.gz`: Kontig tanpa prefix `chr` (contoh: `21`) untuk memvalidasi mekanisme `--rename-chrs` pada WP-3.

---

## 2. Cara Menghasilkan Ulang Data Uji dari Nol

Skrip generator bersifat **deterministik** (menggunakan seed tetap), sehingga dapat dibuat ulang di laptop mana pun dengan hasil bit-for-bit yang identik:

```bash
python3 tools/buat_data_uji.py --outdir data_uji --panjang 10000 --nsnp 20
```

Berkas yang dihasilkan di folder `data_uji/`:
```text
data_uji/
├── ref.fa                         # Genom referensi (10 Kb)
├── truth.vcf                      # Ground truth 20 SNP
├── sample_R1.fastq.gz             # Read 1 paired-end (35x)
├── sample_R2.fastq.gz             # Read 2 paired-end (35x)
├── sample_single.fastq.gz         # Read single-end (35x)
├── anotasi_dbsnp.vcf.gz           # Anotasi dbSNP sintetis
└── anotasi_beda_kontig.vcf.gz     # Anotasi beda kontig (uji R10)
```

---

## 3. Cara Menjalankan Validasi Akurasi (Gerbang G3)

Setelah analisis selesai dan berkas VCF hasil terbentuk di `storage/results/<id_analisis>/hasil.vcf`:

```bash
python3 tools/bandingkan_vcf.py storage/results/<id_analisis>/hasil.vcf data_uji/truth.vcf --ambang 90.0
```

### Ambang Penerimaan Gerbang G3:
* **Recall (Sensitivitas):** $\ge 90.0\%$
* **Presisi:** $\ge 90.0\%$

---

## 4. Karakteristik Waktu Eksekusi Pipeline (Benchmark Laptop Mac Apple Silicon)

Pengukuran durasi tahap pada data uji mini (10 Kb, 35x coverage, 4 threads):

| # | Tahap Pipeline | Perangkat | Durasi Rata-rata | Status |
|---|---|---|:---:|:---:|
| 1 | QC & Trimming | `fastp` | ~1.2 detik | Berhasil |
| 2 | Alignment | `bwa mem` | ~0.8 detik | Berhasil |
| 3 | Pemrosesan BAM | `samtools sort & index` | ~0.6 detik | Berhasil |
| 4 | Variant Calling | `bcftools mpileup & call & norm` | ~1.4 detik | Berhasil |
| 5 | Filtering | `bcftools view` | ~0.3 detik | Berhasil |
| 6 | Anotasi | `bcftools annotate` | ~0.5 detik | Berhasil |
| **Total** | **Siklus Penuh (End-to-End)** | **6 Tahap** | **~4.8 detik** | **Lulus G1 & G2** |


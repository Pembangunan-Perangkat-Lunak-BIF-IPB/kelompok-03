# Dokumen Pemetaan Parameter Pipeline Bioinformatika

> Disusun oleh: Yafits (System Analyst, WP-3) & Dhafin (PM, WP-2)
> Proyek: Human GVC (Kelompok GenoSys)
> Tanggal: 9 November 2026
> Status: Disepakati untuk Implementasi Minggu 9

---

## 1. Pendahuluan

Dokumen ini mendefinisikan pemetaan formal dari parameter analisis yang ditentukan pada SKPL (kebutuhan fungsional FR-06 dan aturan bisnis BR-04) ke dalam perintah dan flag perangkat lunak bioinformatika (*fastp*, *bwa-mem2*, *bcftools*).

Tujuan pemetaan ini adalah memastikan bahwa setiap masukan parameter dari antarmuka pengguna memiliki dampak biologis dan algoritmik yang presisi, terhindar dari salah tafsir flag alat, serta terdokumentasi secara transparan untuk pengujian sistem.

---

## 2. Tabel Pemetaan Parameter Pengguna (BR-04)

| Parameter SKPL | Tipe & Rentang | Nilai Bawaan | Tahap Eksekusi | Perangkat & Flag | Alasan Teknis & Biologis |
|---|---|---|---|---|---|
| **Batas Kualitas Pemangkasan** (`kualitas_pemangkasan_min`) | Integer [0, 40] | 20 (Q20) | `qc_trimming` | `fastp --cut_right --cut_right_mean_quality <nilai> --cut_right_window_size 4` | Memangkas basa berkualitas rendah dari ujung 3' (*tail*) menggunakan jendela geser 4 basa. Menghilangkan artefak sekuensing pada ujung read tanpa membuang seluruh read secara prematur (Keputusan K4). |
| **Batas Kedalaman Minimal** (`kedalaman_min`) | Integer [1, 1000] | 10 (10x) | `filtering` | `bcftools view -i 'FMT/DP>=<nilai> \|\| INFO/DP>=<nilai>'` | Memastikan varian hanya dilaporkan jika didukung oleh cakupan pembacaan yang cukup untuk membedakan variasi germline heterozigot/homozigot sejati dari kesalahan acak PCR/sekuensing. |
| **Batas Skor Kualitas Minimal** (`qual_min`) | Float/Int [0, 1000] | 30 (Phred 30) | `filtering` | `bcftools view -i 'QUAL>=<nilai>'` | Phred scale $Q = -10 \log_{10}(P_{\text{error}})$. Skor QUAL $\ge 30$ berarti probabilitas panggilan varian keliru kurang dari 0.1% (akurasi panggilan 99.9%). |

---

## 3. Rantai Perintah Per Tahap Bioinformatika

### 3.1 Tahap 1: QC & Trimming (`stages/qc_trimming.py`)
- **Perangkat**: `fastp 1.4.0+`
- **Tujuan**: Memangkas adaptor secara otomatis, memotong basa berkualitas rendah dengan jendela geser, dan mencatat ringkasan statistik bacaan sebelum vs sesudah filter.
- **Perintah Baku**:
  ```bash
  fastp \
    -i {fastq_r1} -o {out_r1} \
    [-I {fastq_r2} -O {out_r2}] \
    -j {kerja}/fastp.json -h {kerja}/fastp.html \
    -w {threads} \
    --cut_right \
    --cut_right_window_size 4 \
    --cut_right_mean_quality {kualitas_pemangkasan_min}
  ```

### 3.2 Tahap 2: Alignment (`stages/alignment.py`)
- **Perangkat**: `bwa-mem2 2.2.1` (fallback `bwa 0.7.19`) dan `samtools view`
- **Tujuan**: Memetakan reads terpotong ke genom referensi tanpa menulis file SAM intermediat ke disk (menghemat ruang penyimpanan dan I/O bottleneck).
- **Perintah Baku**:
  ```bash
  bwa-mem2 mem -t {threads} -R '@RG\tID:{id_sampel}\tSM:{nama_sampel_aman}\tPL:ILLUMINA' {referensi} {out_r1} [{out_r2}] \
    | samtools view -@ {threads} -b -o {kerja}/aln_raw.bam -
  ```
- **Pembersihan Nama Sampel**: Karakter spasi, tab, dan karakter khusus digantikan dengan garis bawah (`_`) untuk menjaga validitas sintaks header SAM `@RG`.

### 3.3 Tahap 3: Pemrosesan BAM (`stages/bam_processing.py`)
- **Perangkat**: `samtools 1.25+`
- **Tujuan**: Mengurutkan koordinat genomik, membuat indeks `.bai` untuk akses acak cepat, serta menghitung statistik keterbacaan (alignment rate).
- **Perintah Baku**:
  ```bash
  samtools sort -@ {threads} -o {kerja}/sorted.bam {kerja}/aln_raw.bam
  samtools index {kerja}/sorted.bam
  samtools flagstat {kerja}/sorted.bam > {kerja}/flagstat.txt
  ```

### 3.4 Tahap 4: Variant Calling (`stages/variant_calling.py`)
- **Perangkat**: `bcftools 1.25+` (`mpileup`, `call`, dan `norm`)
- **Tujuan**: Mengidentifikasi variasi SNP dan INDEL terhadap referensi, serta menormalisasi varian multialelik.
- **Perintah Baku**:
  ```bash
  bcftools mpileup -f {referensi} -a FORMAT/DP,FORMAT/AD -Ou {kerja}/sorted.bam \
    | bcftools call -mv -Ou \
    | bcftools norm -m- -Oz -o {kerja}/raw.vcf.gz
  bcftools index -f {kerja}/raw.vcf.gz
  ```
- **Normalisasi Multialelik (`norm -m-`)**:
  Perintah ini krusial untuk memecah baris VCF multialelik (misal ALT: `A,T`) menjadi baris bialelik terpisah (`A` pada satu baris dan `T` pada baris berikutnya). Hal ini mencegah hilangnya varian kedua pada fungsi pengurai `parse_vcf` yang hanya mengonsumsi alel alternatif pertama.

### 3.5 Tahap 5: Filtering (`stages/filtering.py`)
- **Perangkat**: `bcftools view`
- **Tujuan**: Menerapkan ambang batas kualitas dan kedalaman pembacaan yang telah ditetapkan oleh pengguna.
- **Perintah Baku**:
  ```bash
  bcftools view -i 'QUAL>={qual_min} && (FMT/DP>={kedalaman_min} || INFO/DP>={kedalaman_min})' \
    -Oz -o {kerja}/filtered.vcf.gz {kerja}/raw.vcf.gz
  bcftools index -f {kerja}/filtered.vcf.gz
  ```
- **Pencatatan Metrik**: Jumlah record varian sebelum dan sesudah pemfilteran dihitung menggunakan `bcftools view -H | wc -l` dan dicatat ke log proses.
- **Hasil Verifikasi Eksekusi Nyata (`bcftools view -i ...`)**:
  Pengujian dilakukan dengan dataset VCF sintetis yang memiliki kombinasi kasus:
  1. `POS 100`: QUAL=50, DP=20 -> **LOLOS** (memenuhi syarat QUAL >= 30 dan DP >= 10).
  2. `POS 200`: QUAL=15, DP=20 -> **DIGUGURKAN** (gagal pada ambang QUAL).
  3. `POS 300`: QUAL=40, DP=5  -> **DIGUGURKAN** (gagal pada ambang kedalaman).
  4. `POS 400`: QUAL=60, tanpa FMT/DP tetapi INFO/DP=25 -> **LOLOS** (berhasil ditangani berkat fallback `INFO/DP`).
  Perilaku ini memvalidasi keandalan ekspresi filter terhadap variasi skema header VCF.

### 3.6 Tahap 6: Anotasi (`stages/anotasi.py`)
- **Perangkat**: `bcftools annotate`
- **Tujuan**: Menambahkan anotasi genetik (ID rsID dbSNP dan simbol gen) dari berkas referensi anotasi VCF.
- **Perintah Baku**:
  ```bash
  bcftools annotate -a {anotasi} -c ID,INFO/GENE,INFO/GENEINFO \
    -Oz -o {kerja}/annotated.vcf.gz {kerja}/filtered.vcf.gz
  ```
- **Penanganan Ketidaksesuaian Kromosom**:
  Jika referensi menggunakan konvensi `chr1` sedangkan basis data anotasi menggunakan `1` (atau sebaliknya), sistem mendeteksi perbedaan tersebut dan menerapkan opsi `--rename-chrs` agar anotasi tidak dilewati secara senyap.
- **Penanganan Format Non-VCF (GTF/GFF)**:
  Sesuai Keputusan K5, berkas non-VCF dilewati secara anggun dengan status keterangan informatif tanpa menggagalkan alur eksekusi analisis.

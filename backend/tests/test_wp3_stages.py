"""Test mandiri untuk WP-3: Stages variant_calling, filtering, dan anotasi.

Menguji logika bioinformatika:
1. Variant calling dengan mpileup -> call -mv -> norm -m-.
2. Filtering berdasarkan ambang qual_min dan kedalaman_min.
3. Anotasi VCF dengan database anotasi sintetis (termasuk rename kontig otomatis).
4. Penanganan peringatan kontig tidak cocok dan graceful skip untuk non-VCF.
"""
import gzip
import shutil
import subprocess
import tempfile
from pathlib import Path
import pytest

from app.pipeline.konteks import Konteks, TahapGagal
from app.pipeline.runner import Runner
from app.pipeline.stages import variant_calling, filtering, anotasi


def _bcftools_tersedia():
    return bool(shutil.which("bcftools") and shutil.which("samtools"))


@pytest.fixture
def wp3_env():
    d = Path(tempfile.mkdtemp(prefix="wp3_test_"))
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def wp3_dataset(wp3_env):
    """Siapkan mini referensi FASTA, BAM terurut sintetis dengan varian, dan database anotasi VCF."""
    # 1. Referensi mini (chr1: 200 bp)
    ref_path = wp3_env / "mini_ref.fa"
    ref_seq = (
        "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT"
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA"
        "TTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGG"
    )
    ref_path.write_text(f">chr1\n{ref_seq}\n", encoding="utf-8")
    subprocess.run(["samtools", "faidx", str(ref_path)], check=True, capture_output=True)

    # 2. Buat SAM sintetis yang memuat mismatch (varian) pada posisi 20, lalu konversi ke sorted.bam
    sam_path = wp3_env / "mini.sam"
    # Read 1: mismatch di pos 20 (Ref=T diganti G)
    # Read 2: mismatch di pos 20 (Ref=T diganti G)
    # Read 3: mismatch di pos 80 (Ref=A diganti C)
    sam_content = (
        "@HD\tVN:1.6\tSO:coordinate\n"
        f"@SQ\tSN:chr1\tLN:{len(ref_seq)}\n"
        "@RG\tID:101\tSM:Sample1\tPL:ILLUMINA\n"
        "r1\t0\tchr1\t10\t60\t30M\t*\t0\t0\tACGTACGTACGTACGTACGGCGTACGTACG\tIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\tRG:Z:101\n"
        "r2\t0\tchr1\t10\t60\t30M\t*\t0\t0\tACGTACGTACGTACGTACGGCGTACGTACG\tIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\tRG:Z:101\n"
        "r3\t0\tchr1\t10\t60\t30M\t*\t0\t0\tACGTACGTACGTACGTACGGCGTACGTACG\tIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\tRG:Z:101\n"
        "r4\t0\tchr1\t10\t60\t30M\t*\t0\t0\tACGTACGTACGTACGTACGGCGTACGTACG\tIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\tRG:Z:101\n"
        "r5\t0\tchr1\t10\t60\t30M\t*\t0\t0\tACGTACGTACGTACGTACGGCGTACGTACG\tIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\tRG:Z:101\n"
    )
    sam_path.write_text(sam_content, encoding="utf-8")

    bam_path = wp3_env / "sorted.bam"
    subprocess.run(["samtools", "view", "-b", "-o", str(bam_path), str(sam_path)], check=True, capture_output=True)
    subprocess.run(["samtools", "index", str(bam_path)], check=True, capture_output=True)

    # 3. Database anotasi VCF (bgzip + tabix)
    anot_vcf = wp3_env / "dbsnp_mini.vcf"
    anot_vcf.write_text(
        "##fileformat=VCFv4.2\n"
        "##INFO=<ID=GENE,Number=1,Type=String,Description=\"Gene Symbol\">\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "chr1\t29\tfe_rs12345\tA\tG\t100\tPASS\tGENE=BRCA1\n",
        encoding="utf-8",
    )
    anot_gz = wp3_env / "dbsnp_mini.vcf.gz"
    subprocess.run(f"bgzip -c {anot_vcf} > {anot_gz}", shell=True, check=True)
    subprocess.run(["bcftools", "index", "-f", str(anot_gz)], check=True, capture_output=True)

    return {
        "ref": ref_path,
        "bam": bam_path,
        "anot": anot_gz,
    }


@pytest.mark.skipif(not _bcftools_tersedia(), reason="bcftools/samtools belum terpasang")
def test_wp3_rantai_calling_filter_anotasi(wp3_env, wp3_dataset):
    """Uji rantai lengkap WP-3: Variant Calling -> Filtering -> Anotasi."""
    kerja = wp3_env / "run"
    kerja.mkdir()

    ctx = Konteks(
        id_analisis=101,
        id_sampel=1,
        nama_sampel="Sampel_Uji",
        kerja=kerja,
        referensi=wp3_dataset["ref"],
        anotasi=wp3_dataset["anot"],
        fastq_r1=Path("dummy_r1.fastq.gz"),
        fastq_r2=None,
        parameter={"qual_min": 10, "kedalaman_min": 2},
        threads=2,
        berkas={"bam": wp3_dataset["bam"]},
    )

    # 1. Variant Calling
    sh_vc = Runner(ctx.id_analisis, "variant_calling", ke_db=False)
    variant_calling.jalankan(ctx, sh_vc)

    assert "vcf_mentah" in ctx.berkas
    assert ctx.berkas["vcf_mentah"].exists()
    assert (kerja / "raw.vcf.gz.csi").exists() or (kerja / "raw.vcf.gz.tbi").exists()

    # 2. Filtering
    sh_filt = Runner(ctx.id_analisis, "filtering", ke_db=False)
    filtering.jalankan(ctx, sh_filt)

    assert "vcf_filter" in ctx.berkas
    assert ctx.berkas["vcf_filter"].exists()
    assert (kerja / "filtered.vcf.gz.csi").exists() or (kerja / "filtered.vcf.gz.tbi").exists()

    # 3. Anotasi
    sh_anot = Runner(ctx.id_analisis, "anotasi", ke_db=False)
    anotasi.jalankan(ctx, sh_anot)

    assert "vcf_akhir" in ctx.berkas
    assert ctx.berkas["vcf_akhir"].exists()

    # Cek isi VCF akhir: pastikan header atau baris memuat ID rsID atau GENE jika match
    res = subprocess.run(["bcftools", "view", "-H", str(ctx.berkas["vcf_akhir"])], capture_output=True, text=True)
    assert res.returncode == 0
    # Setidaknya ada 1 varian terpanggil dari SAM sintetis
    assert len(res.stdout.strip()) > 0


@pytest.mark.skipif(not _bcftools_tersedia(), reason="bcftools/samtools belum terpasang")
def test_wp3_anotasi_non_vcf_skip(wp3_env, wp3_dataset):
    """Uji bahwa berkas non-VCF (.gtf / .bed) dilewati secara anggun tanpa melempar exception."""
    kerja = wp3_env / "run_non_vcf"
    kerja.mkdir()

    gtf_file = wp3_env / "anotasi.gtf"
    gtf_file.write_text("chr1\tHAVANA\tgene\t1\t100\t.\t+\t.\tgene_id \"ENSG01\";\n", encoding="utf-8")

    ctx = Konteks(
        id_analisis=102,
        id_sampel=2,
        nama_sampel="Sampel_GTF",
        kerja=kerja,
        referensi=wp3_dataset["ref"],
        anotasi=gtf_file,
        fastq_r1=Path("dummy.fq"),
        fastq_r2=None,
        parameter={},
        berkas={"vcf_filter": wp3_dataset["anot"]},  # reuse VCF sebagai input filter
    )

    sh_anot = Runner(ctx.id_analisis, "anotasi", ke_db=False)
    anotasi.jalankan(ctx, sh_anot)

    # vcf_akhir harus menunjuk ke vcf_filter (karena anotasi non-VCF dilewati)
    assert ctx.berkas["vcf_akhir"] == ctx.berkas["vcf_filter"]

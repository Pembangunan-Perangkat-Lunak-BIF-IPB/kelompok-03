"""Test mandiri untuk WP-2: Stages qc_trimming, alignment, dan bam_processing.

Menggunakan data sintetis mini (referensi kecil + FASTQ sintetis).
Dapat dijalankan secara mandiri tanpa dependensi WP-1/WP-3/WP-4/WP-5.
"""
import gzip
import shutil
import subprocess
import tempfile
from pathlib import Path
import pytest

from app.pipeline.konteks import Konteks, TahapGagal
from app.pipeline.runner import Runner
from app.pipeline.stages import qc_trimming, alignment, bam_processing


def _tools_tersedia():
    tools = ["fastp", "samtools"]
    has_bwa = shutil.which("bwa-mem2") or shutil.which("bwa")
    return has_bwa and all(shutil.which(t) for t in tools)


@pytest.fixture
def mini_workdir():
    d = Path(tempfile.mkdtemp(prefix="wp2_test_"))
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def mini_dataset(mini_workdir):
    """Buat referensi mini dan pasangan reads FASTQ (paired & single)."""
    ref_path = mini_workdir / "mini_ref.fa"
    # Kromosom kecil 1000 bp
    seq = (
        "ACGTACGTACGTNNNNACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT"
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA"
        * 8
    )
    ref_path.write_text(f">chrMini\n{seq}\n", encoding="utf-8")

    # Siapkan indeks bwa / bwa-mem2 untuk referensi
    aligner = "bwa-mem2" if shutil.which("bwa-mem2") else "bwa"
    subprocess.run([aligner, "index", str(ref_path)], check=True, capture_output=True)

    # FASTQ 1
    r1_path = mini_workdir / "reads_R1.fastq.gz"
    with gzip.open(r1_path, "wt") as f:
        f.write("@read1/1\nACGTACGTACGTACGTACGTACGTACGTACGT\n+\nIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n")
        f.write("@read2/1\nGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n+\nIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n")

    # FASTQ 2 (paired)
    r2_path = mini_workdir / "reads_R2.fastq.gz"
    with gzip.open(r2_path, "wt") as f:
        f.write("@read1/2\nACGTACGTACGTACGTACGTACGTACGTACGT\n+\nIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n")
        f.write("@read2/2\nGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n+\nIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n")

    return {
        "ref": ref_path,
        "r1": r1_path,
        "r2": r2_path,
    }


@pytest.mark.skipif(not _tools_tersedia(), reason="Perangkat bioinformatika belum lengkap terpasang")
def test_wp2_pipeline_rantai_tahap(mini_workdir, mini_dataset):
    """Menguji alur penuh 3 tahap WP-2: QC -> Alignment -> BAM Processing."""
    kerja = mini_workdir / "run"
    kerja.mkdir()

    ctx = Konteks(
        id_analisis=999,
        id_sampel=101,
        nama_sampel="Sample_Uji-01",
        kerja=kerja,
        referensi=mini_dataset["ref"],
        anotasi=None,
        fastq_r1=mini_dataset["r1"],
        fastq_r2=mini_dataset["r2"],
        parameter={"kualitas_pemangkasan_min": 20},
        threads=2,
    )

    # 1. Tahap QC & Trimming
    sh_qc = Runner(ctx.id_analisis, "qc_trimming", ke_db=False)
    qc_trimming.jalankan(ctx, sh_qc)

    assert "reads_r1" in ctx.berkas
    assert ctx.berkas["reads_r1"].exists()
    assert "reads_r2" in ctx.berkas
    assert ctx.berkas["reads_r2"].exists()
    assert "fastp_json" in ctx.berkas
    assert "qc" in ctx.ringkasan
    assert ctx.ringkasan["qc"]["reads_sebelum"] >= 2

    # 2. Tahap Alignment
    sh_aln = Runner(ctx.id_analisis, "alignment", ke_db=False)
    alignment.jalankan(ctx, sh_aln)

    assert "bam_mentah" in ctx.berkas
    assert ctx.berkas["bam_mentah"].exists()
    assert ctx.berkas["bam_mentah"].stat().st_size > 0

    # 3. Tahap BAM Processing
    sh_bam = Runner(ctx.id_analisis, "bam_processing", ke_db=False)
    bam_processing.jalankan(ctx, sh_bam)

    assert "bam" in ctx.berkas
    assert ctx.berkas["bam"].exists()
    # Pastikan sorted.bam terindeks (.bai)
    bai = kerja / "sorted.bam.bai"
    bai_alt = kerja / "sorted.bai"
    assert bai.exists() or bai_alt.exists()

    # Pastikan flagstat dihasilkan
    assert "flagstat_txt" in ctx.berkas
    assert "alignment" in ctx.ringkasan
    assert ctx.ringkasan["alignment"]["total_reads"] > 0
    assert "mapped" in ctx.berkas["flagstat_txt"]


@pytest.mark.skipif(not _tools_tersedia(), reason="Perangkat bioinformatika belum lengkap terpasang")
def test_wp2_qc_single_end(mini_workdir, mini_dataset):
    """Menguji bahwa mode single-end (fastq_r2=None) berjalan mulus."""
    kerja = mini_workdir / "run_se"
    kerja.mkdir()

    ctx = Konteks(
        id_analisis=998,
        id_sampel=102,
        nama_sampel="Sample_SE",
        kerja=kerja,
        referensi=mini_dataset["ref"],
        anotasi=None,
        fastq_r1=mini_dataset["r1"],
        fastq_r2=None,  # Single-end
        parameter={"kualitas_pemangkasan_min": 15},
        threads=1,
    )

    sh_qc = Runner(ctx.id_analisis, "qc_trimming", ke_db=False)
    qc_trimming.jalankan(ctx, sh_qc)

    assert "reads_r1" in ctx.berkas
    assert "reads_r2" not in ctx.berkas
    assert ctx.berkas["reads_r1"].exists()

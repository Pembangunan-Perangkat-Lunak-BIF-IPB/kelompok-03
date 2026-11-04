"""Tes Integrasi Pipeline Nyata (WP-5 Fattha, Tester).

Dilewati otomatis (gracefully skipped) jika perangkat bioinformatika (fastp, bwa, samtools, bcftools)
atau berkas data uji belum tersedia di sistem.
"""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline.konteks import Konteks, TahapGagal
from app.pipeline.runner import PERANGKAT_WAJIB, Runner
from app.pipeline.stages import alignment, anotasi, bam_processing, filtering, qc_trimming, variant_calling
from app.pipeline.vcfio import parse_vcf

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_UJI_DIR = REPO_ROOT / "data_uji"


def perangkat_lengkap() -> bool:
    """Memeriksa apakah semua tool bioinformatika terpasang."""
    return all(shutil.which(tool) is not None for tool in PERANGKAT_WAJIB)


def data_uji_ada() -> bool:
    """Memeriksa apakah berkas data uji mini telah dibuat."""
    return (
        DATA_UJI_DIR.exists()
        and (DATA_UJI_DIR / "ref.fa").exists()
        and (DATA_UJI_DIR / "sample_R1.fastq.gz").exists()
        and (DATA_UJI_DIR / "truth.vcf").exists()
    )


class TestPipelineNyata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not perangkat_lengkap():
            raise unittest.SkipTest("Perangkat bioinformatika (fastp/bwa/samtools/bcftools) belum terpasang di PATH.")
        if not data_uji_ada():
            raise unittest.SkipTest("Berkas data uji di 'data_uji/' belum dibuat. Jalankan 'python3 tools/buat_data_uji.py'.")

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.kerja = Path(self.tmp_dir)

        # Salin referensi ke folder kerja agar tidak memodifikasi data uji asli saat membuat indeks
        self.ref = self.kerja / "ref.fa"
        shutil.copy(DATA_UJI_DIR / "ref.fa", self.ref)

        self.r1 = DATA_UJI_DIR / "sample_R1.fastq.gz"
        self.r2 = DATA_UJI_DIR / "sample_R2.fastq.gz"
        self.anot = DATA_UJI_DIR / "anotasi_dbsnp.vcf.gz"

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_alur_lengkap_paired_end(self):
        """Uji alur nyata 6 tahap berurutan dari FASTQ ke VCF teranotasi."""
        ctx = Konteks(
            id_analisis=101,
            id_sampel=1,
            nama_sampel="Sampel_Uji_Nyata",
            kerja=self.kerja,
            referensi=self.ref,
            anotasi=self.anot,
            fastq_r1=self.r1,
            fastq_r2=self.r2,
            parameter={"kualitas_pemangkasan_min": 20, "kedalaman_min": 10, "qual_min": 30.0},
            threads=2,
        )

        sh = Runner(id_analisis=101, tahap="init")

        # 1. QC & Trimming
        sh.tahap = "qc_trimming"
        qc_trimming.jalankan(ctx, sh)
        self.assertIn("reads_r1", ctx.berkas)
        self.assertIn("reads_r2", ctx.berkas)

        # Buat indeks referensi untuk alignment
        sh.run(["bwa", "index", str(self.ref)])
        sh.run(["samtools", "faidx", str(self.ref)])

        # 2. Alignment
        sh.tahap = "alignment"
        alignment.jalankan(ctx, sh)
        self.assertIn("bam_mentah", ctx.berkas)

        # 3. BAM Processing
        sh.tahap = "bam_processing"
        bam_processing.jalankan(ctx, sh)
        self.assertIn("bam", ctx.berkas)
        self.assertIn("flagstat", ctx.berkas)

        # 4. Variant Calling
        sh.tahap = "variant_calling"
        variant_calling.jalankan(ctx, sh)
        self.assertIn("vcf_mentah", ctx.berkas)

        # 5. Filtering
        sh.tahap = "filtering"
        filtering.jalankan(ctx, sh)
        self.assertIn("vcf_filter", ctx.berkas)

        # 6. Anotasi
        sh.tahap = "anotasi"
        anotasi.jalankan(ctx, sh)
        self.assertIn("vcf_akhir", ctx.berkas)

        # Verifikasi varian akhir
        varian = parse_vcf(ctx.berkas["vcf_akhir"])
        self.assertGreater(len(varian), 0, "Pipeline nyata harus mendeteksi varian pada data uji.")

    def test_gagal_jika_referensi_hilang(self):
        """Uji penanganan kegagalan jika referensi tidak ditemukan."""
        ctx = Konteks(
            id_analisis=102,
            id_sampel=2,
            nama_sampel="Sampel_Fail",
            kerja=self.kerja,
            referensi=Path("/tidak/ada/ref.fa"),
            fastq_r1=self.r1,
        )
        sh = Runner(id_analisis=102, tahap="alignment")
        with self.assertRaises(TahapGagal):
            alignment.jalankan(ctx, sh)


if __name__ == "__main__":
    unittest.main()


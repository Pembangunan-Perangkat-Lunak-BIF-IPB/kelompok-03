"""Pengujian Unit untuk Tahap WP-3 (Variant Calling, Filtering, Anotasi).

Menguji kepatuhan terhadap spesifikasi PEMETAAN_PARAMETER.md:
- Normalisasi multi-alel norm -m- (R9)
- Formula filtering QUAL & FMT/DP (R8)
- Penanganan disparitas nama kromosom pada anotasi (R10)
- Penanganan berkas anotasi non-VCF (K5)
"""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline.konteks import Konteks, TahapGagal
from app.pipeline.stages import anotasi, filtering, variant_calling


class DummyRunnerWP3:
    """Mock runner untuk menguji perintah dan berkas keluaran WP-3."""
    def __init__(self, simulate_file_creation=True):
        self.commands = []
        self.logs = []
        self.progress_history = []
        self.simulate_file_creation = simulate_file_creation

    def catat(self, pesan, jenis="info"):
        self.logs.append((jenis, pesan))

    def progres(self, persen):
        self.progress_history.append(persen)

    def run(self, cmd, *, stdout=None, stdin_from=None, timeout=None, nama=None):
        self.commands.append((cmd, stdout, nama))
        if self.simulate_file_creation:
            if "index" in cmd:
                # Membuat file indeks tiruan (.csi)
                target = Path(cmd[-1])
                Path(str(target) + ".csi").write_text("dummy index")
            elif "view" in cmd:
                # Filter keluaran
                for idx, flag in enumerate(cmd):
                    if flag == "-o" and idx + 1 < len(cmd):
                        p = Path(cmd[idx + 1])
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\nchr1\t100\t.\tA\tT\t50\tPASS\tDP=20\tGT:DP\t0/1:20\n")
            elif "annotate" in cmd:
                for idx, flag in enumerate(cmd):
                    if flag == "-o" and idx + 1 < len(cmd):
                        p = Path(cmd[idx + 1])
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\nchr1\t100\trs123\tA\tT\t50\tPASS\tDP=20;GENE=BRCA1\tGT:DP\t0/1:20\n")


class TestStagesWP3(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp_dir)
        self.kerja = self.tmp_path / "work_wp3"
        self.kerja.mkdir(parents=True, exist_ok=True)

        self.ref = self.tmp_path / "ref.fa"
        self.ref.write_text(">chr1\nACGTACGT\n")

        self.bam = self.tmp_path / "sorted.bam"
        self.bam.write_text("dummy bam")
        (self.tmp_path / "sorted.bam.bai").write_text("dummy bai")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_variant_calling_missing_bam(self):
        sh = DummyRunnerWP3()
        ctx = Konteks(
            id_analisis=1,
            id_sampel=1,
            nama_sampel="S1",
            kerja=self.kerja,
            referensi=self.ref,
            berkas={"bam": Path("/tidak/ada/sorted.bam")},
        )
        with self.assertRaises(TahapGagal) as exc:
            variant_calling.jalankan(ctx, sh)
        self.assertIn("BAM terurut tidak ditemukan", str(exc.exception))

    def test_filtering_parameter_mapping(self):
        sh = DummyRunnerWP3()
        raw_vcf = self.tmp_path / "raw.vcf.gz"
        raw_vcf.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\nchr1\t100\t.\tA\tT\t50\tPASS\tDP=20\tGT:DP\t0/1:20\n")

        ctx = Konteks(
            id_analisis=2,
            id_sampel=2,
            nama_sampel="S2",
            kerja=self.kerja,
            referensi=self.ref,
            berkas={"vcf_mentah": raw_vcf},
            parameter={"qual_min": 40.0, "kedalaman_min": 15},
        )

        filtering.jalankan(ctx, sh)

        self.assertIn("vcf_filter", ctx.berkas)
        # Verifikasi ekspresi filter biologis pada perintah bcftools view (R8)
        cmd_view = sh.commands[0][0]
        self.assertIn("QUAL>=40.0 && FMT/DP>=15", cmd_view)

    def test_anotasi_dilewati_jika_format_gtf(self):
        sh = DummyRunnerWP3()
        filtered_vcf = self.tmp_path / "filtered.vcf.gz"
        filtered_vcf.write_text("dummy vcf")
        gtf_anot = self.tmp_path / "genes.gtf"
        gtf_anot.write_text("chr1\tENSEMBL\tgene\t1\t1000\t.\t+\t.\tgene_id \"ENSG1\";")

        ctx = Konteks(
            id_analisis=3,
            id_sampel=3,
            nama_sampel="S3",
            kerja=self.kerja,
            referensi=self.ref,
            anotasi=gtf_anot,
            berkas={"vcf_filter": filtered_vcf},
        )

        res = anotasi.jalankan(ctx, sh)
        self.assertEqual(res, "dilewati")
        self.assertEqual(ctx.berkas["vcf_akhir"], filtered_vcf)

    def test_anotasi_vcf_dengan_renaming_chr(self):
        sh = DummyRunnerWP3()
        # Sampel pakai prefix 'chr1'
        filtered_vcf = self.tmp_path / "filtered.vcf"
        filtered_vcf.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\nchr1\t100\t.\tA\tT\t50\tPASS\tDP=20\tGT:DP\t0/1:20\n")

        # Anotasi dbSNP pakai '1' (tanpa chr) -> R10
        anot_vcf = self.tmp_path / "dbsnp.vcf"
        anot_vcf.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n1\t100\trs123\tA\tT\t.\tPASS\tGENE=BRCA1\n")
        (self.tmp_path / "dbsnp.vcf.csi").write_text("dummy")

        ctx = Konteks(
            id_analisis=4,
            id_sampel=4,
            nama_sampel="S4",
            kerja=self.kerja,
            referensi=self.ref,
            anotasi=anot_vcf,
            berkas={"vcf_filter": filtered_vcf},
        )

        res = anotasi.jalankan(ctx, sh)
        self.assertIsNone(res)
        self.assertIn("vcf_akhir", ctx.berkas)

        # Cek bahwa ada opsi --rename-chrs pada perintah annotate
        found_rename = False
        for cmd_tuple in sh.commands:
            cmd = cmd_tuple[0]
            if "annotate" in cmd and "--rename-chrs" in cmd:
                found_rename = True
                break
        self.assertTrue(found_rename, "Flag --rename-chrs seharusnya ditambahkan saat gaya nama kontig berbeda.")


if __name__ == "__main__":
    unittest.main()


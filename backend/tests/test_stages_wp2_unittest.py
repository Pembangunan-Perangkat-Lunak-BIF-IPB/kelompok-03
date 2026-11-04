"""Pengujian mandiri menggunakan unittest standard library untuk menguji tahap WP-2."""
import unittest
from pathlib import Path
import tempfile
import sys
import shutil
import importlib.util

# Impor langsung dari direktori modul pipeline
PIPELINE_DIR = Path(__file__).resolve().parent.parent / "app" / "pipeline"


def _import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


konteks_mod = _import_module_from_path("konteks", PIPELINE_DIR / "konteks.py")
Konteks = konteks_mod.Konteks
TahapGagal = konteks_mod.TahapGagal

qc_trimming = _import_module_from_path("qc_trimming", PIPELINE_DIR / "stages" / "qc_trimming.py")
alignment = _import_module_from_path("alignment", PIPELINE_DIR / "stages" / "alignment.py")
bam_processing = _import_module_from_path("bam_processing", PIPELINE_DIR / "stages" / "bam_processing.py")


class DummyRunner:
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
            if cmd[0] == "fastp":
                for idx, flag in enumerate(cmd):
                    if flag in ("-o", "-O", "-j", "-h") and idx + 1 < len(cmd):
                        p = Path(cmd[idx + 1])
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_text("dummy fastp output")
            elif cmd[0] == "samtools":
                if cmd[1] == "sort":
                    for idx, flag in enumerate(cmd):
                        if flag == "-o" and idx + 1 < len(cmd):
                            p = Path(cmd[idx + 1])
                            p.parent.mkdir(parents=True, exist_ok=True)
                            p.write_text("dummy sorted bam")
                elif cmd[1] == "index":
                    bam_path = Path(cmd[2])
                    Path(str(bam_path) + ".bai").write_text("dummy bai index")
                elif cmd[1] == "flagstat" and stdout:
                    Path(stdout).write_text("100 + 0 in total\n80 + 0 mapped (80.00%)\n")

    def run_pipe(self, cmd1, cmd2, *, nama=None):
        self.commands.append((("PIPE", cmd1, cmd2), None, nama))
        if self.simulate_file_creation:
            for idx, flag in enumerate(cmd2):
                if flag == "-o" and idx + 1 < len(cmd2):
                    p = Path(cmd2[idx + 1])
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text("dummy raw bam")


class TestStagesWP2(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp_dir)
        self.kerja = self.tmp_path / "work_1"
        self.kerja.mkdir(parents=True, exist_ok=True)
        self.ref = self.tmp_path / "ref.fasta"
        self.ref.write_text(">chr1\nACGTACGT\n")
        self.r1 = self.tmp_path / "sample_R1.fastq.gz"
        self.r1.write_text("@r1\nACGT\n+\nIIII\n")
        self.r2 = self.tmp_path / "sample_R2.fastq.gz"
        self.r2.write_text("@r2\nACGT\n+\nIIII\n")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_qc_trimming_paired_end(self):
        sh = DummyRunner()
        ctx = Konteks(
            id_analisis=1,
            id_sampel=101,
            nama_sampel="Sampel Uji paired",
            kerja=self.kerja,
            referensi=self.ref,
            fastq_r1=self.r1,
            fastq_r2=self.r2,
            parameter={"kualitas_pemangkasan_min": 25},
            threads=4
        )

        qc_trimming.jalankan(ctx, sh)

        self.assertIn("reads_r1", ctx.berkas)
        self.assertIn("reads_r2", ctx.berkas)
        self.assertIn("fastp_json", ctx.berkas)
        self.assertTrue(ctx.berkas["reads_r1"].exists())
        self.assertTrue(ctx.berkas["reads_r2"].exists())

        fastp_cmd = sh.commands[0][0]
        self.assertIn("--cut_right", fastp_cmd)
        self.assertIn("--cut_right_mean_quality", fastp_cmd)
        self.assertIn("25", fastp_cmd)

    def test_qc_trimming_single_end(self):
        sh = DummyRunner()
        ctx = Konteks(
            id_analisis=2,
            id_sampel=102,
            nama_sampel="Sampel Uji single",
            kerja=self.kerja,
            referensi=self.ref,
            fastq_r1=self.r1,
            fastq_r2=None,
            parameter={"kualitas_pemangkasan_min": 20},
            threads=2
        )

        qc_trimming.jalankan(ctx, sh)

        self.assertIn("reads_r1", ctx.berkas)
        self.assertNotIn("reads_r2", ctx.berkas)
        self.assertTrue(ctx.berkas["reads_r1"].exists())

    def test_qc_trimming_file_not_found(self):
        sh = DummyRunner()
        ctx = Konteks(
            id_analisis=3,
            id_sampel=103,
            nama_sampel="Sampel Hilang",
            kerja=self.kerja,
            referensi=self.ref,
            fastq_r1=Path("/path/tidak/ada/r1.fastq.gz"),
            fastq_r2=None
        )

        with self.assertRaises(TahapGagal):
            qc_trimming.jalankan(ctx, sh)

    def test_alignment_with_rg_sanitization(self):
        sh = DummyRunner()
        ctx = Konteks(
            id_analisis=4,
            id_sampel=104,
            nama_sampel="Sampel Bahaya\tTab Spasi;Drop",
            kerja=self.kerja,
            referensi=self.ref,
            fastq_r1=self.r1,
            threads=2,
            berkas={"reads_r1": self.r1}
        )

        alignment.jalankan(ctx, sh)

        self.assertIn("bam_mentah", ctx.berkas)
        pipe_entry = sh.commands[0][0]
        self.assertEqual(pipe_entry[0], "PIPE")
        cmd_bwa = pipe_entry[1]
        self.assertIn("-R", cmd_bwa)
        rg_idx = cmd_bwa.index("-R") + 1
        rg_str = cmd_bwa[rg_idx]
        self.assertNotIn("\tTab", rg_str)
        self.assertIn("Sampel_Bahaya_Tab_Spasi_Drop", rg_str)

    def test_bam_processing_sort_index_flagstat(self):
        sh = DummyRunner()
        raw_bam = self.kerja / "dummy_raw.bam"
        raw_bam.write_text("raw bam content")

        ctx = Konteks(
            id_analisis=5,
            id_sampel=105,
            nama_sampel="Sampel Uji",
            kerja=self.kerja,
            referensi=self.ref,
            threads=2,
            berkas={"bam_mentah": raw_bam}
        )

        bam_processing.jalankan(ctx, sh)

        self.assertIn("bam", ctx.berkas)
        self.assertIn("flagstat", ctx.berkas)
        self.assertEqual(ctx.berkas["bam"].name, "sorted.bam")
        self.assertEqual(ctx.berkas["flagstat"].name, "flagstat.txt")
        self.assertTrue(ctx.berkas["flagstat"].exists())


if __name__ == "__main__":
    unittest.main()

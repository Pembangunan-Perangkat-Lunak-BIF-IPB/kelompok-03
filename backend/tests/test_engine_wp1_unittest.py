"""Pengujian Unit untuk Paket WP-1 (Runner, Preflight, Versioning, dan Reference Indexing).

Menguji:
1. Runner.run berhasil (perintah standar)
2. Runner.run gagal dengan exit code != 0 melempar TahapGagal
3. Runner.run timeout melempar TahapGagal
4. Runner.run_pipe menjalankan pipa dua perintah
5. Preflight menolak analisis jika tool atau berkas referensi hilang
6. Versi perangkat menghasilkan status perangkat bioinformatika
"""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

# Tambahkan backend ke path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline.konteks import TahapGagal
from app.pipeline.runner import (
    Runner,
    cek_perangkat_terpasang,
    preflight_pipeline,
    versi_perangkat,
)


class MockDBRunner(Runner):
    """Runner dengan pencatatan DB disimulasikan di memori."""
    def __init__(self, id_analisis=1, tahap="test", base_progres=0, span_progres=20):
        super().__init__(id_analisis, tahap, base_progres, span_progres)
        self.logs = []
        self.progres_vals = []

    def catat(self, pesan: str, jenis: str = "info") -> None:
        self.logs.append((jenis, pesan))

    def progres(self, persen_dalam_tahap: int) -> None:
        p_global = min(99, int(self.base_progres + (persen_dalam_tahap / 100.0) * self.span_progres))
        self.progres_vals.append(p_global)


class TestEngineWP1(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_runner_run_sukses(self):
        r = MockDBRunner()
        out_file = self.tmp_path / "out.txt"
        res = r.run(["python3", "-c", "print('hello_pipeline')"], stdout=out_file)
        self.assertEqual(res.returncode, 0)
        self.assertTrue(out_file.exists())
        self.assertIn("hello_pipeline", out_file.read_text())

    def test_runner_run_gagal_exit_code(self):
        r = MockDBRunner()
        with self.assertRaises(TahapGagal) as ctx:
            r.run(["python3", "-c", "import sys; sys.stderr.write('pesan error'); sys.exit(2)"])
        self.assertIn("kode kesalahan 2", str(ctx.exception))
        self.assertIn("pesan error", str(ctx.exception))

    def test_runner_run_timeout(self):
        r = MockDBRunner()
        with self.assertRaises(TahapGagal) as ctx:
            r.run(["python3", "-c", "import time; time.sleep(5)"], timeout=1)
        self.assertIn("melebihi batas waktu", str(ctx.exception))

    def test_runner_run_pipe(self):
        r = MockDBRunner()
        c1 = ["python3", "-c", "print('baris1\\nbaris2\\nbaris3')"]
        c2 = ["grep", "baris2"]
        r.run_pipe(c1, c2, timeout=5)
        # Jika lolos tanpa raise TahapGagal, pipa berhasil

    def test_runner_tool_tidak_ada(self):
        r = MockDBRunner()
        with self.assertRaises(TahapGagal) as ctx:
            r.run(["perangkat_palsu_xyz", "--version"])
        self.assertIn("tidak terpasang", str(ctx.exception))

    def test_preflight_gagal_jika_berkas_referensi_hilang(self):
        analisis_dummy = {
            "referensi": {"nama_referensi": "GRCh38.fa", "lokasi_berkas": "references/99/ref.fa"},
            "sampel": {"lokasi_fastq_r1": "samples/99/r1.fq.gz"},
        }
        kendala = preflight_pipeline(analisis_dummy, self.tmp_path)
        # File referensi dan FASTQ belum dibuat di tmp_path
        self.assertTrue(any("tidak ditemukan" in k for k in kendala))

    def test_versi_perangkat(self):
        v = versi_perangkat()
        self.assertIn("fastp", v)
        self.assertIn("bwa", v)
        self.assertIn("samtools", v)
        self.assertIn("bcftools", v)


if __name__ == "__main__":
    unittest.main()


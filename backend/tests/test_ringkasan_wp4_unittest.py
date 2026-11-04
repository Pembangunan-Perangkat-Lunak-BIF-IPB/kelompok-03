"""Pengujian Unit untuk Parser Ringkasan QC (FR-14) dan Alignment (FR-15) - WP-4 Abid."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline.ringkasan import ringkasan_alignment, ringkasan_qc

SAMPLE_FASTP_JSON = """{
  "summary": {
    "before_filtering": {
      "total_reads": 250000,
      "total_bases": 37500000,
      "q20_rate": 0.9850,
      "q30_rate": 0.9425
    },
    "after_filtering": {
      "total_reads": 246500,
      "total_bases": 36900000,
      "q20_rate": 0.9950,
      "q30_rate": 0.9810
    }
  }
}"""

SAMPLE_FLAGSTAT_TEXT = """250000 + 0 in total (QC-passed reads + QC-failed reads)
0 + 0 secondary
0 + 0 supplementary
0 + 0 duplicates
242500 + 0 mapped (97.00% : N/A)
250000 + 0 paired in sequencing
125000 + 0 read1
125000 + 0 read2
238000 + 0 properly paired (95.20% : N/A)
"""


class TestRingkasanWP4(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_ringkasan_qc_dari_file(self):
        json_file = self.tmp_path / "fastp.json"
        json_file.write_text(SAMPLE_FASTP_JSON, encoding="utf-8")

        res = ringkasan_qc(json_file)
        self.assertEqual(res["reads_sebelum"], 250000)
        self.assertEqual(res["reads_sesudah"], 246500)
        self.assertAlmostEqual(res["q30_sebelum"], 94.25, places=2)
        self.assertAlmostEqual(res["q30_sesudah"], 98.10, places=2)

    def test_ringkasan_qc_fallback_jika_kosong(self):
        res = ringkasan_qc("{}")
        self.assertEqual(res["reads_sebelum"], 0)
        self.assertEqual(res["reads_sesudah"], 0)
        self.assertEqual(res["q30_sebelum"], 0.0)

    def test_ringkasan_alignment_dari_teks(self):
        res = ringkasan_alignment(SAMPLE_FLAGSTAT_TEXT)
        self.assertEqual(res["total_reads"], 250000)
        self.assertEqual(res["reads_teralign"], 242500)
        self.assertAlmostEqual(res["persen_teralign"], 97.00, places=2)

    def test_ringkasan_alignment_dari_file(self):
        flagstat_file = self.tmp_path / "flagstat.txt"
        flagstat_file.write_text(SAMPLE_FLAGSTAT_TEXT, encoding="utf-8")

        res = ringkasan_alignment(flagstat_file)
        self.assertEqual(res["total_reads"], 250000)
        self.assertEqual(res["reads_teralign"], 242500)
        self.assertAlmostEqual(res["persen_teralign"], 97.00, places=2)


if __name__ == "__main__":
    unittest.main()


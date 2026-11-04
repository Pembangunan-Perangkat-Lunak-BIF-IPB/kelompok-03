"""Definisi dataclass Konteks dan exception TahapGagal sesuai Kontrak Antarmodul Bagian 3."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


class TahapGagal(Exception):
    """Dilempar saat eksekusi tahap gagal atau terjadi pelanggaran prasyarat."""
    pass


@dataclass
class Konteks:
    id_analisis: int
    id_sampel: int
    nama_sampel: str
    kerja: Path                          # folder kerja sementara milik analisis ini
    referensi: Path                      # FASTA genom
    anotasi: Optional[Path] = None       # VCF anotasi (opsional)
    fastq_r1: Path = Path()
    fastq_r2: Optional[Path] = None      # None jika single-end
    parameter: dict = field(default_factory=dict)  # kualitas_pemangkasan_min, kedalaman_min, qual_min
    threads: int = 2
    berkas: dict = field(default_factory=dict)     # keluaran antar tahap
    ringkasan: dict = field(default_factory=dict)  # ringkasan per tahap (FR-14, FR-15)


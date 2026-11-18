"""Konteks eksekusi pipeline dan definisi exception (WP-1 / Rakazaki).

Sesuai Kontrak Antarmodul Bagian 3.2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class TahapGagal(Exception):
    """Tahap pipeline gagal; pesan kesalahan berbahasa Indonesia ditampilkan ke pengguna."""
    pass


@dataclass
class Konteks:
    """Dataclass konteks data analisis yang diteruskan ke setiap tahap pipeline."""
    id_analisis: int
    id_sampel:   int
    nama_sampel: str
    kerja:       Path                 # folder kerja sementara milik analisis ini
    referensi:   Path                 # FASTA genom referensi
    anotasi:     Path | None          # berkas anotasi VCF; None jika dilewati
    fastq_r1:    Path                 # FASTQ R1
    fastq_r2:    Path | None          # FASTQ R2 (None jika single-end)
    parameter:   dict                 # kualitas_pemangkasan_min, kedalaman_min, qual_min
    threads:     int = 4
    berkas:      dict = field(default_factory=dict)   # keluaran antar tahap (kunci baku Bagian 3.3)
    ringkasan:   dict = field(default_factory=dict)   # ringkasan per tahap (FR-14, FR-15)

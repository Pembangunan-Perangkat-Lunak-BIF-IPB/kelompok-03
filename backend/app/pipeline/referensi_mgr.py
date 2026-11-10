"""Manajer Pengindeksan Referensi (WP-1 / Rakazaki).

Memastikan indeks BWA (bwa-mem2 / bwa) dan samtools faidx dibuat SEKALI per referensi
dengan proteksi kunci threading untuk mencegah race condition (Risiko R2).
"""
from __future__ import annotations

import shutil
import threading
from pathlib import Path

from .konteks import TahapGagal
from .runner import Runner

_locks: dict[str, threading.Lock] = {}
_global_lock = threading.Lock()


def _get_ref_lock(ref_path: Path) -> threading.Lock:
    """Ambil atau buat lock khusus untuk path referensi ini."""
    key = str(ref_path.resolve())
    with _global_lock:
        if key not in _locks:
            _locks[key] = threading.Lock()
        return _locks[key]


def pastikan_indeks_referensi(ref_path: Path, sh: Runner | None = None) -> None:
    """Pastikan indeks bwa/bwa-mem2 dan samtools faidx tersedia untuk referensi."""
    if not ref_path.exists():
        raise TahapGagal(f"Berkas referensi tidak ditemukan: {ref_path.name}")

    if ref_path.name.lower().endswith((".gz", ".bgz")):
        raise TahapGagal(
            f"Referensi FASTA terkompresi ({ref_path.name}) belum didukung. "
            "Gunakan berkas FASTA (.fa / .fasta) yang tidak terkompresi."
        )

    lock = _get_ref_lock(ref_path)
    with lock:
        # 1. samtools faidx
        fai = Path(str(ref_path) + ".fai")
        if not fai.exists():
            if sh:
                sh.catat(f"Membuat indeks samtools faidx untuk {ref_path.name}...")
            cmd = ["samtools", "faidx", str(ref_path)]
            if sh:
                sh.run(cmd, nama="samtools faidx")
            else:
                import subprocess
                subprocess.run(cmd, check=True)

        # 2. bwa / bwa-mem2 index
        # Format index bwa-mem2: .bwt.2bit.64 (atau 0.122)
        # Format index bwa biasa: .bwt
        p_bwt = Path(str(ref_path) + ".bwt")
        p_bwt_2bit = Path(str(ref_path) + ".bwt.2bit.64")
        p_0123 = Path(str(ref_path) + ".0123")

        aligner = "bwa-mem2" if shutil.which("bwa-mem2") else "bwa"
        perlu_index = False
        if aligner == "bwa-mem2" and not (p_bwt_2bit.exists() or p_0123.exists()):
            perlu_index = True
        elif aligner == "bwa" and not p_bwt.exists():
            perlu_index = True

        if perlu_index:
            if sh:
                sh.catat(f"Membuat indeks {aligner} untuk referensi {ref_path.name}...")
            cmd = [aligner, "index", str(ref_path)]
            if sh:
                sh.run(cmd, nama=f"{aligner} index")
            else:
                import subprocess
                subprocess.run(cmd, check=True)

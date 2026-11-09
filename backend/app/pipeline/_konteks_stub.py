"""Stub sementara WP-2 — dipakai selama WP-1 (konteks.py + runner.py) belum merge.

JANGAN import file ini dari kode produksi.
Hapus file ini setelah WP-1 merge dan ganti import di stages/*.py.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class TahapGagal(Exception):
    """Tahap pipeline gagal; pesan ditampilkan ke pengguna (berbahasa Indonesia)."""


@dataclass
class Konteks:
    """Dataclass konteks pipeline — harus identik dengan konteks.py milik WP-1 (Bagian 3.2)."""
    id_analisis: int
    id_sampel:   int
    nama_sampel: str
    kerja:       Path          # folder kerja sementara milik analisis ini
    referensi:   Path          # FASTA genom (tidak terkompresi)
    anotasi:     Path | None   # berkas anotasi VCF; None = lewati tahap anotasi
    fastq_r1:    Path
    fastq_r2:    Path | None   # None = single-end
    parameter:   dict          # kualitas_pemangkasan_min, kedalaman_min, qual_min
    threads:     int = 4
    berkas:      dict = field(default_factory=dict)   # keluaran antar tahap (kunci baku 3.3)
    ringkasan:   dict = field(default_factory=dict)   # ringkasan per tahap (FR-14, FR-15)


class Runner:
    """Stub Runner sementara — WP-1 akan mengganti ini dengan implementasi penuh
    (log ke log_proses, batas laju, timeout, dukungan pipa antarperintah).

    Perbedaan dari Runner WP-1:
    - Tidak menulis ke basis data (hanya cetak ke stdout).
    - Tidak mengirim progres ke kolom analisis.
    - sh.run() hanya mendukung perintah tunggal (pipa dikerjakan inline di stages/).
    """

    def __init__(self, id_analisis: int, tahap: str, cetak_log: bool = True) -> None:
        self._id = id_analisis
        self._tahap = tahap
        self._cetak = cetak_log

    # --------------------------------------------------------------------- #
    # Antarmuka publik — harus cocok dengan kontrak Runner WP-1 (Bagian 3.2) #
    # --------------------------------------------------------------------- #

    def run(
        self,
        cmd: list,
        *,
        stdout: Path | None = None,
        stdin_from=None,
        timeout: int | None = None,
        nama: str = "",
    ) -> int:
        """Jalankan cmd; lempar TahapGagal jika gagal atau timeout."""
        label = nama or str(cmd[0])
        self.catat("$ " + " ".join(str(c) for c in cmd), jenis="berjalan")

        kw: dict = {}
        if timeout:
            kw["timeout"] = timeout
        if stdout:
            kw["stdout"] = open(stdout, "wb")
            kw["stderr"] = subprocess.PIPE
        else:
            kw["capture_output"] = True
        if stdin_from is not None:
            kw["stdin"] = stdin_from

        try:
            r = subprocess.run([str(c) for c in cmd], **kw)
        except FileNotFoundError:
            raise TahapGagal(
                f"Perangkat '{cmd[0]}' tidak ditemukan. "
                "Pastikan conda activate human-gvc sudah dijalankan."
            )
        except subprocess.TimeoutExpired:
            raise TahapGagal(f"{label} melebihi batas waktu ({timeout}s).")
        finally:
            if stdout and "stdout" in kw:
                kw["stdout"].close()

        if r.returncode != 0:
            stderr = ""
            if hasattr(r, "stderr") and r.stderr:
                raw = r.stderr
                stderr = raw.decode(errors="replace") if isinstance(raw, bytes) else raw
            raise TahapGagal(f"{label} gagal (kode {r.returncode}): {stderr[-400:]}")

        return r.returncode

    def catat(self, pesan: str, jenis: str = "info") -> None:
        """Catat pesan ke log (stub: hanya cetak)."""
        if self._cetak:
            print(f"[{jenis.upper()}][{self._tahap}] {pesan}")

    def progres(self, persen_dalam_tahap: int) -> None:
        """Perbarui progres dalam tahap saat ini (stub: hanya cetak)."""
        if self._cetak:
            print(f"[PROGRES][{self._tahap}] {persen_dalam_tahap}%")

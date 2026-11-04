"""Subprocess Runner, Logger, dan Preflight Checker (WP-1 Rakazaki).

Menyediakan:
- Runner: Eksekusi perintah aman dengan log bertahap, batas laju DB, piping, dan batas waktu (timeout).
- Preflight: Pemeriksaan perangkat bioinformatika & berkas sebelum analisis masuk antrean.
- Versi: Deteksi versi perkakas bioinformatika untuk GET /api/health.
"""
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Optional

try:
    from ..db import get_conn
except ImportError:
    get_conn = None

from .konteks import TahapGagal

PERANGKAT_WAJIB = ["fastp", "bwa", "samtools", "bcftools"]


def cek_perangkat_terpasang() -> dict[str, bool]:
    """Memeriksa status keberadaan perangkat di PATH sistem."""
    return {tool: (shutil.which(tool) is not None) for tool in PERANGKAT_WAJIB}


def versi_perangkat() -> dict[str, str]:
    """Mendapatkan versi ringkas dari setiap perangkat bioinformatika terpasang."""
    hasil = {}
    for tool in PERANGKAT_WAJIB:
        if not shutil.which(tool):
            hasil[tool] = "tidak terpasang"
            continue
        try:
            if tool == "bwa":
                # BWA tidak punya flag --version; jalankan bwa tanpa argumen dan baca stderr
                res = subprocess.run(["bwa"], capture_output=True, text=True, timeout=5)
                m = re.search(r"Version:\s*([0-9a-zA-Z.-]+)", res.stderr)
                hasil[tool] = m.group(1) if m else "terpasang"
            else:
                res = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=5)
                teks = (res.stdout or res.stderr).strip().splitlines()
                hasil[tool] = teks[0] if teks else "terpasang"
        except Exception:
            hasil[tool] = "terpasang"
    return hasil


def preflight_pipeline(a: dict, storage_dir: Path) -> list[str]:
    """Pemeriksaan pra-eksekusi (preflight) sebelum analisis masuk antrean.

    Mengembalikan daftar pesan kendala (kosong jika lolos preflight).
    """
    kendala = []
    # 1. Cek perangkat bioinformatika
    hilang = [tool for tool in PERANGKAT_WAJIB if not shutil.which(tool)]
    if hilang:
        kendala.append(f"Perangkat belum terpasang di server: {', '.join(hilang)}")

    # 2. Cek berkas referensi genom
    ref = a.get("referensi")
    if not ref:
        kendala.append("Genom referensi belum dipilih.")
    else:
        path_ref = storage_dir / ref["lokasi_berkas"]
        if not path_ref.exists():
            kendala.append(f"Berkas referensi '{ref.get('nama_referensi')}' tidak ditemukan di storage.")

    # 3. Cek berkas anotasi (bila dipilih)
    anot = a.get("anotasi")
    if anot:
        path_anot = storage_dir / anot["lokasi_berkas"]
        if not path_anot.exists():
            kendala.append(f"Berkas anotasi '{anot.get('nama_referensi')}' tidak ditemukan di storage.")

    # 4. Cek berkas FASTQ sampel
    s = a.get("sampel")
    if not s:
        kendala.append("Data sampel belum dipilih.")
    else:
        r1 = s.get("lokasi_fastq_r1")
        if not r1 or not (storage_dir / r1).exists():
            kendala.append("Berkas FASTQ R1 tidak ditemukan di storage.")
        r2 = s.get("lokasi_fastq_r2")
        if r2 and not (storage_dir / r2).exists():
            kendala.append("Berkas FASTQ R2 (paired-end) tidak ditemukan di storage.")

    return kendala


class Runner:
    """Pembungkus eksekusi perintah dengan streaming log, timeout, dan pelaporan progres."""

    def __init__(self, id_analisis: int, tahap: str, base_progres: int = 0, span_progres: int = 15):
        self.id_analisis = id_analisis
        self.tahap = tahap
        self.base_progres = base_progres
        self.span_progres = span_progres
        self._terakhir_catat = 0.0

    def catat(self, pesan: str, jenis: str = "info") -> None:
        """Menyimpan entri log ke tabel log_proses dengan pemotongan karakter aman."""
        if not get_conn:
            return
        try:
            with get_conn() as c:
                c.execute(
                    "INSERT INTO log_proses (id_analisis, tahap, jenis_pesan, pesan) VALUES (%s, %s, %s, %s)",
                    (self.id_analisis, self.tahap, jenis, str(pesan)[:2000]),
                )
        except Exception as e:
            print(f"[Runner Log Error] id_analisis={self.id_analisis}: {e}")

    def progres(self, persen_dalam_tahap: int) -> None:
        """Memperbarui nilai progres_persen global secara mulus di basis data."""
        p_tahap = max(0, min(100, persen_dalam_tahap))
        p_global = min(99, int(self.base_progres + (p_tahap / 100.0) * self.span_progres))
        if not get_conn:
            return
        try:
            with get_conn() as c:
                c.execute(
                    "UPDATE analisis SET progres_persen=%s WHERE id_analisis=%s",
                    (p_global, self.id_analisis),
                )
        except Exception as e:
            print(f"[Runner Progress Error] id_analisis={self.id_analisis}: {e}")

    def run(
        self,
        cmd: list,
        *,
        stdout: Optional[Path] = None,
        stdin_from: Optional[Path] = None,
        timeout: Optional[int] = 1800,
        nama: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """Menjalankan satu proses subprocess dengan batas waktu dan pencatatan log stderr."""
        str_cmd = [str(x) for x in cmd]
        label = nama or str_cmd[0]
        perintah_teks = " ".join(str_cmd)
        if len(perintah_teks) > 300:
            perintah_teks = perintah_teks[:300] + "..."
        self.catat(f"$ {perintah_teks}", jenis="berjalan")

        # Cek apakah executable tersedia
        if not shutil.which(str_cmd[0]):
            raise TahapGagal(f"Perangkat '{str_cmd[0]}' tidak terpasang di sistem.")

        out_dest = open(stdout, "w", encoding="utf-8") if stdout else subprocess.PIPE
        in_src = open(stdin_from, "r", encoding="utf-8") if stdin_from else None

        try:
            p = subprocess.Popen(
                str_cmd,
                stdin=in_src,
                stdout=out_dest,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                _, stderr = p.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                p.kill()
                p.communicate()
                raise TahapGagal(f"Perintah '{label}' melebihi batas waktu eksekusi ({timeout} detik).")
        finally:
            if stdout and hasattr(out_dest, "close"):
                out_dest.close()
            if in_src and hasattr(in_src, "close"):
                in_src.close()

        if p.returncode != 0:
            tail_err = (stderr or "").strip()[-500:]
            raise TahapGagal(f"{label} keluar dengan kode kesalahan {p.returncode}: {tail_err}")

        return subprocess.CompletedProcess(args=str_cmd, returncode=p.returncode, stderr=stderr)

    def run_pipe(
        self,
        cmd1: list,
        cmd2: list,
        *,
        timeout: Optional[int] = 1800,
        nama: Optional[str] = None,
    ) -> None:
        """Menjalankan saluran pipa (pipeline): cmd1 stdout dialirkan ke cmd2 stdin."""
        c1 = [str(x) for x in cmd1]
        c2 = [str(x) for x in cmd2]
        label = nama or f"{c1[0]}|{c2[0]}"

        self.catat(f"$ {' '.join(c1)[:150]} | {' '.join(c2)[:150]}", jenis="berjalan")

        for binary in (c1[0], c2[0]):
            if not shutil.which(binary):
                raise TahapGagal(f"Perangkat '{binary}' tidak terpasang di sistem.")

        p1 = subprocess.Popen(c1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p2 = subprocess.Popen(c2, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p1.stdout.close()  # Izinkan p1 menerima sinyal SIGPIPE jika p2 berhenti

        mulai = time.time()
        while True:
            r1 = p1.poll()
            r2 = p2.poll()
            if r1 is not None and r2 is not None:
                break
            if timeout and (time.time() - mulai) > timeout:
                p1.kill()
                p2.kill()
                raise TahapGagal(f"Saluran pipa '{label}' melebihi batas waktu ({timeout} detik).")
            time.sleep(0.5)

        err1 = p1.stderr.read().decode("utf-8", errors="replace") if p1.stderr else ""
        err2 = p2.stderr.read().decode("utf-8", errors="replace") if p2.stderr else ""
        if p1.stderr:
            p1.stderr.close()
        if p2.stderr:
            p2.stderr.close()
        if p2.stdout:
            p2.stdout.close()

        if p1.returncode != 0:
            raise TahapGagal(f"{c1[0]} dalam pipa gagal (kode {p1.returncode}): {err1[-400:]}")
        if p2.returncode != 0:
            raise TahapGagal(f"{c2[0]} dalam pipa gagal (kode {p2.returncode}): {err2[-400:]}")

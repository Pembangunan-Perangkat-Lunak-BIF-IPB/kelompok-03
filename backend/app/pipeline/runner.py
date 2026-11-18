"""Modul Runner: Eksekusi subprocess dengan penanganan log, timeout, dan progres (WP-1 / Rakazaki).

Sesuai Kontrak Antarmodul Bagian 3.2.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from app.db import get_conn
from .konteks import TahapGagal


class Runner:
    """Pembungkus eksekusi perintah dengan streaming log ke DB, timeout, dan progres bertahap."""

    def __init__(
        self,
        id_analisis: int,
        tahap: str,
        tahap_index: int = 0,
        total_tahap: int = 6,
        ke_db: bool = True,
    ) -> None:
        self.id_analisis = id_analisis
        self.tahap = tahap
        self.tahap_index = tahap_index
        self.total_tahap = max(1, total_tahap)
        self.ke_db = ke_db
        self._terakhir_catat = 0.0

    def catat(self, pesan: str, jenis: str = "info") -> None:
        """Simpan catatan ke tabel log_proses dan cetak ke konsol."""
        pesan_potong = pesan[:2000]
        if self.ke_db:
            try:
                with get_conn() as c:
                    c.execute(
                        "INSERT INTO log_proses (id_analisis, tahap, jenis_pesan, pesan) VALUES (%s, %s, %s, %s)",
                        (self.id_analisis, self.tahap, jenis, pesan_potong),
                    )
            except Exception:
                pass  # Jangan hentikan alur hanya karena kegagalan logging sementara
        else:
            print(f"[{jenis.upper()}][{self.tahap}] {pesan_potong}")

    def progres(self, persen_dalam_tahap: int) -> None:
        """Hitung dan perbarui progres kumulatif (0-99%) pada baris analisis."""
        persen_tahap = max(0, min(100, persen_dalam_tahap))
        kumulatif = int((self.tahap_index + (persen_tahap / 100.0)) / self.total_tahap * 100)
        kumulatif = min(99, max(0, kumulatif))

        if self.ke_db:
            try:
                with get_conn() as c:
                    c.execute(
                        "UPDATE analisis SET progres_persen=%s WHERE id_analisis=%s",
                        (kumulatif, self.id_analisis),
                    )
            except Exception:
                pass

    def run(
        self,
        cmd: list[Any],
        *,
        stdout: Path | None = None,
        stdin_from: Any = None,
        timeout: int | None = None,
        nama: str = "",
    ) -> int:
        """Jalankan perintah subprocess dengan batas waktu dan pencatatan log.

        Gagal -> raise TahapGagal('pesan jelas berbahasa Indonesia').
        """
        label = nama or str(cmd[0])
        str_cmd = [str(x) for x in cmd]
        self.catat(f"$ {' '.join(str_cmd)[:300]}", jenis="berjalan")

        kw: dict[str, Any] = {}
        if timeout:
            kw["timeout"] = timeout

        out_file = None
        if stdout:
            out_file = open(stdout, "wb")
            kw["stdout"] = out_file
            kw["stderr"] = subprocess.PIPE
        else:
            kw["capture_output"] = True

        if stdin_from is not None:
            kw["stdin"] = stdin_from

        try:
            r = subprocess.run(str_cmd, text=True if not stdout else False, **kw)
        except FileNotFoundError:
            raise TahapGagal(f"Perangkat '{cmd[0]}' tidak terpasang atau tidak ditemukan di PATH server.")
        except subprocess.TimeoutExpired:
            raise TahapGagal(f"Perintah '{label}' melebihi batas waktu eksekusi ({timeout} detik).")
        finally:
            if out_file:
                out_file.close()

        if r.returncode != 0:
            err_msg = ""
            if hasattr(r, "stderr") and r.stderr:
                raw_err = r.stderr
                err_msg = raw_err.decode(errors="replace") if isinstance(raw_err, bytes) else str(raw_err)
            potongan = err_msg.strip()[-400:]
            raise TahapGagal(f"{label} gagal dengan kode keluar {r.returncode}: {potongan}")

        return r.returncode

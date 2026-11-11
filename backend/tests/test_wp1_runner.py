"""Tes unit untuk Runner (WP-1 / Rakazaki).

Menguji:
1. Perintah sukses (echo).
2. Perintah gagal dengan exit code non-zero (raise TahapGagal dengan pesan jelas).
3. Perintah timeout (raise TahapGagal saat durasi terlewati).
4. Perangkat tidak ditemukan (raise TahapGagal).
5. Keluaran besar (tidak macet karena buffer overflow).
"""
import sys
import pytest
from pathlib import Path

from app.pipeline.konteks import TahapGagal
from app.pipeline.runner import Runner


def test_runner_sukses():
    runner = Runner(id_analisis=1, tahap="test", ke_db=False)
    # Perintah sederhana yang sukses
    rc = runner.run([sys.executable, "-c", "print('Antigravity Human GVC')"])
    assert rc == 0


def test_runner_gagal_exit_code():
    runner = Runner(id_analisis=1, tahap="test", ke_db=False)
    # Perintah dengan exit code != 0
    with pytest.raises(TahapGagal) as exc_info:
        runner.run([sys.executable, "-c", "import sys; sys.stderr.write('Error spesifik\\n'); sys.exit(2)"])
    assert "gagal dengan kode keluar 2" in str(exc_info.value)
    assert "Error spesifik" in str(exc_info.value)


def test_runner_timeout():
    runner = Runner(id_analisis=1, tahap="test", ke_db=False)
    # Perintah sleep melebihi timeout 1 detik
    with pytest.raises(TahapGagal) as exc_info:
        runner.run([sys.executable, "-c", "import time; time.sleep(5)"], timeout=1)
    assert "melebihi batas waktu" in str(exc_info.value)


def test_runner_command_not_found():
    runner = Runner(id_analisis=1, tahap="test", ke_db=False)
    with pytest.raises(TahapGagal) as exc_info:
        runner.run(["perangkat_palsu_yang_pasti_tidak_ada_xyz_123"])
    assert "tidak terpasang atau tidak ditemukan" in str(exc_info.value)


def test_runner_keluaran_besar():
    runner = Runner(id_analisis=1, tahap="test", ke_db=False)
    # Menghasilkan 10.000 baris output untuk memastikan streaming tidak deadlock
    cmd = [sys.executable, "-c", "for i in range(10000): print(f'baris output {i}')"]
    rc = runner.run(cmd)
    assert rc == 0

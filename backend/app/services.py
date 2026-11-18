"""Helper bersama: objek analisis lengkap, kepemilikan (BR-07), validasi parameter (BR-04), validasi FASTQ."""
import gzip, re, shutil
from pathlib import Path
from fastapi import HTTPException
from .config import PARAM_DEFAULT, PARAM_RANGE, STORAGE_DIR

FASTQ_EXT = re.compile(r"\.fastq(\.gz)?$", re.I)


def analisis_lengkap(conn, id_analisis: int) -> dict:
    a = conn.execute("SELECT * FROM analisis WHERE id_analisis=%s", (id_analisis,)).fetchone()
    if not a:
        return None
    one = lambda t, k, v: conn.execute(f"SELECT * FROM {t} WHERE {k}=%s", (v,)).fetchone() if v else None
    a["sampel"] = one("sampel", "id_sampel", a["id_sampel"])
    a["referensi"] = one("referensi", "id_referensi", a["id_referensi"])
    a["anotasi"] = one("referensi", "id_referensi", a["id_referensi_anotasi"])
    return a


def analisis_milik(conn, id_analisis: int, id_pengguna: int) -> dict:
    """404 jika tidak ada ATAU bukan milik pemanggil, atau sudah melewati masa retensi (BR-07, BR-08)."""
    a = conn.execute(
        """SELECT a.id_analisis FROM analisis a LEFT JOIN riwayat_analisis r USING (id_analisis)
           WHERE a.id_analisis=%s AND a.id_pengguna=%s
             AND (r.id_riwayat IS NULL OR r.tanggal + r.masa_retensi_hari * interval '1 day' >= now())""",
        (id_analisis, id_pengguna),
    ).fetchone()
    if not a:
        raise HTTPException(404, "Analisis tidak ditemukan atau bukan milik akun Anda.")
    return analisis_lengkap(conn, id_analisis)


def validasi_parameter(p: dict, dasar: dict | None = None) -> dict:
    """Gabungkan dengan nilai lama/default, tolak yang di luar rentang."""
    hasil = {**PARAM_DEFAULT, **(dasar or {})}
    for k, v in (p or {}).items():
        if k not in PARAM_RANGE:
            raise HTTPException(422, f"Parameter tidak dikenal: {k}.")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise HTTPException(422, f"Parameter {k} harus berupa angka.")
        lo, hi = PARAM_RANGE[k]
        if not lo <= v <= hi:
            raise HTTPException(422, f"Parameter {k} di luar rentang yang diizinkan ({lo} sampai {hi}).")
        hasil[k] = int(v) if float(v).is_integer() else v
    return hasil


def pasangan_fastq(nama: list[str]) -> list[int] | None:
    """Urutan indeks [R1, R2] jika dua nama berpasangan (mis. x_R1/x_R2, x_1/x_2), selain itu None (BR-03)."""
    def parse(n):
        m = re.match(r"^(.*?)[_.-]?(?:R)?([12])$", FASTQ_EXT.sub("", n), re.I)
        return (m.group(1), int(m.group(2))) if m else None
    a, b = parse(nama[0]), parse(nama[1])
    if not a or not b or a[0] != b[0] or a[1] == b[1]:
        return None
    return [0, 1] if a[1] == 1 else [1, 0]


def periksa_isi_fastq(path: Path, label: str) -> None:
    """Cek struktur FASTQ dasar: baris 1 '@', baris 3 '+', panjang urutan = panjang kualitas."""
    try:
        op = gzip.open if path.suffix.lower() == ".gz" else open
        with op(path, "rt", errors="strict") as f:
            baris = [f.readline().rstrip("\n") for _ in range(4)]
    except (OSError, EOFError, UnicodeDecodeError):
        raise HTTPException(422, f"Berkas {label} rusak atau bukan FASTQ{' (gzip tidak valid)' if path.suffix.lower() == '.gz' else ''}.")
    if not baris[0].startswith("@") or not baris[2].startswith("+") or len(baris[1]) != len(baris[3]) or not baris[1]:
        raise HTTPException(422, f"Isi berkas {label} bukan format FASTQ yang valid.")


def hapus_folder(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def simpan_stream(upload, tujuan: Path, batas_mb: int) -> int:
    """Salin UploadFile ke disk bertahap; hentikan jika melebihi batas."""
    total, batas = 0, batas_mb * 1024 * 1024
    with open(tujuan, "wb") as out:
        while chunk := upload.file.read(1024 * 1024):
            total += len(chunk)
            if total > batas:
                raise HTTPException(413, f"Ukuran berkas melebihi batas {batas_mb} MB.")
            out.write(chunk)
    return total


def rel(path: Path) -> str:
    return str(path.relative_to(STORAGE_DIR))

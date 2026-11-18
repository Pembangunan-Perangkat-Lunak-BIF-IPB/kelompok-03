"""Visualisasi distribusi hasil variant calling (FR-20): agregasi per kromosom, jenis varian, dan QUAL."""
from fastapi import APIRouter, Depends, HTTPException

from ..db import get_conn
from ..deps import pengguna_saat_ini
from ..services import analisis_milik

router = APIRouter(prefix="/api/analisis", tags=["distribusi"])
BIN = 10


def _urut_kromosom(nama: str):
    k = nama.lower().removeprefix("chr")
    return (0, int(k), "") if k.isdigit() else (1, 0, k)


@router.get("/{id_a}/distribusi")
def distribusi(id_a: int, u=Depends(pengguna_saat_ini)):
    with get_conn() as c:
        a = analisis_milik(c, id_a, u["id_pengguna"])
        if a.get("status") != "selesai":
            raise HTTPException(409, "Hasil belum tersedia: analisis belum selesai atau gagal.")
        krom = c.execute("SELECT kromosom nama, count(*) jumlah FROM varian WHERE id_analisis=%s GROUP BY kromosom", (id_a,)).fetchall()
        jenis = c.execute(
            """SELECT CASE WHEN length(ref)=1 AND length(alt)=1 THEN 'SNP'
                           WHEN length(alt)>length(ref) THEN 'Insersi'
                           WHEN length(alt)<length(ref) THEN 'Delesi'
                           ELSE 'Substitusi multi-basa' END nama, count(*) jumlah
               FROM varian WHERE id_analisis=%s GROUP BY 1 ORDER BY 2 DESC""", (id_a,)).fetchall()
        mm = c.execute("SELECT min(quality_score) lo, max(quality_score) hi FROM varian WHERE id_analisis=%s", (id_a,)).fetchone()
        qual = {"min": None, "max": None, "bin": []}
        if mm["lo"] is not None:
            lo, hi = float(mm["lo"]), float(mm["hi"])
            batas = (hi if hi > lo else lo + 1) + 0.001
            hit = {r["b"]: r["n"] for r in c.execute(
                "SELECT width_bucket(quality_score::float8, %s::float8, %s::float8, %s) b, count(*) n FROM varian WHERE id_analisis=%s GROUP BY b",
                (lo, batas, BIN, id_a)).fetchall()}
            lebar = (batas - lo) / BIN
            qual = {"min": lo, "max": hi, "bin": [
                {"dari": round(lo + i * lebar, 1), "sampai": round(lo + (i + 1) * lebar, 1), "jumlah": hit.get(i + 1, 0)} for i in range(BIN)]}
    krom.sort(key=lambda r: _urut_kromosom(r["nama"]))
    if len(krom) > 30:  # banyak kontig: tampilkan 30 terbanyak agar grafik tetap terbaca
        krom = sorted(sorted(krom, key=lambda r: -r["jumlah"])[:30], key=lambda r: _urut_kromosom(r["nama"]))
    return {"kromosom": krom, "jenis": jenis, "qual": qual}

"""Log aktivitas pengguna untuk administrator (FR-12, FR-7, NFR-3): lihat, saring, dan unduh CSV."""
import csv
import io
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from ..db import get_conn
from ..deps import hanya_admin

router = APIRouter(prefix="/api/log", tags=["log"])

DASAR = "FROM log_akses l JOIN pengguna p ON p.id_pengguna = l.id_pengguna"
PILIH = "SELECT l.id_log, l.waktu, p.nama, p.email, l.jenis_objek, l.id_objek, l.jenis_aksi " + DASAR


def _where(q: Optional[str], aksi: Optional[str], dari: Optional[date], sampai: Optional[date]):
    w, p = [], []
    if q:
        w.append("(p.email ILIKE %s OR p.nama ILIKE %s)")
        p += [f"%{q}%", f"%{q}%"]
    if aksi:
        w.append("l.jenis_aksi = %s")
        p.append(aksi)
    if dari:
        w.append("l.waktu >= %s::date")
        p.append(dari)
    if sampai:
        w.append("l.waktu < (%s::date + 1)")
        p.append(sampai)
    return (" WHERE " + " AND ".join(w)) if w else "", p


@router.get("")
def daftar(q: Optional[str] = None, aksi: Optional[str] = None, dari: Optional[date] = None,
           sampai: Optional[date] = None, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
           u=Depends(hanya_admin)):
    w, p = _where(q, aksi, dari, sampai)
    with get_conn() as c:
        total = c.execute(f"SELECT count(*) AS n {DASAR}{w}", p).fetchone()["n"]
        items = c.execute(f"{PILIH}{w} ORDER BY l.waktu DESC, l.id_log DESC LIMIT %s OFFSET %s",
                          p + [size, (page - 1) * size]).fetchall()
    return {"total": total, "items": items}


@router.get("/unduh")
def unduh(q: Optional[str] = None, aksi: Optional[str] = None, dari: Optional[date] = None,
          sampai: Optional[date] = None, u=Depends(hanya_admin)):
    w, p = _where(q, aksi, dari, sampai)
    with get_conn() as c:
        rows = c.execute(f"{PILIH}{w} ORDER BY l.waktu DESC, l.id_log DESC LIMIT 50000", p).fetchall()
    buf = io.StringIO()
    out = csv.writer(buf)
    out.writerow(["id_log", "waktu", "nama", "email", "aksi", "objek", "id_objek"])
    for r in rows:
        out.writerow([r["id_log"], r["waktu"].isoformat(sep=" ", timespec="seconds"), r["nama"], r["email"],
                      r["jenis_aksi"], r["jenis_objek"], r["id_objek"]])
    nama = f"log-aktivitas-{datetime.now():%Y%m%d-%H%M}.csv"
    return Response("\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nama}"'})

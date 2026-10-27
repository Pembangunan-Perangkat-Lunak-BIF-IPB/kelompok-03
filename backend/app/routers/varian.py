import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from ..db import get_conn
from ..deps import catat, pengguna_saat_ini

router = APIRouter(prefix="/api/varian", tags=["varian"])
KODE = "'SAMP-' || extract(year FROM s.dibuat_pada)::int || '-' || lpad(s.id_sampel::text, 3, '0')"   # kode tampilan SAMP-2026-001
DARI = """FROM varian v JOIN analisis a USING (id_analisis) JOIN sampel s ON s.id_sampel = a.id_sampel
          JOIN pengguna p ON p.id_pengguna = a.id_pengguna WHERE a.dipublikasikan"""


@router.get("")
def cari(q: str = "", kromosom: str = "", qual_min: Optional[str] = None, page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100),
         u=Depends(pengguna_saat_ini)):
    """UC-06: cari di basis data bersama (hanya analisis yang dipublikasikan, BR-06)."""
    w, p = "", []
    q = q.strip()
    if q:
        m = re.fullmatch(r"(chr\w+):(\d+)", q, re.I)
        if re.match(r"chr\w+:", q, re.I) and not m:
            raise HTTPException(422, "Format posisi tidak valid. Gunakan chr17:41196312.")   # UC-06 alt 1
        if m:
            w += " AND lower(v.kromosom)=lower(%s) AND v.posisi=%s"; p += [m.group(1), int(m.group(2))]
        else:
            like = f"%{q}%"
            w += f" AND (v.gen ILIKE %s OR {KODE} ILIKE %s OR s.nama_sampel ILIKE %s" + (" OR v.posisi=%s)" if q.isdigit() else ")")
            p += [like, like, like] + ([int(q)] if q.isdigit() else [])
    if kromosom:
        w += " AND v.kromosom=%s"; p.append(kromosom)
    if qual_min not in (None, ""):
        try:
            qm = float(qual_min)
        except ValueError:
            raise HTTPException(422, "Nilai QUAL minimum harus berupa angka.")
        if qm < 0:
            raise HTTPException(422, "Nilai QUAL minimum tidak boleh negatif.")
        w += " AND v.quality_score>=%s"; p.append(qm)
    with get_conn() as c:
        total = c.execute(f"SELECT count(*) n {DARI}{w}", p).fetchone()["n"]
        items = c.execute(
            f"""SELECT v.id_varian, v.id_analisis, s.id_sampel, s.dibuat_pada sampel_dibuat, s.nama_sampel, v.kromosom, v.posisi, v.ref, v.alt,
                       v.quality_score, v.gen, p.nama pengunggah {DARI}{w} ORDER BY v.id_analisis DESC, v.kromosom, v.posisi LIMIT %s OFFSET %s""",
            [*p, size, (page - 1) * size]).fetchall()
        catat(c, u["id_pengguna"], "varian", items[0]["id_varian"] if items else 0, "cari")
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/{id_varian}")
def detail(id_varian: int, u=Depends(pengguna_saat_ini)):
    with get_conn() as c:
        v = c.execute("SELECT v.*, a.dipublikasikan, a.id_pengguna pemilik, a.tanggal tanggal_analisis, a.parameter, a.id_sampel FROM varian v JOIN analisis a USING (id_analisis) WHERE v.id_varian=%s", (id_varian,)).fetchone()
        if not v or not (v["dipublikasikan"] or v["pemilik"] == u["id_pengguna"]):
            raise HTTPException(403, "Data varian tidak ada atau Anda tidak memiliki hak akses.")   # UC-06 alt 3
        v["genotipe"] = c.execute("SELECT * FROM genotipe WHERE id_varian=%s LIMIT 1", (id_varian,)).fetchone()
        v["sampel"] = c.execute("SELECT * FROM sampel WHERE id_sampel=%s", (v["id_sampel"],)).fetchone()
        v["pengunggah"] = c.execute("SELECT nama FROM pengguna WHERE id_pengguna=%s", (v["pemilik"],)).fetchone()["nama"]
        catat(c, u["id_pengguna"], "varian", id_varian, "lihat")
    return v

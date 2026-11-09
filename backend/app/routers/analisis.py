import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from .. import pipeline
from ..config import PARAM_DEFAULT, PIPELINE_MODE, STORAGE_DIR
from ..db import get_conn
from ..deps import catat, pengguna_saat_ini
from ..services import analisis_lengkap, analisis_milik, validasi_parameter

router = APIRouter(prefix="/api/analisis", tags=["analisis"])


class Konfigurasi(BaseModel):
    id_referensi: Optional[int] = None
    id_referensi_anotasi: Optional[int] = None
    parameter: Optional[dict] = None


@router.get("")
def riwayat(u=Depends(pengguna_saat_ini)):
    """FR-17 + BR-07 (hanya milik sendiri) + BR-08 (yang melewati retensi tidak ditampilkan)."""
    with get_conn() as c:
        ids = c.execute(
            """SELECT a.id_analisis FROM analisis a LEFT JOIN riwayat_analisis r USING (id_analisis)
               WHERE a.id_pengguna=%s AND (r.id_riwayat IS NULL OR r.tanggal + r.masa_retensi_hari * interval '1 day' >= now())
               ORDER BY a.id_analisis DESC""", (u["id_pengguna"],)).fetchall()
        return [analisis_lengkap(c, i["id_analisis"]) for i in ids]


@router.get("/{id_a}")
def detail(id_a: int, u=Depends(pengguna_saat_ini)):
    with get_conn() as c:
        a = analisis_milik(c, id_a, u["id_pengguna"])
        catat(c, u["id_pengguna"], "analisis", id_a, "lihat")
        return a


@router.patch("/{id_a}")
def simpan_konfigurasi(id_a: int, b: Konfigurasi, u=Depends(pengguna_saat_ini)):
    with get_conn() as c:
        a = analisis_milik(c, id_a, u["id_pengguna"])
        if a["terkunci"] or a["status"] != "draf":
            raise HTTPException(409, "Analisis yang sudah dijalankan tidak dapat diubah. Jalankan sebagai analisis baru.")   # BR-05
        kolom, nilai = [], []
        for field, jenis in (("id_referensi", "genom"), ("id_referensi_anotasi", "anotasi")):
            if field in b.model_fields_set:
                if b.__dict__[field] is not None:
                    r = c.execute("SELECT jenis FROM referensi WHERE id_referensi=%s", (b.__dict__[field],)).fetchone()
                    if not r or r["jenis"] != jenis:
                        raise HTTPException(422, f"Referensi tidak valid: bukan berkas {jenis}.")   # UC-02 alt 1
                kolom.append(f"{field}=%s"); nilai.append(b.__dict__[field])
        if b.parameter is not None:
            kolom.append("parameter=%s::jsonb"); nilai.append(json.dumps(validasi_parameter(b.parameter, a["parameter"])))
        if kolom:
            c.execute(f"UPDATE analisis SET {', '.join(kolom)} WHERE id_analisis=%s", [*nilai, id_a])
            catat(c, u["id_pengguna"], "analisis", id_a, "ubah")
        return analisis_lengkap(c, id_a)


@router.post("/{id_a}/jalankan")
def jalankan(id_a: int, u=Depends(pengguna_saat_ini)):
    with get_conn() as c:
        a = analisis_milik(c, id_a, u["id_pengguna"])
        if a["status"] != "draf":
            raise HTTPException(409, "Analisis sudah pernah dijalankan.")
        kurang = []
        if not a["id_sampel"]:
            kurang.append("data sekuens")
        if not a["id_referensi"]:
            kurang.append("genom referensi")   # BR-01
        if kurang:
            raise HTTPException(422, "Analisis belum dapat dijalankan. Belum lengkap: " + ", ".join(kurang) + ".")
        if PIPELINE_MODE == "nyata":
            for r in (a["referensi"], a["anotasi"]):
                if r and not (STORAGE_DIR / r["lokasi_berkas"]).exists():
                    raise HTTPException(422, f"Berkas referensi '{r['nama_referensi']}' belum tersedia di server.")
        c.execute("UPDATE analisis SET status='menunggu', progres_persen=0, tahap_saat_ini=NULL WHERE id_analisis=%s", (id_a,))
        c.execute("INSERT INTO log_proses (id_analisis,tahap,jenis_pesan,pesan) VALUES (%s,NULL,'info','Analisis masuk antrean.')", (id_a,))
        catat(c, u["id_pengguna"], "analisis", id_a, "jalankan")
        hasil = analisis_lengkap(c, id_a)
    pipeline.kirim(id_a)   # setelah commit, agar thread latar melihat status 'menunggu'
    return hasil


@router.get("/{id_a}/log")
def log(id_a: int, u=Depends(pengguna_saat_ini)):
    with get_conn() as c:
        analisis_milik(c, id_a, u["id_pengguna"])
        return c.execute("SELECT * FROM log_proses WHERE id_analisis=%s ORDER BY waktu, id_log_proses", (id_a,)).fetchall()


@router.post("/{id_a}/salin", status_code=201)
def salin(id_a: int, u=Depends(pengguna_saat_ini)):
    """BR-05: menjalankan ulang = analisis baru (draf) dengan sampel, referensi, dan parameter yang sama."""
    with get_conn() as c:
        a = analisis_milik(c, id_a, u["id_pengguna"])
        n = c.execute("INSERT INTO analisis (id_pengguna,id_sampel,id_referensi,id_referensi_anotasi,parameter) VALUES (%s,%s,%s,%s,%s::jsonb) RETURNING id_analisis",
                      (u["id_pengguna"], a["id_sampel"], a["id_referensi"], a["id_referensi_anotasi"], json.dumps(a["parameter"] or PARAM_DEFAULT))).fetchone()
        catat(c, u["id_pengguna"], "analisis", n["id_analisis"], "jalankan")
        return analisis_lengkap(c, n["id_analisis"])


def _selesai(a):
    if a["status"] != "selesai":
        raise HTTPException(409, "Hasil belum tersedia: analisis belum selesai atau gagal.")   # UC-05 alt 1-2


@router.get("/{id_a}/ringkasan")
def ringkasan(id_a: int, u=Depends(pengguna_saat_ini)):
    with get_conn() as c:
        _selesai(analisis_milik(c, id_a, u["id_pengguna"]))
        r = c.execute(
            """SELECT count(*) total,
                      count(*) FILTER (WHERE (ref='A' AND alt='G') OR (ref='G' AND alt='A') OR (ref='C' AND alt='T') OR (ref='T' AND alt='C')) ti,
                      avg(quality_score) qrata FROM varian WHERE id_analisis=%s""", (id_a,)).fetchone()
    tv = r["total"] - r["ti"]
    return {"total_varian": r["total"], "ti_tv": round(r["ti"] / tv, 2) if tv else None, "qual_rata2": round(float(r["qrata"]), 1) if r["qrata"] is not None else None}


@router.get("/{id_a}/varian")
def varian(id_a: int, page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=200), u=Depends(pengguna_saat_ini)):
    with get_conn() as c:
        _selesai(analisis_milik(c, id_a, u["id_pengguna"]))
        total = c.execute("SELECT count(*) n FROM varian WHERE id_analisis=%s", (id_a,)).fetchone()["n"]
        items = c.execute("SELECT * FROM varian WHERE id_analisis=%s ORDER BY kromosom, posisi LIMIT %s OFFSET %s", (id_a, size, (page - 1) * size)).fetchall()
    return {"total": total, "page": page, "size": size, "items": items}


@router.post("/{id_a}/kunci")
def kunci(id_a: int, u=Depends(pengguna_saat_ini)):
    with get_conn() as c:
        _selesai(analisis_milik(c, id_a, u["id_pengguna"]))   # FR-10 / BR-05: hanya yang selesai
        c.execute("UPDATE analisis SET terkunci=TRUE WHERE id_analisis=%s", (id_a,))
        catat(c, u["id_pengguna"], "analisis", id_a, "ubah")
        return analisis_lengkap(c, id_a)


@router.post("/{id_a}/publikasi")
def publikasi(id_a: int, u=Depends(pengguna_saat_ini)):
    with get_conn() as c:
        a = analisis_milik(c, id_a, u["id_pengguna"])
        if a["status"] != "selesai":
            raise HTTPException(409, "Analisis gagal atau belum selesai tidak dapat dipublikasikan.")   # BR-06
        c.execute("UPDATE analisis SET dipublikasikan=TRUE WHERE id_analisis=%s", (id_a,))
        catat(c, u["id_pengguna"], "analisis", id_a, "ubah")
        return analisis_lengkap(c, id_a)


@router.get("/{id_a}/unduh")
def unduh(id_a: int, format: str = Query("vcf", pattern="^(vcf|csv)$"), u=Depends(pengguna_saat_ini)):
    with get_conn() as c:
        a = analisis_milik(c, id_a, u["id_pengguna"])
        _selesai(a)
        rw = c.execute("SELECT lokasi_hasil_vcf, lokasi_hasil_csv FROM riwayat_analisis WHERE id_analisis=%s", (id_a,)).fetchone()
        rows = None
        path = STORAGE_DIR / (rw["lokasi_hasil_vcf" if format == "vcf" else "lokasi_hasil_csv"] or "_") if rw else None
        if not path or not path.exists():   # berkas hilang: bangun ulang dari database
            rows = c.execute("""SELECT v.*, g.genotipe gt, g.kedalaman dp, g.kualitas_genotipe gq FROM varian v LEFT JOIN genotipe g USING (id_varian)
                                WHERE v.id_analisis=%s ORDER BY kromosom, posisi""", (id_a,)).fetchall()
        catat(c, u["id_pengguna"], "analisis", id_a, "unduh")
    if rows is not None:
        isi = pipeline.bangun_vcf(rows, a["sampel"]["nama_sampel"]) if format == "vcf" else pipeline.bangun_csv(rows)
        return Response(isi, media_type="text/plain", headers={"Content-Disposition": f'attachment; filename="analisis-{id_a}.{format}"'})
    return FileResponse(path, media_type="text/plain", filename=f"analisis-{id_a}.{format}")

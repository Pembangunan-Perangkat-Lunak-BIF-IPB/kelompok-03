import re, uuid
from typing import Optional
import psycopg
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from ..config import MAX_REFERENSI_MB, STORAGE_DIR
from ..db import get_conn
from ..deps import catat, hanya_admin, pengguna_saat_ini
from ..services import rel, simpan_stream

router = APIRouter(prefix="/api/referensi", tags=["referensi"])
EXT = {"genom": re.compile(r"\.(fa|fasta|fna)(\.gz)?$", re.I), "anotasi": re.compile(r"\.(vcf|gtf|gff|gff3)(\.gz)?$", re.I)}
PESAN = {"genom": "Referensi genom harus berformat FASTA (.fa/.fasta).", "anotasi": "Berkas anotasi harus berformat .vcf, .gtf, atau .gff (boleh .gz)."}


@router.get("")
def daftar(jenis: Optional[str] = None, u=Depends(pengguna_saat_ini)):
    with get_conn() as c:
        if jenis in ("genom", "anotasi"):
            return c.execute("SELECT * FROM referensi WHERE jenis=%s ORDER BY status, id_referensi", (jenis,)).fetchall()
        return c.execute("SELECT * FROM referensi ORDER BY jenis, status, id_referensi").fetchall()


@router.post("", status_code=201)
def unggah(nama_referensi: str = Form(""), jenis: str = Form(...), berkas: UploadFile = File(...), u=Depends(pengguna_saat_ini)):
    if jenis not in EXT:
        raise HTTPException(422, "Jenis referensi harus 'genom' atau 'anotasi'.")
    if not EXT[jenis].search(berkas.filename or ""):
        raise HTTPException(422, PESAN[jenis])
    folder = STORAGE_DIR / "references" / uuid.uuid4().hex[:12]
    folder.mkdir(parents=True)
    tujuan = folder / re.sub(r"[^\w.\-]", "_", berkas.filename)
    try:
        if simpan_stream(berkas, tujuan, MAX_REFERENSI_MB) == 0:
            raise HTTPException(422, "Berkas referensi kosong.")
    except HTTPException:
        tujuan.unlink(missing_ok=True); folder.rmdir(); raise
    with get_conn() as c:
        r = c.execute("INSERT INTO referensi (nama_referensi,status,jenis,lokasi_berkas,id_pengunggah) VALUES (%s,'unggahan',%s,%s,%s) RETURNING *",
                      ((nama_referensi.strip() or berkas.filename)[:200], jenis, rel(tujuan), u["id_pengguna"])).fetchone()
        catat(c, u["id_pengguna"], "referensi", r["id_referensi"], "unggah")
    return r


@router.delete("/{id_referensi}", status_code=204)
def hapus(id_referensi: int, u=Depends(hanya_admin)):
    try:
        with get_conn() as c:
            r = c.execute("SELECT * FROM referensi WHERE id_referensi=%s", (id_referensi,)).fetchone()
            if not r:
                raise HTTPException(404, "Referensi tidak ditemukan.")
            pakai = c.execute("SELECT count(*) n FROM analisis WHERE id_referensi=%s OR id_referensi_anotasi=%s", (id_referensi, id_referensi)).fetchone()["n"]
            if pakai:
                raise HTTPException(409, f"Referensi masih dipakai oleh {pakai} analisis dan tidak dapat dihapus.")
            c.execute("DELETE FROM referensi WHERE id_referensi=%s", (id_referensi,))
            catat(c, u["id_pengguna"], "referensi", id_referensi, "hapus")
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(409, "Referensi masih dipakai dan tidak dapat dihapus.")
    if r["status"] == "unggahan":
        (STORAGE_DIR / r["lokasi_berkas"]).unlink(missing_ok=True)

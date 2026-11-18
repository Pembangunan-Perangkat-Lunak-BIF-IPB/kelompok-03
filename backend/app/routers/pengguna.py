import re
from typing import Optional
import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..db import get_conn
from ..deps import catat, hanya_admin

router = APIRouter(prefix="/api/pengguna", tags=["pengguna"])
KOLOM = "id_pengguna,nama,email,peran,aktif,email_terverifikasi,dibuat_pada"


class Akun(BaseModel):
    nama: str
    email: str
    password: Optional[str] = None
    peran: str = "peneliti"
    aktif: bool = True


def _cek(b: Akun, baru: bool):
    if not b.nama.strip():
        raise HTTPException(422, "Nama wajib diisi.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", b.email.strip()):
        raise HTTPException(422, "Format email tidak valid.")
    if b.peran not in ("peneliti", "administrator"):
        raise HTTPException(422, "Peran harus 'peneliti' atau 'administrator'.")
    if (baru or b.password) and len(b.password or "") < 8:
        raise HTTPException(422, "Kata sandi minimal 8 karakter.")


@router.get("")
def daftar(u=Depends(hanya_admin)):
    with get_conn() as c:
        return c.execute(f"SELECT {KOLOM} FROM pengguna ORDER BY id_pengguna").fetchall()


@router.post("", status_code=201)
def tambah(b: Akun, u=Depends(hanya_admin)):
    _cek(b, True)
    with get_conn() as c:
        if c.execute("SELECT 1 FROM pengguna WHERE lower(email)=lower(%s)", (b.email.strip(),)).fetchone():
            raise HTTPException(409, "Email sudah terdaftar.")
        r = c.execute(f"INSERT INTO pengguna (nama,email,password_hash,peran,email_terverifikasi) VALUES (%s,%s,crypt(%s, gen_salt('bf')),%s,TRUE) RETURNING {KOLOM}",
                      (b.nama.strip(), b.email.strip(), b.password, b.peran)).fetchone()
        catat(c, u["id_pengguna"], "akun", r["id_pengguna"], "ubah")
    return r


@router.patch("/{id_p}")
def ubah(id_p: int, b: Akun, u=Depends(hanya_admin)):
    _cek(b, False)
    if id_p == u["id_pengguna"] and (not b.aktif or b.peran != "administrator"):
        raise HTTPException(409, "Anda tidak dapat menonaktifkan atau menurunkan peran akun Anda sendiri.")
    with get_conn() as c:
        if c.execute("SELECT 1 FROM pengguna WHERE lower(email)=lower(%s) AND id_pengguna<>%s", (b.email.strip(), id_p)).fetchone():
            raise HTTPException(409, "Email sudah terdaftar.")
        sql = "UPDATE pengguna SET nama=%s,email=%s,peran=%s,aktif=%s" + (",password_hash=crypt(%s, gen_salt('bf'))" if b.password else "") + f" WHERE id_pengguna=%s RETURNING {KOLOM}"
        args = [b.nama.strip(), b.email.strip(), b.peran, b.aktif] + ([b.password] if b.password else []) + [id_p]
        r = c.execute(sql, args).fetchone()
        if not r:
            raise HTTPException(404, "Akun tidak ditemukan.")
        catat(c, u["id_pengguna"], "akun", id_p, "ubah")
    return r


@router.delete("/{id_p}", status_code=204)
def hapus(id_p: int, u=Depends(hanya_admin)):
    """Hapus akun yang belum terpakai (mis. pendaftar yang tak pernah verifikasi). Akun yang sudah punya data atau
    jejak akses tidak dihapus agar keterlacakan (log_akses, ON DELETE RESTRICT) terjaga; nonaktifkan saja."""
    if id_p == u["id_pengguna"]:
        raise HTTPException(409, "Anda tidak dapat menghapus akun Anda sendiri.")
    try:
        with get_conn() as c:
            if not c.execute("SELECT 1 FROM pengguna WHERE id_pengguna=%s", (id_p,)).fetchone():
                raise HTTPException(404, "Akun tidak ditemukan.")
            pakai = c.execute("""SELECT (SELECT count(*) FROM sampel WHERE id_pengguna=%s) + (SELECT count(*) FROM analisis WHERE id_pengguna=%s)
                                        + (SELECT count(*) FROM log_akses WHERE id_pengguna=%s) n""", (id_p, id_p, id_p)).fetchone()["n"]
            if pakai:
                raise HTTPException(409, "Akun sudah memiliki data atau riwayat akses sehingga tidak dapat dihapus. Nonaktifkan akun sebagai gantinya.")
            c.execute("DELETE FROM pengguna WHERE id_pengguna=%s", (id_p,))
            catat(c, u["id_pengguna"], "akun", id_p, "hapus")
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(409, "Akun masih terkait dengan data lain dan tidak dapat dihapus. Nonaktifkan akun sebagai gantinya.")

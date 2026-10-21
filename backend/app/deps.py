"""Dependency FastAPI: pengguna saat ini, pembatasan admin, pencatatan log akses (FR-13)."""
from fastapi import Depends, Header, HTTPException
from .db import get_conn
from .security import baca_token


def pengguna_saat_ini(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Sesi berakhir. Silakan masuk kembali.")
    uid = baca_token(authorization.split(" ", 1)[1])
    if not uid:
        raise HTTPException(401, "Sesi berakhir. Silakan masuk kembali.")
    with get_conn() as c:
        u = c.execute("SELECT id_pengguna,nama,email,peran,aktif FROM pengguna WHERE id_pengguna=%s", (uid,)).fetchone()
    if not u or not u["aktif"]:
        raise HTTPException(401, "Akun tidak aktif atau tidak ditemukan.")
    return u


def hanya_admin(u: dict = Depends(pengguna_saat_ini)) -> dict:
    if u["peran"] != "administrator":
        raise HTTPException(403, "Fitur ini hanya untuk administrator.")
    return u


def catat(conn, id_pengguna: int, jenis_objek: str, id_objek: int, jenis_aksi: str) -> None:
    """Tulis satu baris log_akses pada transaksi yang sedang berjalan."""
    conn.execute(
        "INSERT INTO log_akses (id_pengguna, jenis_objek, id_objek, jenis_aksi) VALUES (%s,%s,%s,%s)",
        (id_pengguna, jenis_objek, id_objek, jenis_aksi),
    )

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..db import get_conn
from ..deps import catat, pengguna_saat_ini
from ..security import buat_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Login(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(b: Login):
    with get_conn() as c:
        u = c.execute(
            "SELECT id_pengguna,nama,email,peran,aktif FROM pengguna WHERE lower(email)=lower(%s) AND password_hash = crypt(%s, password_hash)",
            (b.email.strip(), b.password)).fetchone()
        if not u:
            raise HTTPException(401, "Email atau kata sandi salah.")
        if not u["aktif"]:
            raise HTTPException(403, "Akun dinonaktifkan. Hubungi administrator.")
        catat(c, u["id_pengguna"], "akun", u["id_pengguna"], "login")
    u.pop("aktif")
    return {"token": buat_token(u["id_pengguna"]), "pengguna": u}


@router.get("/me")
def me(u=Depends(pengguna_saat_ini)):
    return u

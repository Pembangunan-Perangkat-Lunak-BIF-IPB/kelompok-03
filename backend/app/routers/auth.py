"""Autentikasi: login, registrasi mandiri, verifikasi email, kirim ulang, lupa & reset kata sandi.
(Registrasi/verifikasi/reset adalah penambahan di luar SKPL; lihat PERUBAHAN_DI_LUAR_SKPL.md.)"""
import hashlib, re, secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from .. import config, mailer, ratelimit
from ..db import get_conn
from ..deps import catat, pengguna_saat_ini
from ..security import buat_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
GENERIK = "Jika email terdaftar, instruksi telah dikirim. Periksa kotak masuk dan folder spam."


class Login(BaseModel):
    email: str
    password: str


class Daftar(BaseModel):
    nama: str
    email: str
    password: str


class Surel(BaseModel):
    email: str


class TokenIn(BaseModel):
    token: str


class Reset(BaseModel):
    token: str
    password: str


def _hash(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def _buat_token(conn, id_pengguna: int, jenis: str, masa: timedelta) -> str:
    """Token baru; token lama yang belum dipakai untuk jenis yang sama dibatalkan. Hanya hash yang disimpan."""
    conn.execute("DELETE FROM token_email WHERE id_pengguna=%s AND jenis=%s AND dipakai_pada IS NULL", (id_pengguna, jenis))
    t = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO token_email (id_pengguna,jenis,token_hash,kedaluwarsa) VALUES (%s,%s,%s,%s)",
                 (id_pengguna, jenis, _hash(t), datetime.now(timezone.utc) + masa))
    return t


def _cek_sandi(p: str):
    if len(p or "") < 8:
        raise HTTPException(422, "Kata sandi minimal 8 karakter.")


def _email_verifikasi(bg: BackgroundTasks, nama: str, email: str, token: str):
    bg.add_task(mailer.kirim, email, *mailer.teks_verifikasi(nama, f"{config.APP_URL}/verifikasi?token={token}"))


@router.post("/login")
def login(b: Login, request: Request):
    ratelimit.batasi(request, "login:" + b.email.strip().lower(), login=True)
    with get_conn() as c:
        u = c.execute(
            "SELECT id_pengguna,nama,email,peran,aktif,email_terverifikasi FROM pengguna WHERE lower(email)=lower(%s) AND password_hash = crypt(%s, password_hash)",
            (b.email.strip(), b.password)).fetchone()
        if not u:
            raise HTTPException(401, "Email atau kata sandi salah.")
        if not u["aktif"]:
            raise HTTPException(403, "Akun dinonaktifkan. Hubungi administrator.")
        if not u["email_terverifikasi"]:
            raise HTTPException(403, "Email belum diverifikasi. Periksa kotak masuk Anda atau kirim ulang email verifikasi.")
        catat(c, u["id_pengguna"], "akun", u["id_pengguna"], "login")
    u.pop("aktif"); u.pop("email_terverifikasi")
    return {"token": buat_token(u["id_pengguna"]), "pengguna": u}


@router.post("/daftar", status_code=201)
def daftar(b: Daftar, request: Request, bg: BackgroundTasks):
    ratelimit.batasi(request, "daftar")
    nama, email = b.nama.strip(), b.email.strip()
    if not nama:
        raise HTTPException(422, "Nama wajib diisi.")
    if not EMAIL.fullmatch(email):
        raise HTTPException(422, "Format email tidak valid.")
    _cek_sandi(b.password)
    with get_conn() as c:
        ada = c.execute("SELECT email_terverifikasi FROM pengguna WHERE lower(email)=lower(%s)", (email,)).fetchone()
        if ada:
            raise HTTPException(409, "Email sudah terdaftar tetapi belum diverifikasi. Gunakan 'Kirim ulang email verifikasi' di halaman masuk."
                                if not ada["email_terverifikasi"] else "Email sudah terdaftar. Silakan masuk.")
        u = c.execute("INSERT INTO pengguna (nama,email,password_hash,peran,email_terverifikasi) VALUES (%s,%s,crypt(%s, gen_salt('bf')),'peneliti',FALSE) RETURNING id_pengguna",
                      (nama, email, b.password)).fetchone()   # peran selalu 'peneliti' pada registrasi mandiri
        t = _buat_token(c, u["id_pengguna"], "verifikasi", timedelta(hours=config.VERIFIKASI_JAM))
    _email_verifikasi(bg, nama, email, t)
    return {"pesan": "Pendaftaran berhasil. Kami mengirim tautan verifikasi ke email Anda. Akun dapat dipakai setelah email diverifikasi."}


@router.post("/verifikasi")
def verifikasi(b: TokenIn):
    with get_conn() as c:
        r = c.execute("""SELECT t.id_token, t.dipakai_pada, t.kedaluwarsa, p.id_pengguna, p.email_terverifikasi FROM token_email t
                         JOIN pengguna p USING (id_pengguna) WHERE t.token_hash=%s AND t.jenis='verifikasi'""", (_hash(b.token),)).fetchone()
        if not r:
            raise HTTPException(400, "Tautan verifikasi tidak valid atau sudah tidak berlaku.")
        if r["dipakai_pada"]:   # klik ganda / muat ulang: tidak dianggap kesalahan bila email sudah terverifikasi
            if r["email_terverifikasi"]:
                return {"pesan": "Email sudah terverifikasi. Silakan masuk."}
            raise HTTPException(400, "Tautan verifikasi tidak valid atau sudah tidak berlaku.")
        if r["kedaluwarsa"] < datetime.now(timezone.utc):
            raise HTTPException(400, "Tautan verifikasi sudah kedaluwarsa. Minta email verifikasi baru dari halaman masuk.")
        c.execute("UPDATE pengguna SET email_terverifikasi=TRUE WHERE id_pengguna=%s", (r["id_pengguna"],))
        c.execute("UPDATE token_email SET dipakai_pada=now() WHERE id_token=%s", (r["id_token"],))
        catat(c, r["id_pengguna"], "akun", r["id_pengguna"], "ubah")
    return {"pesan": "Email berhasil diverifikasi. Silakan masuk."}


@router.post("/kirim-ulang")
def kirim_ulang(b: Surel, request: Request, bg: BackgroundTasks):
    ratelimit.batasi(request, "kirim-ulang")
    with get_conn() as c:
        u = c.execute("SELECT id_pengguna,nama,email FROM pengguna WHERE lower(email)=lower(%s) AND NOT email_terverifikasi AND aktif", (b.email.strip(),)).fetchone()
        if u:
            t = _buat_token(c, u["id_pengguna"], "verifikasi", timedelta(hours=config.VERIFIKASI_JAM))
    if u:
        _email_verifikasi(bg, u["nama"], u["email"], t)
    return {"pesan": GENERIK}   # jawaban sama untuk email tak dikenal (tidak membocorkan keberadaan akun)


@router.post("/lupa")
def lupa(b: Surel, request: Request, bg: BackgroundTasks):
    ratelimit.batasi(request, "lupa")
    with get_conn() as c:
        u = c.execute("SELECT id_pengguna,nama,email FROM pengguna WHERE lower(email)=lower(%s) AND aktif", (b.email.strip(),)).fetchone()
        if u:
            t = _buat_token(c, u["id_pengguna"], "reset_sandi", timedelta(minutes=config.RESET_MENIT))
    if u:
        bg.add_task(mailer.kirim, u["email"], *mailer.teks_reset(u["nama"], f"{config.APP_URL}/reset-sandi?token={t}"))
    return {"pesan": GENERIK}


@router.post("/reset")
def reset(b: Reset):
    _cek_sandi(b.password)
    with get_conn() as c:
        r = c.execute("""SELECT t.id_token, t.dipakai_pada, t.kedaluwarsa, t.id_pengguna FROM token_email t
                         WHERE t.token_hash=%s AND t.jenis='reset_sandi'""", (_hash(b.token),)).fetchone()
        if not r or r["dipakai_pada"]:
            raise HTTPException(400, "Tautan atur ulang kata sandi tidak valid atau sudah dipakai.")
        if r["kedaluwarsa"] < datetime.now(timezone.utc):
            raise HTTPException(400, "Tautan atur ulang kata sandi sudah kedaluwarsa. Minta tautan baru.")
        # membuka tautan dari email = bukti pemilik kotak surat, jadi email ikut terverifikasi
        c.execute("UPDATE pengguna SET password_hash=crypt(%s, gen_salt('bf')), email_terverifikasi=TRUE WHERE id_pengguna=%s", (b.password, r["id_pengguna"]))
        c.execute("UPDATE token_email SET dipakai_pada=now() WHERE id_token=%s", (r["id_token"],))
        catat(c, r["id_pengguna"], "akun", r["id_pengguna"], "ubah")
    return {"pesan": "Kata sandi berhasil diubah. Silakan masuk dengan kata sandi baru."}


@router.get("/me")
def me(u=Depends(pengguna_saat_ini)):
    return u

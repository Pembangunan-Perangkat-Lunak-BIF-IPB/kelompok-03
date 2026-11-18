"""Registrasi mandiri, verifikasi email, kirim ulang, lupa/reset kata sandi, dan penghapusan akun oleh admin."""
import hashlib, re
from app import mailer, ratelimit
from app.db import get_conn
from .conftest import masuk

REG = {"nama": "Uji Mandiri", "email": "uji.mandiri@gmail.com", "password": "Rahasia#123"}


def token_terakhir(email):
    surat = [m for m in mailer.OUTBOX if m["to"] == email]
    assert surat, f"tidak ada email ke {email}"
    return re.search(r"token=([\w\-]+)", surat[-1]["body"]).group(1)


def test_daftar_validasi(client):
    assert client.post("/api/auth/daftar", json={**REG, "password": "pendek"}).status_code == 422
    assert client.post("/api/auth/daftar", json={**REG, "email": "bukan-email"}).status_code == 422
    assert client.post("/api/auth/daftar", json={**REG, "nama": "  "}).status_code == 422


def test_daftar_verifikasi_login(client):
    n0 = len(mailer.OUTBOX)
    r = client.post("/api/auth/daftar", json={**REG, "peran": "administrator"})   # upaya menaikkan peran diabaikan
    assert r.status_code == 201 and len(mailer.OUTBOX) == n0 + 1
    t1 = token_terakhir(REG["email"])
    with get_conn() as c:   # hanya hash yang tersimpan, token asli tidak
        row = c.execute("SELECT t.token_hash, p.peran, p.email_terverifikasi FROM token_email t JOIN pengguna p USING (id_pengguna) WHERE p.email=%s", (REG["email"],)).fetchone()
    assert row["token_hash"] == hashlib.sha256(t1.encode()).hexdigest() and row["token_hash"] != t1
    assert row["peran"] == "peneliti" and row["email_terverifikasi"] is False
    # login ditolak sebelum verifikasi
    r = client.post("/api/auth/login", json={"email": REG["email"], "password": REG["password"]})
    assert r.status_code == 403 and "belum diverifikasi" in r.json()["detail"]
    # email ganda
    r = client.post("/api/auth/daftar", json=REG); assert r.status_code == 409 and "belum diverifikasi" in r.json()["detail"]
    # kirim ulang: token lama tidak berlaku lagi, token baru berlaku
    assert client.post("/api/auth/kirim-ulang", json={"email": REG["email"]}).status_code == 200
    t2 = token_terakhir(REG["email"]); assert t2 != t1
    assert client.post("/api/auth/verifikasi", json={"token": t1}).status_code == 400
    assert client.post("/api/auth/verifikasi", json={"token": "ngawur"}).status_code == 400
    # token kedaluwarsa
    with get_conn() as c:
        c.execute("UPDATE token_email SET kedaluwarsa = now() - interval '1 minute' WHERE token_hash=%s", (hashlib.sha256(t2.encode()).hexdigest(),))
    r = client.post("/api/auth/verifikasi", json={"token": t2}); assert r.status_code == 400 and "kedaluwarsa" in r.json()["detail"]
    client.post("/api/auth/kirim-ulang", json={"email": REG["email"]}); t3 = token_terakhir(REG["email"])
    assert client.post("/api/auth/verifikasi", json={"token": t3}).status_code == 200
    assert client.post("/api/auth/verifikasi", json={"token": t3}).status_code == 200      # klik ganda tidak error
    assert client.post("/api/auth/daftar", json=REG).status_code == 409                    # kini 'sudah terdaftar'
    h = masuk(client, REG["email"], REG["password"])
    assert client.get("/api/auth/me", headers=h).json()["peran"] == "peneliti"
    assert client.get("/api/pengguna", headers=h).status_code == 403
    # sudah terverifikasi: kirim ulang tidak mengirim email lagi
    n = len(mailer.OUTBOX); client.post("/api/auth/kirim-ulang", json={"email": REG["email"]}); assert len(mailer.OUTBOX) == n


def test_kirim_ulang_dan_lupa_tidak_membocorkan_akun(client):
    n = len(mailer.OUTBOX)
    a = client.post("/api/auth/kirim-ulang", json={"email": "tidak.ada@x.id"})
    b = client.post("/api/auth/lupa", json={"email": "tidak.ada@x.id"})
    assert a.status_code == b.status_code == 200 and len(mailer.OUTBOX) == n
    assert a.json() == client.post("/api/auth/lupa", json={"email": REG["email"]}).json()   # respons sama untuk email terdaftar


def test_lupa_dan_reset_sandi(client):
    assert client.post("/api/auth/lupa", json={"email": REG["email"]}).status_code == 200
    t = token_terakhir(REG["email"])
    assert client.post("/api/auth/reset", json={"token": t, "password": "pendek"}).status_code == 422
    assert client.post("/api/auth/reset", json={"token": "salah", "password": "SandiBaru#1"}).status_code == 400
    assert client.post("/api/auth/reset", json={"token": t, "password": "SandiBaru#1"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": REG["email"], "password": REG["password"]}).status_code == 401   # sandi lama mati
    masuk(client, REG["email"], "SandiBaru#1")
    assert client.post("/api/auth/reset", json={"token": t, "password": "Lain#12345"}).status_code == 400                    # sekali pakai


def test_reset_memverifikasi_email_pendaftar(client):
    client.post("/api/auth/daftar", json={"nama": "Belum Verif", "email": "uji.belum@x.id", "password": "Awal#12345"})
    client.post("/api/auth/lupa", json={"email": "uji.belum@x.id"})
    t = token_terakhir("uji.belum@x.id")
    assert client.post("/api/auth/reset", json={"token": t, "password": "Baru#123456"}).status_code == 200
    masuk(client, "uji.belum@x.id", "Baru#123456")


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(ratelimit, "MAKS", 3); ratelimit.reset()
    kode = [client.post("/api/auth/lupa", json={"email": "a@b.co"}).status_code for _ in range(4)]
    assert kode == [200, 200, 200, 429]
    monkeypatch.setattr(ratelimit, "MAKS_LOGIN", 2); ratelimit.reset()
    kode = [client.post("/api/auth/login", json={"email": "peneliti@ipb.ac.id", "password": "x"}).status_code for _ in range(3)]
    assert kode == [401, 401, 429]
    ratelimit.reset()


def test_admin_hapus_akun_tidak_terpakai(client, admin, peneliti):
    daftar = client.get("/api/pengguna", headers=admin).json()
    assert all("email_terverifikasi" in u for u in daftar)
    belum = [u for u in daftar if u["email"] == "uji.belum@x.id"][0]
    # daftar baru yang tak pernah dipakai bisa dihapus
    client.post("/api/auth/daftar", json={"nama": "Tak Terpakai", "email": "uji.sepi@x.id", "password": "Awal#12345"})
    sepi = [u for u in client.get("/api/pengguna", headers=admin).json() if u["email"] == "uji.sepi@x.id"][0]
    assert sepi["email_terverifikasi"] is False
    assert client.delete(f"/api/pengguna/{sepi['id_pengguna']}", headers=peneliti).status_code == 403
    assert client.delete(f"/api/pengguna/{sepi['id_pengguna']}", headers=admin).status_code == 204
    assert client.delete(f"/api/pengguna/{sepi['id_pengguna']}", headers=admin).status_code == 404
    # akun yang sudah punya jejak akses/data tidak boleh dihapus; diri sendiri juga tidak
    assert client.delete(f"/api/pengguna/{belum['id_pengguna']}", headers=admin).status_code == 409
    me = client.get("/api/auth/me", headers=admin).json()
    assert client.delete(f"/api/pengguna/{me['id_pengguna']}", headers=admin).status_code == 409
    pen = [u for u in daftar if u["email"] == "peneliti@ipb.ac.id"][0]
    r = client.delete(f"/api/pengguna/{pen['id_pengguna']}", headers=admin)
    assert r.status_code == 409 and "Nonaktifkan" in r.json()["detail"]

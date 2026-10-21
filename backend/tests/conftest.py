import os, tempfile
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/human_gvc_test")
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="gvc_test_")
os.environ["SIM_DETIK_PER_TAHAP"] = "0.1"
os.environ["PIPELINE_MODE"] = "simulasi"
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from app.main import app
    from app.db import get_conn
    with get_conn() as c:   # mulai bersih, pertahankan seed (pengguna & referensi bawaan)
        c.execute("TRUNCATE log_akses, log_proses, riwayat_analisis, genotipe, varian, analisis, sampel RESTART IDENTITY CASCADE")
        c.execute("DELETE FROM referensi WHERE status='unggahan'")
        c.execute("DELETE FROM pengguna WHERE email LIKE 'uji.%'")
        c.execute("UPDATE pengguna SET aktif=TRUE")
    with TestClient(app) as cl:
        yield cl


def masuk(client, email, pw):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture(scope="session")
def peneliti(client): return masuk(client, "peneliti@ipb.ac.id", "Peneliti#123")
@pytest.fixture(scope="session")
def admin(client): return masuk(client, "rakahendrawan@ipb.ac.id", "Admin#123")

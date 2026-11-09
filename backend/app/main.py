"""Human GVC API (UI/API + Job Manager pada Desain Modular). Jalankan: uvicorn app.main:app --reload --port 8000"""
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import pipeline
from .config import FRONTEND_ORIGIN, PIPELINE_MODE
from .db import get_conn
from .routers import analisis, auth, pengguna, referensi, sampel, varian


@asynccontextmanager
async def lifespan(app):
    try:
        n = pipeline.pulihkan_saat_start()
        if n:
            print(f"[startup] {n} analisis tertunda ditandai gagal.")
    except Exception as e:  # noqa: BLE001 - database mungkin belum siap; /api/health akan melaporkannya
        print(f"[startup] lewati pemulihan: {e}")
    yield


app = FastAPI(title="Human GVC API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=list({FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"}),
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition"])
for r in (auth, sampel, referensi, analisis, varian, pengguna):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    try:
        with get_conn() as c:
            c.execute("SELECT 1")
        db = "terhubung"
    except Exception as e:  # noqa: BLE001
        db = f"gagal: {e}"
    return {"api": "ok", "database": db, "mode_pipeline": PIPELINE_MODE, "waktu": datetime.now().isoformat()}

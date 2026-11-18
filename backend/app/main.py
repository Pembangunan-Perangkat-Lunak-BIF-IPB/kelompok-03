"""Human GVC API (UI/API + Job Manager pada Desain Modular). Jalankan: uvicorn app.main:app --reload --port 8000"""
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import pipeline
from .config import FRONTEND_ORIGIN, PIPELINE_MODE
from .db import get_conn
from .routers import analisis, auth, distribusi, log, pengguna, referensi, sampel, varian


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
for r in (auth, sampel, referensi, analisis, log, distribusi, varian, pengguna):
    app.include_router(r.router)


import shutil
import subprocess

def _versi_perangkat() -> dict:
    hasil = {}
    # fastp
    try:
        r = subprocess.run(["fastp", "--version"], capture_output=True, text=True, check=False)
        hasil["fastp"] = r.stderr.strip() or r.stdout.strip()
    except Exception:
        hasil["fastp"] = "tidak terpasang"

    # bwa-mem2 / bwa
    aligner = "bwa-mem2" if shutil.which("bwa-mem2") else ("bwa" if shutil.which("bwa") else None)
    if aligner:
        try:
            cmd = [aligner, "version"] if aligner == "bwa-mem2" else [aligner]
            r = subprocess.run(cmd, capture_output=True, text=True, check=False)
            output = (r.stdout or r.stderr or "").strip().splitlines()
            baris = output[0] if output else "tersedia"
            hasil["aligner"] = f"{aligner} ({baris})"
        except Exception:
            hasil["aligner"] = aligner
    else:
        hasil["aligner"] = "tidak terpasang"

    # samtools
    try:
        r = subprocess.run(["samtools", "--version"], capture_output=True, text=True, check=False)
        hasil["samtools"] = r.stdout.splitlines()[0] if r.stdout else "tersedia"
    except Exception:
        hasil["samtools"] = "tidak terpasang"

    # bcftools
    try:
        r = subprocess.run(["bcftools", "--version"], capture_output=True, text=True, check=False)
        hasil["bcftools"] = r.stdout.splitlines()[0] if r.stdout else "tersedia"
    except Exception:
        hasil["bcftools"] = "tidak terpasang"

    return hasil


@app.get("/api/health")
def health():
    try:
        with get_conn() as c:
            c.execute("SELECT 1")
        db = "terhubung"
    
    except Exception:  # noqa: BLE001
        logging.getLogger("uvicorn.error").exception("Health check: koneksi database gagal")
        db = "gagal"
    
    return {
        "api": "ok",
        "database": db,
        "mode_pipeline": PIPELINE_MODE,
        "perangkat_bioinformatika": _versi_perangkat(),
        "waktu": datetime.now().isoformat(),
    }

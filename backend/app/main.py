"""
Kerangka backend Human GVC (komponen UI/API + Job Manager pada Desain Modular).

Minggu 7: endpoint dasar untuk memastikan FE <-> BE <-> DB tersambung.
Belum ada: autentikasi, upload FASTQ, eksekusi pipeline (Minggu 8-9).
"""
import os
from datetime import datetime
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from .db import get_conn, table_columns

# SEMENTARA (sebelum login, Minggu 8): jika diisi di .env, request yang tidak membawa
# id_pengguna dianggap berasal dari pengguna ini. Kosongkan/hapus saat autentikasi siap.
DEV_DEFAULT_USER_ID = os.getenv("DEV_DEFAULT_USER_ID")

app = FastAPI(title="Human GVC API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _db_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=f"Database tidak dapat diakses: {exc}")


@app.get("/api/health")
def health():
    """Cek API hidup dan database terhubung."""
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        db = "terhubung"
    except Exception as exc:  # noqa: BLE001
        db = f"gagal: {exc}"
    return {"api": "ok", "database": db, "waktu": datetime.now().isoformat()}


@app.get("/api/sampel")
def list_sampel():
    """UC-01 (awal): daftar sampel."""
    try:
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM sampel ORDER BY 1 DESC").fetchall()
    except Exception as exc:  # noqa: BLE001
        raise _db_error(exc)
    return jsonable_encoder(rows)


@app.post("/api/sampel", status_code=201)
def create_sampel(data: dict[str, Any]):
    """
    UC-01 (awal): simpan metadata sampel (FR-04).
    Hanya kolom yang benar-benar ada di tabel `sampel` yang disimpan,
    sehingga cocok dengan skema Minggu 6 apa pun nama kolomnya.
    """
    if DEV_DEFAULT_USER_ID and not data.get("id_pengguna"):
        data = {**data, "id_pengguna": int(DEV_DEFAULT_USER_ID)}
    try:
        with get_conn() as conn:
            cols = table_columns(conn, "sampel")
            pk = cols[0] if cols else None
            payload = {k: v for k, v in data.items() if k in cols and k != pk and v not in ("", None)}
            if not payload:
                raise HTTPException(400, f"Tidak ada kolom valid. Kolom tabel sampel: {cols}")
            names = ", ".join(payload)
            marks = ", ".join(["%s"] * len(payload))
            row = conn.execute(
                f"INSERT INTO sampel ({names}) VALUES ({marks}) RETURNING *",
                list(payload.values()),
            ).fetchone()
            conn.commit()
    except HTTPException:
        raise
    except psycopg.errors.IntegrityError as exc:
        # NOT NULL / FK / CHECK / UNIQUE dilanggar = salah data, bukan database mati
        raise HTTPException(status_code=422, detail=exc.diag.message_primary)
    except Exception as exc:  # noqa: BLE001
        raise _db_error(exc)
    return jsonable_encoder(row)


@app.get("/api/sampel/kolom")
def sampel_columns():
    """Dipakai FE untuk membangun form sesuai skema sebenarnya."""
    try:
        with get_conn() as conn:
            return table_columns(conn, "sampel")
    except Exception as exc:  # noqa: BLE001
        raise _db_error(exc)


@app.get("/api/analisis")
def list_analisis():
    """UC-03/UC-04 (awal): daftar analisis beserta status."""
    try:
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM analisis ORDER BY 1 DESC").fetchall()
    except Exception as exc:  # noqa: BLE001
        raise _db_error(exc)
    return jsonable_encoder(rows)


@app.get("/api/analisis/{id_analisis}/log")
def analisis_log(id_analisis: int):
    """UC-04 / FR-07: log proses kronologis (tabel log_proses), dipolling oleh FE."""
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM log_proses WHERE id_analisis = %s ORDER BY waktu",
                (id_analisis,),
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        raise _db_error(exc)
    return jsonable_encoder(rows)

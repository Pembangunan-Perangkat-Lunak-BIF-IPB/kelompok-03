"""Koneksi PostgreSQL (komponen Database pada Desain Modular)."""
import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/human_gvc"
)


def get_conn():
    """Buka koneksi baru. Hasil query berupa dict {kolom: nilai}."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=3)


def table_columns(conn, table: str) -> list[str]:
    """Daftar nama kolom tabel, dibaca dari skema yang sebenarnya."""
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s "
        "ORDER BY ordinal_position",
        (table,),
    ).fetchall()
    return [r["column_name"] for r in rows]

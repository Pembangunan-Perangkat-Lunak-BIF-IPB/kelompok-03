"""Koneksi PostgreSQL. Hasil query berupa dict. `with get_conn() as c:` commit otomatis jika sukses, rollback jika error."""
import psycopg
from psycopg.rows import dict_row
from .config import DATABASE_URL


def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=5)

"""Pembatas percobaan sederhana di memori (per proses). Cukup untuk satu server; gunakan Redis jika multi-instance."""
import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request
from . import config

MAKS, MAKS_LOGIN, MENIT = config.RATE_LIMIT_MAKS, config.RATE_LIMIT_LOGIN_MAKS, config.RATE_LIMIT_MENIT
_catatan: dict[str, deque] = defaultdict(deque)


def batasi(request: Request, kunci: str, login: bool = False) -> None:
    k = f"{kunci}|{request.client.host if request.client else '-'}"
    q, sekarang = _catatan[k], time.time()
    while q and q[0] < sekarang - MENIT * 60:
        q.popleft()
    if len(q) >= (MAKS_LOGIN if login else MAKS):
        raise HTTPException(429, f"Terlalu banyak percobaan. Coba lagi dalam {MENIT} menit.")
    q.append(sekarang)


def reset() -> None:
    _catatan.clear()

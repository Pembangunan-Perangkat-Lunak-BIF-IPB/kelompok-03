"""Token bertanda tangan HMAC (tanpa dependensi tambahan) dan helper kata sandi (pgcrypto di SQL)."""
import base64, hashlib, hmac, json, time
from .config import SECRET_KEY, TOKEN_JAM


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def buat_token(id_pengguna: int) -> str:
    payload = _b64(json.dumps({"uid": id_pengguna, "exp": int(time.time()) + TOKEN_JAM * 3600}).encode())
    sig = _b64(hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def baca_token(token: str) -> int | None:
    try:
        payload, sig = token.split(".")
        ok = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_unb64(sig), ok):
            return None
        data = json.loads(_unb64(payload))
        return data["uid"] if data["exp"] > time.time() else None
    except Exception:  # noqa: BLE001
        return None
# Hash kata sandi: SQL `crypt(%s, gen_salt('bf'))` dan `password_hash = crypt(%s, password_hash)`
# (kompatibel dengan data di database/Insert_Select_Dummy.sql).

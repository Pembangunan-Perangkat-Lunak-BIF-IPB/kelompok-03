"""Pengiriman email via SMTP (Gmail). Tanpa SMTP_HOST = mode pengembangan: isi email dicetak di terminal
dan disimpan di OUTBOX (dipakai tes). Dipanggil lewat BackgroundTasks agar request tidak menunggu SMTP."""
import smtplib
from email.message import EmailMessage
from . import config

OUTBOX: list[dict] = []   # hanya terisi pada mode pengembangan


def kirim(tujuan: str, subjek: str, teks: str) -> None:
    if not (config.SMTP_HOST and config.SMTP_USER):
        OUTBOX.append({"to": tujuan, "subject": subjek, "body": teks})
        print(f"\n[EMAIL-DEV] Kepada: {tujuan}\n[EMAIL-DEV] Subjek: {subjek}\n{teks}\n", flush=True)
        return
    try:
        m = EmailMessage()
        m["From"], m["To"], m["Subject"] = config.SMTP_FROM, tujuan, subjek
        m.set_content(teks)
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as s:
            s.starttls()
            s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.send_message(m)
    except Exception as e:  # noqa: BLE001 - kegagalan email tidak boleh menjatuhkan request; pengguna bisa kirim ulang
        print(f"[EMAIL-GAGAL] {tujuan}: {e}", flush=True)


def teks_verifikasi(nama: str, tautan: str) -> tuple[str, str]:
    return "Verifikasi email akun Human GVC", (
        f"Halo {nama},\n\nTerima kasih telah mendaftar di Human GVC. Klik tautan berikut untuk memverifikasi email Anda "
        f"(berlaku {config.VERIFIKASI_JAM} jam):\n\n{tautan}\n\nJika Anda tidak merasa mendaftar, abaikan email ini.\n")


def teks_reset(nama: str, tautan: str) -> tuple[str, str]:
    return "Atur ulang kata sandi Human GVC", (
        f"Halo {nama},\n\nKami menerima permintaan mengatur ulang kata sandi akun Anda. Klik tautan berikut "
        f"(berlaku {config.RESET_MENIT} menit):\n\n{tautan}\n\nJika Anda tidak memintanya, abaikan email ini; kata sandi Anda tidak berubah.\n")

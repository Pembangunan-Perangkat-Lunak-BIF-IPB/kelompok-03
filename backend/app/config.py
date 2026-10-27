"""Konfigurasi dari environment (.env). Lihat env.example."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/human_gvc")
SECRET_KEY = os.getenv("SECRET_KEY", "ganti-dengan-string-acak-panjang")
TOKEN_JAM = int(os.getenv("TOKEN_JAM", "12"))
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "./storage")).resolve()   # Storage berkas besar (Desain Modular, komponen Storage)
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "2048"))                # SKPL hanya menyebut "ukuran wajar"; angka ini asumsi
MAX_REFERENSI_MB = int(os.getenv("MAX_REFERENSI_MB", "4096"))

# simulasi = pipeline tiruan (tanpa tool bioinformatika, untuk demo/uji)
# nyata    = menjalankan fastp, bwa, samtools, bcftools (harus terpasang)
PIPELINE_MODE = os.getenv("PIPELINE_MODE", "simulasi")
SIM_DETIK_PER_TAHAP = float(os.getenv("SIM_DETIK_PER_TAHAP", "4"))
PIPELINE_THREADS = int(os.getenv("PIPELINE_THREADS", "4"))
PIPELINE_WORKERS = int(os.getenv("PIPELINE_WORKERS", "2"))             # analisis yang boleh berjalan bersamaan

# BR-04. SKPL tidak menyebut angka rentang: samakan dengan frontend/lib/constants.js
PARAM_RANGE = {
    "kualitas_pemangkasan_min": (0, 40),
    "kedalaman_min": (1, 1000),
    "qual_min": (0, 1000),
}
PARAM_DEFAULT = {"kualitas_pemangkasan_min": 20, "kedalaman_min": 10, "qual_min": 30}
MASA_RETENSI_HARI = int(os.getenv("MASA_RETENSI_HARI", "90"))          # BR-08 (default kolom DB: 90)

# Akun: verifikasi email & reset kata sandi
APP_URL = os.getenv("APP_URL", FRONTEND_ORIGIN).rstrip("/")            # dasar tautan di email
SMTP_HOST = os.getenv("SMTP_HOST", "")                                   # kosong = mode pengembangan (tautan dicetak di terminal)
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "") or SMTP_USER
VERIFIKASI_JAM = int(os.getenv("VERIFIKASI_JAM", "24"))
RESET_MENIT = int(os.getenv("RESET_MENIT", "60"))
RATE_LIMIT_MAKS = int(os.getenv("RATE_LIMIT_MAKS", "5"))                # daftar / kirim ulang / lupa sandi per 15 menit
RATE_LIMIT_LOGIN_MAKS = int(os.getenv("RATE_LIMIT_LOGIN_MAKS", "10"))   # percobaan login per 15 menit
RATE_LIMIT_MENIT = int(os.getenv("RATE_LIMIT_MENIT", "15"))

STAGES = ["qc_trimming", "alignment", "bam_processing", "variant_calling", "filtering", "anotasi"]
STAGE_LABEL = {
    "qc_trimming": "QC & Trimming", "alignment": "Alignment", "bam_processing": "Pemrosesan BAM",
    "variant_calling": "Variant Calling", "filtering": "Filtering", "anotasi": "Anotasi",
}
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

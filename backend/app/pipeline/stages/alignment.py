"""Tahap 2: Alignment (WP-2 / Dhafin).

Membaca : ctx.berkas["reads_r1"], ctx.berkas["reads_r2"] (opsional), ctx.referensi
Menulis : ctx.berkas["bam_mentah"]

Perangkat: bwa-mem2 (dipilih pengguna, fallback bwa mem jika bwa-mem2 tidak ada).
Pipa     : bwa-mem2 mem ... | samtools view -b -o bam_mentah -
           -> Menghilangkan SAM antara di disk (menghemat ruang & I/O; Risiko R4).
Read Group: @RG\tID:<id_sampel>\tSM:<nama_sampel_aman>\tPL:ILLUMINA
           -> Nama sampel dibersihkan: hapus tab, spasi, newline (Risiko R3).
Referensi: Ditolak jika berakhiran .gz (FASTA terkompresi belum didukung di pipeline ini).
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

try:
    from ..konteks import Konteks, TahapGagal
    from ..runner import Runner
except ImportError:
    from .._konteks_stub import Konteks, TahapGagal, Runner  # fallback WP-2


def _bersihkan_nama_sampel(nama: str) -> str:
    """Bersihkan nama sampel agar aman di tag @RG SM:... (hapus tab, spasi, karakter kontrol)."""
    # Ganti spasi, tab, newline dengan underscore; hanya izinkan alfanumerik, dash, underscore, titik
    aman = re.sub(r"[\s\t\r\n]+", "_", nama.strip())
    aman = re.sub(r"[^A-Za-z0-9._-]", "", aman)
    return aman or "sample"


def _pilih_aligner() -> str:
    """Gunakan bwa-mem2 jika tersedia, fallback ke bwa."""
    if shutil.which("bwa-mem2"):
        return "bwa-mem2"
    if shutil.which("bwa"):
        return "bwa"
    raise TahapGagal(
        "Tidak ditemukan 'bwa-mem2' maupun 'bwa'. "
        "Pastikan conda activate human-gvc sudah dijalankan."
    )


def jalankan(ctx: Konteks, sh: Runner) -> None:
    """Lakukan alignment reads ke referensi; hasilkan bam_mentah."""
    # 1. Validasi referensi
    ref = ctx.referensi
    if not ref.exists():
        raise TahapGagal(f"Berkas referensi tidak ditemukan: {ref.name}")
    if ref.name.lower().endswith((".gz", ".bgz")):
        raise TahapGagal(
            f"Referensi FASTA terkompresi ({ref.name}) belum didukung. "
            "Gunakan berkas FASTA (.fa / .fasta) yang tidak terkompresi."
        )

    # 2. Validasi input reads dari tahap qc_trimming
    r1 = ctx.berkas.get("reads_r1")
    if not r1 or not Path(r1).exists():
        raise TahapGagal("Berkas reads R1 dari tahap QC tidak ditemukan.")
    r2 = ctx.berkas.get("reads_r2")
    if r2 and not Path(r2).exists():
        raise TahapGagal("Berkas reads R2 dari tahap QC tidak ditemukan.")

    aligner = _pilih_aligner()
    threads = str(max(1, ctx.threads))
    out_bam = ctx.kerja / "aln_raw.bam"

    sh.catat(f"Menggunakan aligner: {aligner} (threads: {threads})...")
    sh.progres(10)

    # 3. Read group yang aman (Risiko R3)
    sm = _bersihkan_nama_sampel(ctx.nama_sampel)
    rg = f"@RG\\tID:{ctx.id_sampel}\\tSM:{sm}\\tPL:ILLUMINA"
    sh.catat(f"Read Group: ID={ctx.id_sampel}, SM={sm}")

    # 4. Bangun perintah: bwa[-mem2] mem -> samtools view (pipa langsung, tanpa SAM di disk)
    cmd_bwa = [
        aligner, "mem",
        "-t", threads,
        "-R", rg,
        str(ref),
        str(r1),
    ]
    if r2:
        cmd_bwa.append(str(r2))

    cmd_samtools = [
        "samtools", "view",
        "-@", threads,
        "-b",
        "-o", str(out_bam),
        "-",
    ]

    sh.catat(f"Menjalankan: {' '.join(cmd_bwa[:5])}... | samtools view -b -o aln_raw.bam")
    sh.progres(20)

    # 5. Eksekusi pipa bwa | samtools view
    # Menggunakan subprocess.Popen berantai agar output bwa langsung disalurkan ke samtools
    # tanpa menulis file SAM puluhan GB ke disk (Risiko R4).
    p_bwa = None
    p_sam = None
    try:
        p_bwa = subprocess.Popen(
            cmd_bwa,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p_sam = subprocess.Popen(
            cmd_samtools,
            stdin=p_bwa.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Izinkan p_bwa menerima SIGPIPE jika p_sam keluar lebih dulu
        p_bwa.stdout.close()

        sam_out, sam_err = p_sam.communicate()
        bwa_out, bwa_err = p_bwa.communicate()

        if p_bwa.returncode != 0:
            err = (bwa_err or b"").decode(errors="replace")[-400:]
            raise TahapGagal(f"{aligner} mem gagal (kode {p_bwa.returncode}): {err}")
        if p_sam.returncode != 0:
            err = (sam_err or b"").decode(errors="replace")[-400:]
            raise TahapGagal(f"samtools view gagal (kode {p_sam.returncode}): {err}")

    except FileNotFoundError as e:
        raise TahapGagal(f"Perangkat tidak ditemukan saat alignment: {e}")
    finally:
        for p in (p_bwa, p_sam):
            if p and p.poll() is None:
                p.kill()

    sh.progres(90)

    # 6. Verifikasi keluaran
    if not out_bam.exists() or out_bam.stat().st_size == 0:
        raise TahapGagal("Tahap alignment selesai tetapi berkas BAM mentah kosong atau tidak ada.")

    # 7. Isi ctx.berkas (kontrak 3.3)
    ctx.berkas["bam_mentah"] = out_bam
    sh.catat(f"Alignment selesai -> {out_bam.name} ({out_bam.stat().st_size // 1024} KB)")
    sh.progres(100)

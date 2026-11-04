"""Tahap 1: QC & Trimming (WP-2).

Menjalankan fastp untuk kontrol kualitas dan pemangkasan sekuens (single-end maupun paired-end).
Menyelesaikan isu R1: Memetakan 'kualitas_pemangkasan_min' ke pemangkasan jendela geser
(--cut_right & --cut_tail) pada fastp, bukan sekadar filter -q.
"""
from pathlib import Path
from typing import Any

try:
    from ..konteks import Konteks, TahapGagal
except (ImportError, ValueError):
    try:
        from app.pipeline.konteks import Konteks, TahapGagal
    except (ImportError, ValueError):
        from konteks import Konteks, TahapGagal


def jalankan(ctx: Konteks, sh: Any) -> None:
    """Jalankan fastp pada data FASTQ input.

    Membaca: ctx.fastq_r1, ctx.fastq_r2 (opsional)
    Menulis : ctx.berkas['reads_r1'], ctx.berkas['reads_r2'] (jika paired),
              ctx.berkas['fastp_json'], ctx.berkas['fastp_html']
    """
    r1 = ctx.fastq_r1 if ctx.fastq_r1 and ctx.fastq_r1.exists() else ctx.berkas.get("fastq_r1")
    if not r1 or not Path(r1).exists():
        raise TahapGagal(f"Berkas FASTQ R1 tidak ditemukan: {r1}")

    r2 = ctx.fastq_r2 if ctx.fastq_r2 and ctx.fastq_r2.exists() else ctx.berkas.get("fastq_r2")
    is_paired = bool(r2 and Path(r2).exists())

    # Parameter pemangkasan kualitas (K4)
    q_min = int(ctx.parameter.get("kualitas_pemangkasan_min", 20))
    threads = str(ctx.threads)

    out_r1 = ctx.kerja / "trimmed_R1.fastq.gz"
    json_path = ctx.kerja / "fastp.json"
    html_path = ctx.kerja / "fastp.html"

    cmd = [
        "fastp",
        "-i", str(r1),
        "-o", str(out_r1),
        "-w", threads,
        # Trimming kualitas berbasis sliding window (5'->3' dan ekor 3')
        "--cut_right",
        "--cut_right_window_size", "4",
        "--cut_right_mean_quality", str(q_min),
        "--cut_tail",
        "--cut_tail_mean_quality", str(q_min),
        # Filter read berkualitas rendah
        "-q", str(q_min),
        "-j", str(json_path),
        "-h", str(html_path),
    ]

    if is_paired:
        out_r2 = ctx.kerja / "trimmed_R2.fastq.gz"
        cmd.extend(["-I", str(r2), "-O", str(out_r2)])
    else:
        out_r2 = None

    mode_label = "paired-end" if is_paired else "single-end"
    sh.catat(f"Menjalankan fastp ({mode_label}) dengan batas kualitas {q_min}...", jenis="info")
    sh.progres(20)

    # Jalankan perintah melalui Runner
    sh.run(cmd, nama="fastp")

    # Verifikasi berkas keluaran
    if not out_r1.exists():
        raise TahapGagal("fastp selesai tanpa menghasilkan berkas reads_r1 terpangkas.")
    if is_paired and (not out_r2 or not out_r2.exists()):
        raise TahapGagal("fastp selesai tanpa menghasilkan berkas reads_r2 terpangkas.")

    # Simpan ke konteks berkas
    ctx.berkas["reads_r1"] = out_r1
    if is_paired:
        ctx.berkas["reads_r2"] = out_r2
    ctx.berkas["fastp_json"] = json_path
    ctx.berkas["fastp_html"] = html_path

    sh.progres(100)
    sh.catat("Tahap QC & Trimming selesai.", jenis="berhasil")

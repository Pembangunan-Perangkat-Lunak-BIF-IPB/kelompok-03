"""Tahap 1: QC & Trimming (WP-2 / Dhafin).

Membaca : ctx.fastq_r1, ctx.fastq_r2 (None jika single-end)
Menulis : ctx.berkas["reads_r1"], ctx.berkas["reads_r2"] (jika paired),
          ctx.berkas["fastp_json"]
Ringkasan: ctx.ringkasan["qc"] = {reads_sebelum, reads_sesudah, q30_sebelum, q30_sesudah}

Keputusan K4:
- Parameter `kualitas_pemangkasan_min` dipetakan ke:
    --cut_right
    --cut_right_mean_quality <nilai>
  Alasan: ini pemangkasan sliding-window sesungguhnya (bukan filter per basa -q).
  Dokumentasi fastp: geser jendela 4 basa dari 5' ke 3', potong begitu rata jendela < ambang.
- Thread: ctx.threads (-w / --thread).
- Output: FASTQ terkompresi gzip (t1.fastq.gz / t2.fastq.gz) di ctx.kerja.
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    from ..konteks import Konteks, TahapGagal
    from ..runner import Runner
except ImportError:
    from .._konteks_stub import Konteks, TahapGagal, Runner  # fallback WP-2


def jalankan(ctx: Konteks, sh: Runner) -> None:
    """Jalankan fastp untuk single-end atau paired-end; simpan hasil ke ctx.berkas."""
    # 1. Validasi input
    if not ctx.fastq_r1.exists():
        raise TahapGagal(f"Berkas FASTQ R1 tidak ditemukan: {ctx.fastq_r1.name}")
    if ctx.fastq_r2 and not ctx.fastq_r2.exists():
        raise TahapGagal(f"Berkas FASTQ R2 tidak ditemukan: {ctx.fastq_r2.name}")

    sh.catat("Memulai QC dan pemangkasan adaptor/kualitas dengan fastp...")
    sh.progres(10)

    # 2. Siapkan path output
    out_r1 = ctx.kerja / "reads_trimmed_R1.fastq.gz"
    out_r2 = ctx.kerja / "reads_trimmed_R2.fastq.gz" if ctx.fastq_r2 else None
    json_report = ctx.kerja / "fastp.json"
    html_report = ctx.kerja / "fastp.html"

    # 3. Ambil parameter (BR-04, default 20)
    q_min = ctx.parameter.get("kualitas_pemangkasan_min", 20)
    threads = max(1, ctx.threads)

    # 4. Bangun perintah fastp
    cmd = [
        "fastp",
        "-i", str(ctx.fastq_r1),
        "-o", str(out_r1),
        "-j", str(json_report),
        "-h", str(html_report),
        "-w", str(threads),
        # Keputusan K4: pemangkasan sliding-window dari kanan (3')
        "--cut_right",
        "--cut_right_mean_quality", str(q_min),
        "--cut_right_window_size", "4",
    ]

    is_paired = ctx.fastq_r2 is not None
    if is_paired:
        cmd += [
            "-I", str(ctx.fastq_r2),
            "-O", str(out_r2),
        ]

    sh.catat(f"Mode: {'Paired-end' if is_paired else 'Single-end'}, ambang kualitas: Q{q_min}")
    sh.progres(25)

    # 5. Jalankan fastp lewat runner
    sh.run(cmd, nama="fastp")
    sh.progres(80)

    # 6. Verifikasi keluaran
    if not out_r1.exists() or out_r1.stat().st_size == 0:
        raise TahapGagal("fastp selesai tetapi berkas FASTQ hasil pemangkasan kosong atau tidak ada.")
    if is_paired and (not out_r2.exists() or out_r2.stat().st_size == 0):
        raise TahapGagal("fastp selesai tetapi berkas FASTQ R2 hasil pemangkasan kosong atau tidak ada.")
    if not json_report.exists():
        raise TahapGagal("fastp selesai tetapi laporan fastp.json tidak terbentuk.")

    # 7. Isi ctx.berkas (kontrak 3.3)
    ctx.berkas["reads_r1"] = out_r1
    if is_paired:
        ctx.berkas["reads_r2"] = out_r2
    ctx.berkas["fastp_json"] = json_report

    # 8. Ekstrak ringkasan awal untuk FR-14 (WP-4 akan memoles via ringkasan.py)
    try:
        data = json.loads(json_report.read_text(encoding="utf-8"))
        sebelum = data.get("summary", {}).get("before_filtering", {})
        sesudah = data.get("summary", {}).get("after_filtering", {})
        ctx.ringkasan["qc"] = {
            "reads_sebelum": sebelum.get("total_reads", 0),
            "reads_sesudah": sesudah.get("total_reads", 0),
            "q30_sebelum":   round(sebelum.get("q30_rate", 0.0) * 100, 2),
            "q30_sesudah":   round(sesudah.get("q30_rate", 0.0) * 100, 2),
        }
        sh.catat(
            f"QC selesai: {ctx.ringkasan['qc']['reads_sebelum']} -> "
            f"{ctx.ringkasan['qc']['reads_sesudah']} reads "
            f"(Q30: {ctx.ringkasan['qc']['q30_sebelum']}% -> {ctx.ringkasan['qc']['q30_sesudah']}%)"
        )
    except Exception as e:
        sh.catat(f"Peringatan: gagal membaca fastp.json untuk ringkasan: {e}", jenis="peringatan")

    sh.progres(100)

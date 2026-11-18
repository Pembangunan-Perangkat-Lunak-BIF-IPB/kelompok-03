"""Tahap 5: Filtering (WP-3 / Yafits).

Membaca : ctx.berkas["vcf_mentah"], ctx.parameter (qual_min, kedalaman_min)
Menulis : ctx.berkas["vcf_filter"] -> Path berkas filtered.vcf.gz

Aturan filter (BR-04, FR-06):
- qual_min     : Batas skor kualitas minimal (default 30).
- kedalaman_min: Kedalaman pembacaan minimal (default 10).
Ekspresi bcftools:
  QUAL >= {qual_min} && (FMT/DP >= {kedalaman_min} || INFO/DP >= {kedalaman_min})

Mencatat jumlah varian sebelum dan sesudah pemfilteran ke log_proses.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

try:
    from ..konteks import Konteks, TahapGagal
    from ..runner import Runner
except ImportError:
    from .._konteks_stub import Konteks, TahapGagal, Runner


def _hitung_varian(vcf_path: Path) -> int:
    """Hitung baris varian (tanpa header #) dalam berkas VCF terkompresi."""
    try:
        res = subprocess.run(
            ["bcftools", "view", "-H", str(vcf_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if res.returncode == 0:
            return len(res.stdout.splitlines())
    except Exception:
        pass
    return 0


def jalankan(ctx: Konteks, sh: Runner) -> None:
    """Jalankan bcftools view dengan ekspresi filter kualitas dan kedalaman."""
    # 1. Validasi input
    vcf_mentah = ctx.berkas.get("vcf_mentah")
    if not vcf_mentah or not Path(vcf_mentah).exists():
        raise TahapGagal("Berkas VCF mentah dari tahap variant calling tidak ditemukan.")

    # 2. Ambil parameter filter (BR-04)
    param = ctx.parameter or {}
    q_min = param.get("qual_min", 30)
    dp_min = param.get("kedalaman_min", 10)

    out_vcf = ctx.kerja / "filtered.vcf.gz"

    sh.catat(f"Memulai pemfilteran varian (QUAL >= {q_min}, Kedalaman/DP >= {dp_min})...")
    sh.progres(15)

    # 3. Hitung jumlah awal sebelum difilter
    n_sebelum = _hitung_varian(Path(vcf_mentah))
    sh.catat(f"Jumlah varian sebelum pemfilteran: {n_sebelum} varian.")
    sh.progres(30)

    # 4. Bangun ekspresi filter yang tangguh (FMT/DP || INFO/DP)
    expr = f"QUAL>={q_min} && (FMT/DP>={dp_min} || INFO/DP>={dp_min})"

    cmd_filter = [
        "bcftools", "view",
        "-i", expr,
        "-Oz",
        "-o", str(out_vcf),
        str(vcf_mentah),
    ]

    sh.run(cmd_filter, nama="bcftools view (filter)")
    sh.progres(75)

    # 5. Validasi berkas hasil filter
    if not out_vcf.exists():
        raise TahapGagal("Tahap filtering selesai tetapi berkas filtered.vcf.gz tidak terbentuk.")

    # 6. Buat indeks VCF (.tbi / .csi)
    sh.catat("Membuat indeks VCF terfilter dengan bcftools index...")
    sh.run(["bcftools", "index", "-f", str(out_vcf)], nama="bcftools index")
    sh.progres(90)

    # 7. Hitung jumlah varian setelah difilter
    n_sesudah = _hitung_varian(out_vcf)
    sh.catat(
        f"Pemfilteran varian selesai: {n_sesudah}/{n_sebelum} varian lolos ambang batas "
        f"(QUAL >= {q_min}, DP >= {dp_min})."
    )

    # 8. Isi ctx.berkas sesuai kontrak 3.3
    ctx.berkas["vcf_filter"] = out_vcf
    sh.progres(100)

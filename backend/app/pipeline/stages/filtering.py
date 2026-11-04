"""Tahap 5: Filtering VCF (WP-3 Yafits).

Menerapkan penyaringan kualitas (qual_min) dan kedalaman pembacaan (kedalaman_min)
pada berkas VCF mentah sesuai dokumen spesifikasi PEMETAAN_PARAMETER.md.
"""
import gzip
from pathlib import Path
from typing import Any

try:
    from ..konteks import Konteks, TahapGagal
except (ImportError, ValueError):
    try:
        from app.pipeline.konteks import Konteks, TahapGagal
    except (ImportError, ValueError):
        from konteks import Konteks, TahapGagal


def _hitung_varian(vcf_path: Path) -> int:
    """Menghitung jumlah rekaman varian (baris non-header) dalam berkas VCF / VCF.gz."""
    if not vcf_path.exists():
        return 0
    op = gzip.open if vcf_path.suffix == ".gz" else open
    count = 0
    try:
        with op(vcf_path, "rt", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line and not line.startswith("#"):
                    count += 1
    except Exception:
        pass
    return count


def jalankan(ctx: Konteks, sh: Any) -> None:
    """Jalankan filtering varian berdasarkan QUAL dan FMT/DP.

    Membaca: ctx.berkas['vcf_mentah'], ctx.parameter
    Menulis : ctx.berkas['vcf_filter']
    """
    raw_vcf = ctx.berkas.get("vcf_mentah")
    if not raw_vcf or not Path(raw_vcf).exists():
        raise TahapGagal("Berkas VCF mentah tidak ditemukan untuk tahap filtering.")

    p = ctx.parameter
    q_min = float(p.get("qual_min", 30))
    dp_min = int(p.get("kedalaman_min", 10))

    k = ctx.kerja
    filtered_vcf = k / "filtered.vcf.gz"

    sh.catat(f"Menyaring varian dengan batas QUAL >= {q_min} dan kedalaman FMT/DP >= {dp_min}...", jenis="info")
    sh.progres(20)

    # Ekspresi filter biologis standar (R8)
    filter_expr = f"QUAL>={q_min} && FMT/DP>={dp_min}"

    cmd_filter = [
        "bcftools", "view",
        "-i", filter_expr,
        "-Oz",
        "-o", str(filtered_vcf),
        str(raw_vcf),
    ]
    sh.run(cmd_filter, nama="bcftools_filter")

    if not filtered_vcf.exists():
        raise TahapGagal("Penyaringan selesai tetapi berkas filtered.vcf.gz tidak terbentuk.")

    sh.progres(70)
    sh.catat("Membuat indeks VCF terfilter (bcftools index)...", jenis="info")

    cmd_index = ["bcftools", "index", "-f", str(filtered_vcf)]
    sh.run(cmd_index, nama="bcftools_index_filtered")

    # Hitung jumlah varian sebelum vs sesudah filter
    n_sebelum = _hitung_varian(raw_vcf)
    n_sesudah = _hitung_varian(filtered_vcf)

    sh.progres(100)
    sh.catat(
        f"Tahap Filtering selesai: {n_sesudah} dari {n_sebelum} varian lolos filter (QUAL>={q_min}, DP>={dp_min}).",
        jenis="berhasil",
    )

    ctx.berkas["vcf_filter"] = filtered_vcf


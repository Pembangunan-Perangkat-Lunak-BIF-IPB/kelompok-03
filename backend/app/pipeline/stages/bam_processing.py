"""Tahap 3: Pemrosesan BAM (WP-2).

Mengurutkan (sort) dan mengindeks (index) berkas BAM hasil alignment,
serta menjalankan 'samtools flagstat' untuk ringkasan alignment FR-15 (WP-4).
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
    """Jalankan sort, index, dan flagstat pada BAM.

    Membaca: ctx.berkas['bam_mentah']
    Menulis : ctx.berkas['bam'], ctx.berkas['flagstat']
    """
    bam_mentah = ctx.berkas.get("bam_mentah")
    if not bam_mentah or not Path(bam_mentah).exists():
        raise TahapGagal("Berkas BAM mentah tidak ditemukan untuk tahap pemrosesan BAM.")

    threads = str(ctx.threads)
    sorted_bam = ctx.kerja / "sorted.bam"
    flagstat_txt = ctx.kerja / "flagstat.txt"

    sh.catat("Mengurutkan berkas BAM (samtools sort)...", jenis="info")
    sh.progres(20)

    # 1. samtools sort
    cmd_sort = [
        "samtools", "sort",
        "-@", threads,
        "-o", str(sorted_bam),
        str(bam_mentah)
    ]
    sh.run(cmd_sort, nama="samtools_sort")

    if not sorted_bam.exists() or sorted_bam.stat().st_size == 0:
        raise TahapGagal("Pengurutan BAM gagal: berkas sorted.bam tidak terbentuk atau kosong.")

    sh.progres(60)
    sh.catat("Membuat indeks BAM (samtools index)...", jenis="info")

    # 2. samtools index
    cmd_index = [
        "samtools", "index",
        str(sorted_bam)
    ]
    sh.run(cmd_index, nama="samtools_index")

    bai_file = Path(str(sorted_bam) + ".bai")
    if not bai_file.exists():
        raise TahapGagal("Indeks BAM (.bai) tidak berhasil dibuat.")

    sh.progres(80)
    sh.catat("Menghitung statistik keterbacaan (samtools flagstat)...", jenis="info")

    # 3. samtools flagstat untuk ringkasan FR-15 (WP-4)
    cmd_flagstat = [
        "samtools", "flagstat",
        "-@", threads,
        str(sorted_bam)
    ]
    sh.run(cmd_flagstat, stdout=flagstat_txt, nama="samtools_flagstat")

    if not flagstat_txt.exists():
        raise TahapGagal("Keluaran samtools flagstat tidak berhasil disimpan.")

    # Simpan ke konteks berkas untuk tahap selanjutnya
    ctx.berkas["bam"] = sorted_bam
    ctx.berkas["flagstat"] = flagstat_txt

    # Bersihkan bam mentah jika sudah sukses diurutkan guna menghemat disk
    try:
        if Path(bam_mentah).exists() and Path(bam_mentah) != sorted_bam:
            Path(bam_mentah).unlink()
    except OSError:
        pass

    sh.progres(100)
    sh.catat("Tahap Pemrosesan BAM selesai.", jenis="berhasil")

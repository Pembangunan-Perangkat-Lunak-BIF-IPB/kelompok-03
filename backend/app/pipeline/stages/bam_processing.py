"""Tahap 3: Pemrosesan BAM (WP-2 / Dhafin).

Membaca : ctx.berkas["bam_mentah"]
Menulis : ctx.berkas["bam"]              -> BAM terurut (sorted.bam)
          ctx.berkas["flagstat_txt"]     -> String teks flagstat (untuk parser WP-4)
          ctx.berkas["flagstat_path"]    -> Path berkas flagstat.txt
Ringkasan: ctx.ringkasan["alignment"]    -> {total_reads, reads_teralign, persen_teralign}

Urutan operasi:
1. samtools sort -@ T -o sorted.bam bam_mentah
2. samtools index sorted.bam            -> sorted.bam.bai
3. samtools flagstat sorted.bam         -> simpan teks ke ctx.berkas["flagstat_txt"]
4. Ekstrak ringkasan awal untuk FR-15 (WP-4 akan memoles via ringkasan.py)
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

try:
    from ..konteks import Konteks, TahapGagal
    from ..runner import Runner
except ImportError:
    from .._konteks_stub import Konteks, TahapGagal, Runner  # fallback WP-2


def _parse_flagstat_sederhana(teks: str) -> dict:
    """Ekstraksi dasar total reads, mapped reads, dan persen mapping dari teks flagstat.
    Parser definitif tetap berada di WP-4 (ringkasan.py / Abid).
    """
    total = 0
    mapped = 0
    persen = 0.0

    # Pola flagstat standar samtools:
    # 1000 + 0 in total (QC-passed reads + QC-failed reads)
    # 950 + 0 mapped (95.00% : N/A)
    m_total = re.search(r"^(\d+)\s*\+\s*\d+\s+in total", teks, re.MULTILINE)
    if m_total:
        total = int(m_total.group(1))

    m_mapped = re.search(r"^(\d+)\s*\+\s*\d+\s+mapped\s+\(([\d.]+)%", teks, re.MULTILINE)
    if m_mapped:
        mapped = int(m_mapped.group(1))
        persen = float(m_mapped.group(2))
    elif total > 0 and mapped > 0:
        persen = round(mapped / total * 100, 2)

    return {
        "total_reads": total,
        "reads_teralign": mapped,
        "persen_teralign": persen,
    }


def jalankan(ctx: Konteks, sh: Runner) -> None:
    """Urutkan BAM, buat indeks .bai, dan jalankan flagstat."""
    # 1. Validasi input dari tahap alignment
    bam_mentah = ctx.berkas.get("bam_mentah")
    if not bam_mentah or not Path(bam_mentah).exists():
        raise TahapGagal("Berkas BAM mentah dari tahap alignment tidak ditemukan.")

    threads = str(max(1, ctx.threads))
    sorted_bam = ctx.kerja / "sorted.bam"
    flagstat_file = ctx.kerja / "flagstat.txt"

    sh.catat(f"Mengurutkan BAM dengan samtools sort (threads: {threads})...")
    sh.progres(10)

    # 2. samtools sort
    cmd_sort = [
        "samtools", "sort",
        "-@", threads,
        "-o", str(sorted_bam),
        str(bam_mentah),
    ]
    sh.run(cmd_sort, nama="samtools sort")
    sh.progres(50)

    # 3. Validasi hasil sort
    if not sorted_bam.exists() or sorted_bam.stat().st_size == 0:
        raise TahapGagal("samtools sort selesai tetapi berkas BAM terurut kosong atau tidak ada.")

    # Hapus BAM mentah untuk menghemat ruang (opsional, aman karena sudah di-sort)
    try:
        Path(bam_mentah).unlink(missing_ok=True)
    except Exception:
        pass

    # 4. samtools index
    sh.catat("Membuat indeks BAM dengan samtools index...")
    cmd_index = ["samtools", "index", str(sorted_bam)]
    sh.run(cmd_index, nama="samtools index")
    sh.progres(75)

    bai_file = ctx.kerja / "sorted.bam.bai"
    bai_alt = ctx.kerja / "sorted.bai"
    if not bai_file.exists() and not bai_alt.exists():
        raise TahapGagal("samtools index selesai tetapi berkas indeks .bai tidak ditemukan.")

    # 5. samtools flagstat (menghasilkan metrik alignment untuk FR-15)
    sh.catat("Menjalankan samtools flagstat untuk statistik alignment...")
    try:
        res = subprocess.run(
            ["samtools", "flagstat", str(sorted_bam)],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            raise TahapGagal(f"samtools flagstat gagal: {res.stderr[-300:]}")
        teks_flagstat = res.stdout
    except FileNotFoundError:
        raise TahapGagal("Perangkat 'samtools' tidak ditemukan saat menjalankan flagstat.")

    # Simpan teks flagstat ke disk dan ke ctx.berkas
    flagstat_file.write_text(teks_flagstat, encoding="utf-8")
    ctx.berkas["flagstat_txt"] = teks_flagstat
    ctx.berkas["flagstat_path"] = flagstat_file

    # 6. Parse ringkasan alignment awal (kontrak 3.4)
    ringkasan_aln = _parse_flagstat_sederhana(teks_flagstat)
    ctx.ringkasan["alignment"] = ringkasan_aln
    sh.catat(
        f"Alignment stat: {ringkasan_aln['reads_teralign']}/{ringkasan_aln['total_reads']} reads "
        f"teralign ({ringkasan_aln['persen_teralign']}%)"
    )
    sh.progres(95)

    # 7. Isi ctx.berkas (kontrak 3.3 — input untuk variant_calling milik WP-3)
    ctx.berkas["bam"] = sorted_bam
    sh.catat(f"Pemrosesan BAM selesai -> {sorted_bam.name} + indeks .bai")
    sh.progres(100)

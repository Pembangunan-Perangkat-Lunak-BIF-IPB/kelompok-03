"""Tahap 2: Alignment (WP-2).

Menjalankan bwa mem untuk perataan sekuens ke genom referensi.
Menyelesaikan isu R3: Sanitasi nama sampel untuk tag @RG.
Menyelesaikan isu R4: Mengalirkan keluaran BWA langsung ke format BAM terkompresi
                      guna menghemat ruang penyimpanan dan I/O disk.
"""
from pathlib import Path
import re
from typing import Any

try:
    from ..konteks import Konteks, TahapGagal
except (ImportError, ValueError):
    try:
        from app.pipeline.konteks import Konteks, TahapGagal
    except (ImportError, ValueError):
        from konteks import Konteks, TahapGagal


def _sanitasi_string_rg(teks: str) -> str:
    """Membersihkan string untuk tag Read Group agar tidak mengandung tab, spasi, atau simbol berbahaya."""
    if not teks:
        return "SAMPLE"
    bersih = re.sub(r"[^A-Za-z0-9_.-]", "_", str(teks).strip())
    return bersih or "SAMPLE"


def jalankan(ctx: Konteks, sh: Any) -> None:
    """Jalankan alignment menggunakan BWA-MEM dan konversi langsung ke BAM mentah.

    Membaca: ctx.berkas['reads_r1'], ctx.berkas.get('reads_r2'), ctx.referensi
    Menulis : ctx.berkas['bam_mentah']
    """
    ref = ctx.referensi
    if not ref or not Path(ref).exists():
        raise TahapGagal(f"Berkas genom referensi tidak ditemukan: {ref}")

    r1 = ctx.berkas.get("reads_r1")
    if not r1 or not Path(r1).exists():
        raise TahapGagal("Berkas reads R1 hasil QC tidak ditemukan untuk tahap alignment.")

    r2 = ctx.berkas.get("reads_r2")
    is_paired = bool(r2 and Path(r2).exists())

    threads = str(ctx.threads)
    bam_mentah = ctx.kerja / "aln_raw.bam"

    # Sanitasi tag Read Group (R3)
    safe_sm = _sanitasi_string_rg(ctx.nama_sampel)
    safe_id = _sanitasi_string_rg(str(ctx.id_sampel))
    rg_tag = f"@RG\\tID:{safe_id}\\tSM:{safe_sm}\\tPL:ILLUMINA\\tLB:lib_{safe_id}"

    reads = [str(r1)]
    if is_paired:
        reads.append(str(r2))

    cmd_bwa = [
        "bwa", "mem",
        "-t", threads,
        "-R", rg_tag,
        str(ref),
        *reads
    ]

    cmd_view = [
        "samtools", "view",
        "-@", threads,
        "-b",
        "-o", str(bam_mentah)
    ]

    sh.catat(f"Menyelaraskan sekuens sampel '{safe_sm}' ke referensi...", jenis="info")
    sh.progres(20)

    # Efisiensi I/O (R4): Pipe langsung BWA-MEM ke samtools view jika didukung Runner
    if hasattr(sh, "run_pipe"):
        sh.run_pipe(cmd_bwa, cmd_view, nama="bwa_mem_piped")
    else:
        import subprocess
        sh.catat("$ " + " ".join(cmd_bwa) + " | " + " ".join(cmd_view), jenis="berjalan")
        try:
            p_bwa = subprocess.Popen(cmd_bwa, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_view = subprocess.Popen(cmd_view, stdin=p_bwa.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_bwa.stdout.close()
            _, err_view = p_view.communicate()
            _, err_bwa = p_bwa.communicate()

            if p_bwa.returncode != 0:
                raise TahapGagal(f"bwa mem gagal (kode {p_bwa.returncode}): {err_bwa.decode('utf-8', errors='replace')[-400:]}")
            if p_view.returncode != 0:
                raise TahapGagal(f"samtools view gagal (kode {p_view.returncode}): {err_view.decode('utf-8', errors='replace')[-400:]}")
        except FileNotFoundError as e:
            raise TahapGagal(f"Perangkat tidak terpasang di sistem: {e}")

    if not bam_mentah.exists() or bam_mentah.stat().st_size == 0:
        raise TahapGagal("Proses alignment selesai tetapi berkas BAM mentah tidak terbentuk atau kosong.")

    ctx.berkas["bam_mentah"] = bam_mentah
    sh.progres(100)
    sh.catat("Tahap Alignment selesai.", jenis="berhasil")

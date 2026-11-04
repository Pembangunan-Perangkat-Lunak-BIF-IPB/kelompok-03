"""Tahap 4: Variant Calling (WP-3 Yafits).

Menjalankan bcftools mpileup dan bcftools call untuk identifikasi varian,
serta normalisasi alel majemuk (bcftools norm -m- -f) guna mengatasi risiko R9
agar parse_vcf tidak kehilangan alel varian alternatif.
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
    """Jalankan variant calling (mpileup | call) dan normalisasi alel (norm -m-).

    Membaca: ctx.berkas['bam'], ctx.referensi
    Menulis : ctx.berkas['vcf_mentah']
    """
    bam = ctx.berkas.get("bam")
    if not bam or not Path(bam).exists():
        raise TahapGagal("Berkas BAM terurut tidak ditemukan untuk tahap variant calling.")

    ref = ctx.referensi
    if not ref or not Path(ref).exists():
        raise TahapGagal(f"Berkas genom referensi tidak ditemukan: {ref}")

    k = ctx.kerja
    raw_vcf = k / "raw.vcf.gz"

    sh.catat("Memulai variant calling (bcftools mpileup | call)...", jenis="info")
    sh.progres(20)

    # 1. mpileup: menghasilkan informasi tumpukan read dengan tag FORMAT/DP
    cmd_mpileup = [
        "bcftools", "mpileup",
        "-f", str(ref),
        "-a", "FORMAT/DP",
        "-Ou",
        str(bam),
    ]

    # 2. call: memanggil varian germline (-mv)
    cmd_call = [
        "bcftools", "call",
        "-mv",
        "-Ou",
    ]

    # 3. norm: memecah varian multi-alelik (-m-) dan normalisasi indel (-f ref) (R9)
    cmd_norm = [
        "bcftools", "norm",
        "-m-",
        "-f", str(ref),
        "-Oz",
        "-o", str(raw_vcf),
    ]

    # Eksekusi pipeline menggunakan subprocess piping aman
    if hasattr(sh, "run_pipe_three"):
        sh.run_pipe_three(cmd_mpileup, cmd_call, cmd_norm, nama="bcftools_calling_norm")
    else:
        import subprocess
        sh.catat("$ bcftools mpileup ... | bcftools call -mv ... | bcftools norm -m- ...", jenis="berjalan")
        try:
            p_mp = subprocess.Popen(cmd_mpileup, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_call = subprocess.Popen(cmd_call, stdin=p_mp.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_mp.stdout.close()

            p_norm = subprocess.Popen(cmd_norm, stdin=p_call.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_call.stdout.close()

            _, err_norm = p_norm.communicate()
            _, err_call = p_call.communicate()
            _, err_mp = p_mp.communicate()

            if p_mp.returncode != 0:
                raise TahapGagal(f"bcftools mpileup gagal (kode {p_mp.returncode}): {err_mp.decode('utf-8', errors='replace')[-400:]}")
            if p_call.returncode != 0:
                raise TahapGagal(f"bcftools call gagal (kode {p_call.returncode}): {err_call.decode('utf-8', errors='replace')[-400:]}")
            if p_norm.returncode != 0:
                raise TahapGagal(f"bcftools norm gagal (kode {p_norm.returncode}): {err_norm.decode('utf-8', errors='replace')[-400:]}")
        except FileNotFoundError as e:
            raise TahapGagal(f"Perangkat tidak terpasang di sistem: {e}")

    if not raw_vcf.exists() or raw_vcf.stat().st_size == 0:
        raise TahapGagal("Tahap variant calling selesai tetapi berkas raw.vcf.gz tidak terbentuk atau kosong.")

    sh.progres(80)
    sh.catat("Membuat indeks VCF mentah (bcftools index)...", jenis="info")

    # Indeks berkas VCF mentah
    cmd_index = ["bcftools", "index", "-f", str(raw_vcf)]
    sh.run(cmd_index, nama="bcftools_index_raw")

    ctx.berkas["vcf_mentah"] = raw_vcf
    sh.progres(100)
    sh.catat("Tahap Variant Calling selesai.", jenis="berhasil")


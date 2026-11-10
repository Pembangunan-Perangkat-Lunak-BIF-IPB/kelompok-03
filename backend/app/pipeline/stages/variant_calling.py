"""Tahap 4: Variant Calling (WP-3 / Yafits).

Membaca : ctx.berkas["bam"], ctx.referensi
Menulis : ctx.berkas["vcf_mentah"] -> Path berkas raw.vcf.gz

Perangkat:
- bcftools mpileup : Membangkitkan kemungkinan genotipe dari alignment BAM.
- bcftools call    : Variant caller multialelik & rare-variant caller (-mv).
- bcftools norm    : Normalisasi varian multialelik (-m-) memecah multi-ALT menjadi
                     rekord terpisah sehingga parse_vcf tidak kehilangan varian kedua (Risiko R9).

Rantai eksekusi:
bcftools mpileup -f <ref> -a FORMAT/DP,FORMAT/AD -Ou <sorted.bam>
  | bcftools call -mv -Ou
  | bcftools norm -m- -Oz -o <raw.vcf.gz>
diikuti dengan:
bcftools index -f <raw.vcf.gz>
"""
from __future__ import annotations

import subprocess
from pathlib import Path

try:
    from ..konteks import Konteks, TahapGagal
    from ..runner import Runner
except ImportError:
    from .._konteks_stub import Konteks, TahapGagal, Runner


def jalankan(ctx: Konteks, sh: Runner) -> None:
    """Jalankan mpileup -> call -> norm untuk menghasilkan vcf_mentah."""
    # 1. Validasi input
    bam = ctx.berkas.get("bam")
    if not bam or not Path(bam).exists():
        raise TahapGagal("Berkas BAM terurut dari tahap pemrosesan BAM tidak ditemukan.")

    ref = ctx.referensi
    if not ref or not Path(ref).exists():
        raise TahapGagal(f"Berkas referensi tidak ditemukan: {getattr(ref, 'name', ref)}")

    sh.catat("Memulai variant calling dengan bcftools mpileup -> call -> norm...")
    sh.progres(10)

    out_vcf = ctx.kerja / "raw.vcf.gz"

    # Pastikan indeks referensi (.fai) tersedia
    fai_path = Path(str(ref) + ".fai")
    if not fai_path.exists():
        sh.catat("Membuat indeks referensi samtools faidx...")
        sh.run(["samtools", "faidx", str(ref)], nama="samtools faidx")

    sh.progres(25)

    # 2. Bangun perintah pipa: mpileup -> call -> norm
    cmd_mpileup = [
        "bcftools", "mpileup",
        "-f", str(ref),
        "-a", "FORMAT/DP,FORMAT/AD",
        "-Ou",
        str(bam),
    ]

    cmd_call = [
        "bcftools", "call",
        "-mv",
        "-Ou",
    ]

    cmd_norm = [
        "bcftools", "norm",
        "-m-",
        "-Oz",
        "-o", str(out_vcf),
    ]

    sh.catat(f"Menjalankan pipa bcftools mpileup | call -mv | norm -m- -> {out_vcf.name}")

    # 3. Eksekusi pipa berantai 3 tahap secara streaming tanpa file VCF mentah raksasa di disk
    p_mp = None
    p_call = None
    p_norm = None
    try:
        p_mp = subprocess.Popen(
            cmd_mpileup,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p_call = subprocess.Popen(
            cmd_call,
            stdin=p_mp.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p_norm = subprocess.Popen(
            cmd_norm,
            stdin=p_call.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        p_mp.stdout.close()
        p_call.stdout.close()

        norm_out, norm_err = p_norm.communicate()
        call_out, call_err = p_call.communicate()
        mp_out, mp_err = p_mp.communicate()

        if p_mp.returncode != 0:
            err = (mp_err or b"").decode(errors="replace")[-300:]
            raise TahapGagal(f"bcftools mpileup gagal (kode {p_mp.returncode}): {err}")
        if p_call.returncode != 0:
            err = (call_err or b"").decode(errors="replace")[-300:]
            raise TahapGagal(f"bcftools call gagal (kode {p_call.returncode}): {err}")
        if p_norm.returncode != 0:
            err = (norm_err or b"").decode(errors="replace")[-300:]
            raise TahapGagal(f"bcftools norm gagal (kode {p_norm.returncode}): {err}")

    except FileNotFoundError as e:
        raise TahapGagal(f"Perangkat 'bcftools' tidak ditemukan di lingkungan sistem: {e}")
    finally:
        for p in (p_mp, p_call, p_norm):
            if p and p.poll() is None:
                p.kill()

    sh.progres(80)

    # 4. Validasi hasil dan buat indeks VCF (.tbi / .csi)
    if not out_vcf.exists() or out_vcf.stat().st_size == 0:
        raise TahapGagal("bcftools variant calling selesai tetapi berkas raw.vcf.gz kosong atau tidak terbentuk.")

    sh.catat("Membuat indeks VCF dengan bcftools index...")
    sh.run(["bcftools", "index", "-f", str(out_vcf)], nama="bcftools index")
    sh.progres(95)

    # 5. Isi ctx.berkas sesuai kontrak 3.3
    ctx.berkas["vcf_mentah"] = out_vcf
    sh.catat(f"Variant calling selesai -> {out_vcf.name} ({out_vcf.stat().st_size} bytes)")
    sh.progres(100)

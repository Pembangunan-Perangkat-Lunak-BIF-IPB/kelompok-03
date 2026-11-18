"""Tahap 4: Variant Calling (WP-3 / Yafits).

Membaca : ctx.berkas["bam"], ctx.referensi, ctx.anotasi (opsional: .gtf/.gff/.bed)
Menulis : ctx.berkas["vcf_mentah"] -> Path berkas raw.vcf.gz

Perangkat:
- bcftools mpileup : Membangkitkan kemungkinan genotipe dari alignment BAM.
                     Otomatis memakai filter target (-R) jika tersedia berkas .bed
                     atau berkas anotasi .gtf/.gff (diekstrak menjadi .exons.bed).
- bcftools call    : Variant caller multialelik & rare-variant caller (-mv).
- bcftools norm    : Normalisasi varian multialelik (-m-) memecah multi-ALT menjadi
                     rekord terpisah sehingga parse_vcf tidak kehilangan varian kedua (Risiko R9).
"""
from __future__ import annotations

import gzip
import subprocess
from pathlib import Path

try:
    from ..konteks import Konteks, TahapGagal
    from ..runner import Runner
except ImportError:
    from .._konteks_stub import Konteks, TahapGagal, Runner


def _ambil_kontig_fai(fai_path: Path) -> set[str]:
    """Baca daftar nama kromosom/kontig dari berkas referensi .fai."""
    kontigs: set[str] = set()
    if not fai_path.exists():
        return kontigs
    for baris in fai_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if baris.strip():
            kontigs.add(baris.split("\t", 1)[0])
    return kontigs


def _selaraskan_nama_kontig(chrom: str, kontig_ref: set[str]) -> str:
    """Sesuaikan awalan 'chr' pada BED agar cocok dengan nama kontig di FASTA referensi."""
    if not kontig_ref or chrom in kontig_ref:
        return chrom
    if chrom.startswith("chr") and chrom[3:] in kontig_ref:
        return chrom[3:]
    if not chrom.startswith("chr") and f"chr{chrom}" in kontig_ref:
        return f"chr{chrom}"
    return chrom


def _ekstrak_bed_dari_gtf(gtf_path: Path, bed_out: Path, kontig_ref: set[str]) -> int:
    """Ekstrak fitur 'exon' dari GTF/GFF ke format BED (0-based), urutkan, dan gabung tumpang-tindih."""
    interval_per_chr: dict[str, list[tuple[int, int]]] = {}
    opener = gzip.open if gtf_path.name.lower().endswith(".gz") else open

    with opener(gtf_path, "rt", encoding="utf-8", errors="replace") as fh:
        for baris in fh:
            if not baris or baris.startswith("#"):
                continue
            kolom = baris.rstrip("\r\n").split("\t")
            if len(kolom) < 5 or kolom[2].lower() != "exon":
                continue
            try:
                # GTF/GFF menggunakan koordinat 1-based inclusive; BED menggunakan 0-based half-open
                start_0 = max(0, int(kolom[3]) - 1)
                end_1 = int(kolom[4])
            except ValueError:
                continue
            if end_1 <= start_0:
                continue

            chrom = _selaraskan_nama_kontig(kolom[0], kontig_ref)
            interval_per_chr.setdefault(chrom, []).append((start_0, end_1))

    total_region = 0
    tmp_bed = bed_out.with_suffix(".bed.tmp")
    with tmp_bed.open("w", encoding="utf-8") as out:
        for chrom in sorted(interval_per_chr.keys()):
            intervals = sorted(interval_per_chr[chrom])
            merged: list[tuple[int, int]] = []
            for s, e in intervals:
                if not merged or s > merged[-1][1]:
                    merged.append((s, e))
                else:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            for s, e in merged:
                out.write(f"{chrom}\t{s}\t{e}\n")
                total_region += 1

    if total_region > 0:
        tmp_bed.replace(bed_out)
    else:
        tmp_bed.unlink(missing_ok=True)

    return total_region


def _siapkan_target_bed(ctx: Konteks, fai_path: Path, sh: Runner) -> Path | None:
    """Deteksi atau bangun berkas target .bed jika tersedia anotasi GTF/GFF atau berkas BED."""
    # 1. Cek jika parameter atau ctx.anotasi menunjuk ke berkas .bed atau .gtf/.gff
    kandidat = ctx.anotasi
    if not kandidat:
        return None

    anot_path = Path(kandidat)
    if not anot_path.exists():
        return None

    nama_lower = anot_path.name.lower()

    # Kasus A: Pengguna langsung memilih berkas .bed / .bed.gz
    if nama_lower.endswith((".bed", ".bed.gz")):
        sh.catat(f"Menggunakan berkas target region BED: {anot_path.name}")
        return anot_path

    # Kasus B: Pengguna memilih berkas .gtf / .gff / .gff3 (terkompresi maupun tidak)
    if nama_lower.endswith((".gtf", ".gff", ".gff3", ".gtf.gz", ".gff.gz", ".gff3.gz")):
        bed_cache = anot_path.parent / f"{anot_path.name}.exons.bed"
        kontig_ref = _ambil_kontig_fai(fai_path)

        perlu_ekstrak = (
            not bed_cache.exists()
            or bed_cache.stat().st_size == 0
            or bed_cache.stat().st_mtime < anot_path.stat().st_mtime
        )
        if perlu_ekstrak:
            sh.catat(f"Mengekstrak koordinat ekson dari '{anot_path.name}' ke format BED...")
            jumlah = _ekstrak_bed_dari_gtf(anot_path, bed_cache, kontig_ref)
            if jumlah == 0:
                sh.catat(
                    f"Tidak ditemukan fitur 'exon' di {anot_path.name}; pemindaian dilakukan pada seluruh referensi.",
                    jenis="peringatan",
                )
                return None
            sh.catat(f"Berhasil mengekstrak {jumlah} region ekson -> {bed_cache.name}")
        else:
            sh.catat(f"Menggunakan cache target ekson yang sudah tersedia: {bed_cache.name}")

        return bed_cache

    # Kasus C: Anotasi berformat VCF (dbSNP/ClinVar) -> jangan jadikan target BED
    return None


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

    sh.progres(20)

    # 2. Siapkan target region (.bed) jika tersedia dari GTF/GFF atau BED
    target_bed = _siapkan_target_bed(ctx, fai_path, sh)
    sh.progres(30)

    # 3. Bangun perintah pipa: mpileup -> call -> norm
    cmd_mpileup = [
        "bcftools", "mpileup",
        "-f", str(ref),
        "-a", "FORMAT/DP,FORMAT/AD",
    ]
    if target_bed and target_bed.exists():
        cmd_mpileup.extend(["-R", str(target_bed)])
    cmd_mpileup.extend(["-Ou", str(bam)])

    cmd_call = [
        "bcftools", "call",
        "-mv",
        "-Ou",
    ]
    # Dukungan opsional ploidy (default bcftools adalah 2 / diploid jika tidak disetel)
    ploidy = (ctx.parameter or {}).get("ploidy")
    if ploidy in (1, 2, "1", "2"):
        cmd_call.extend(["--ploidy", str(ploidy)])

    cmd_norm = [
        "bcftools", "norm",
        "-m-",
        "-Oz",
        "-o", str(out_vcf),
    ]

    info_target = f" (target: {target_bed.name})" if target_bed else " (seluruh referensi)"
    sh.catat(f"Menjalankan pipa bcftools mpileup | call -mv | norm -m-{info_target} -> {out_vcf.name}")

    # 4. Eksekusi pipa berantai 3 tahap secara streaming tanpa file VCF mentah raksasa di disk
    p_mp = None
    p_call = None
    p_norm = None
    try:
        p_mp = subprocess.Popen(
            cmd_mpileup,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        p_call = subprocess.Popen(
            cmd_call,
            stdin=p_mp.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
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
        p_call.wait()
        p_mp.wait()
        call_err = None
        mp_err = None

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

    # 5. Validasi hasil dan buat indeks VCF (.tbi / .csi)
    if not out_vcf.exists() or out_vcf.stat().st_size == 0:
        raise TahapGagal("bcftools variant calling selesai tetapi berkas raw.vcf.gz kosong atau tidak terbentuk.")

    sh.catat("Membuat indeks VCF dengan bcftools index...")
    sh.run(["bcftools", "index", "-f", str(out_vcf)], nama="bcftools index")
    sh.progres(95)

    # 6. Isi ctx.berkas sesuai kontrak 3.3
    ctx.berkas["vcf_mentah"] = out_vcf
    sh.catat(f"Variant calling selesai -> {out_vcf.name} ({out_vcf.stat().st_size} bytes)")
    sh.progres(100)
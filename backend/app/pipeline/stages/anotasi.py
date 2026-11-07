"""Tahap 6: Anotasi VCF (WP-3 Yafits).

Menganotasi berkas VCF terfilter menggunakan basis data varian VCF (seperti dbSNP/ClinVar).
Menyelesaikan isu R10: Deteksi dan normalisasi ketidakcocokan gaya penamaan kontig (mis. chr1 vs 1)
menggunakan tabel pemetaan --rename-chrs agar anotasi gen menempel dengan benar.
Menyelesaikan isu K5: Melewati format non-VCF (GTF/GFF) secara aman dengan status 'dilewati'.
"""
import gzip
from pathlib import Path
from typing import Any, Optional

try:
    from ..konteks import Konteks, TahapGagal
except (ImportError, ValueError):
    try:
        from app.pipeline.konteks import Konteks, TahapGagal
    except (ImportError, ValueError):
        from konteks import Konteks, TahapGagal


def _ambil_daftar_kromosom(vcf_path: Path, max_baris: int = 100) -> set[str]:
    """Mengambil sampel daftar nama kromosom dari baris data VCF."""
    chrs = set()
    if not vcf_path.exists():
        return chrs
    op = gzip.open if vcf_path.suffix == ".gz" else open
    try:
        with op(vcf_path, "rt", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if parts:
                    chrs.add(parts[0])
                if len(chrs) >= 10:
                    break
    except Exception:
        pass
    return chrs


def _buat_tabel_pemetaan_chr(kerja: Path, chrs_sampel: set[str], chrs_anot: set[str]) -> Optional[Path]:
    """Membuat berkas pemetaan kromosom jika terdapat disparitas prefix 'chr'."""
    sampel_has_chr = any(c.startswith("chr") for c in chrs_sampel)
    anot_has_chr = any(c.startswith("chr") for c in chrs_anot)

    if sampel_has_chr == anot_has_chr:
        return None  # Konvensi sudah seragam

    map_file = kerja / "chr_rename_map.txt"
    lines = []

    # Daftar kromosom standar manusia
    daftar_chr = [str(i) for i in range(1, 23)] + ["X", "Y", "M", "MT"]
    if not anot_has_chr and sampel_has_chr:
        # Anotasi: 1, 2, ... -> Sampel butuh: chr1, chr2, ...
        # Format bcftools --rename-chrs: <nama_lama> <nama_baru>
        for c in daftar_chr:
            lines.append(f"{c}\tchr{c}\n")
        if "MT" in daftar_chr:
            lines.append("MT\tchrM\n")
    elif anot_has_chr and not sampel_has_chr:
        # Anotasi: chr1, chr2, ... -> Sampel butuh: 1, 2, ...
        for c in daftar_chr:
            lines.append(f"chr{c}\t{c}\n")
        lines.append("chrM\tMT\n")

    if lines:
        map_file.write_text("".join(lines), encoding="utf-8")
        return map_file
    return None


def jalankan(ctx: Konteks, sh: Any) -> Optional[str]:
    """Jalankan anotasi varian dari berkas VCF anotasi.

    Membaca: ctx.berkas['vcf_filter'], ctx.anotasi
    Menulis : ctx.berkas['vcf_akhir']
    Mengembalikan: 'dilewati' jika berkas anotasi tidak ada atau format non-VCF.
    """
    filtered_vcf = ctx.berkas.get("vcf_filter")
    if not filtered_vcf or not Path(filtered_vcf).exists():
        raise TahapGagal("Berkas VCF terfilter tidak ditemukan untuk tahap anotasi.")

    a = ctx.anotasi
    if not a or not Path(a).exists():
        ctx.berkas["vcf_akhir"] = filtered_vcf
        return "dilewati"

    # Keputusan K5: format non-VCF (GTF/GFF) dilewati dengan keterangan jelas
    nama_anot = a.name.lower()
    if not (nama_anot.endswith(".vcf") or nama_anot.endswith(".vcf.gz")):
        sh.catat(f"Format berkas anotasi '{a.name}' bukan VCF. Tahap anotasi dilewati.", jenis="info")
        ctx.berkas["vcf_akhir"] = filtered_vcf
        return "dilewati"

    k = ctx.kerja
    annotated_vcf = k / "annotated.vcf.gz"

    sh.catat("Mempersiapkan basis data anotasi varian...", jenis="info")
    sh.progres(20)

    # 1. Pastikan berkas anotasi memiliki indeks .tbi / .csi jika terkompresi
    is_compressed = a.name.lower().endswith((".vcf.gz", ".bcf"))
    if is_compressed:
        tbi = Path(str(a) + ".tbi")
        csi = Path(str(a) + ".csi")
        if not tbi.exists() and not csi.exists():
            try:
                sh.catat("Membuat indeks untuk berkas anotasi (bcftools index)...", jenis="info")
                sh.run(["bcftools", "index", "-f", str(a)], nama="bcftools_index_anot")
            except TahapGagal as err:
                sh.catat(f"Peringatan: Berkas anotasi tidak dapat diindeks ({err}). Mencoba membaca langsung...", jenis="info")

    sh.progres(40)

    # 2. Deteksi keselarasan nama kontig/kromosom (R10)
    chrs_sampel = _ambil_daftar_kromosom(filtered_vcf)
    chrs_anot = _ambil_daftar_kromosom(a)
    map_file = _buat_tabel_pemetaan_chr(k, chrs_sampel, chrs_anot)

    cmd_annot = [
        "bcftools", "annotate",
        "-a", str(a),
        "-c", "ID,INFO",
        "-Oz",
        "-o", str(annotated_vcf),
    ]

    if map_file and map_file.exists():
        sh.catat(f"Menyelaraskan nama kontig anotasi dengan sampel menggunakan {map_file.name}...", jenis="info")
        cmd_annot.extend(["--rename-chrs", str(map_file)])

    cmd_annot.append(str(filtered_vcf))

    sh.catat("Menjalankan anotasi varian (bcftools annotate)...", jenis="info")
    sh.progres(60)

    sh.run(cmd_annot, nama="bcftools_annotate")

    if not annotated_vcf.exists():
        raise TahapGagal("Tahap anotasi selesai tetapi berkas annotated.vcf.gz tidak terbentuk.")

    sh.progres(85)
    sh.catat("Membuat indeks VCF akhir...", jenis="info")

    cmd_index = ["bcftools", "index", "-f", str(annotated_vcf)]
    sh.run(cmd_index, nama="bcftools_index_annotated")

    ctx.berkas["vcf_akhir"] = annotated_vcf
    sh.progres(100)
    sh.catat("Tahap Anotasi selesai.", jenis="berhasil")
    return None


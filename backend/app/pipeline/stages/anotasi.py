"""Tahap 6: Anotasi (WP-3 / Yafits).

Membaca : ctx.berkas["vcf_filter"], ctx.anotasi (opsional / Path / None)
Menulis : ctx.berkas["vcf_akhir"] -> Path berkas annotated.vcf.gz (atau vcf_filter jika dilewati)

Ketentuan & Kasus Penanganan:
1. Jika berkas anotasi tidak disediakan (None), tahap dilewati secara anggun.
2. Jika berkas anotasi berformat non-VCF (misal .gtf, .gff, .bed), sesuai Keputusan K5
   tahap dilewati dengan pencatatan peringatan informatif di log.
3. Menyelaraskan nama kromosom (misal 'chr1' vs '1') antara VCF sampel dan database anotasi
   agar anotasi tidak gagal menempel secara senyap (Risiko R10).
4. Anotasi menambahkan ID (rsID) dan atribut INFO (GENE, GENEINFO) ke dalam VCF akhir.
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


def _ambil_kolom_anotasi_tersedia(anot_path: Path) -> list[str]:
    """Deteksi kolom dan tag INFO yang benar-benar ada di header berkas anotasi.
    bcftools annotate gagal jika field yang diminta di -c tidak terdefinisi di header (-h).
    """
    kolom = ["ID"]
    try:
        res = subprocess.run(
            ["bcftools", "view", "-h", str(anot_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            header = res.stdout
            if "##INFO=<ID=GENE," in header:
                kolom.append("INFO/GENE")
            if "##INFO=<ID=GENEINFO," in header:
                kolom.append("INFO/GENEINFO")
    except Exception:
        pass
    return kolom


def _ambil_kontig_vcf(vcf_path: Path) -> set[str]:
    """Ekstrak daftar nama kromosom/kontig yang ada dalam berkas VCF."""
    kontigs = set()
    try:
        res = subprocess.run(
            ["bcftools", "query", "-f", "%CHROM\\n", str(vcf_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if line.strip():
                    kontigs.add(line.strip())
    except Exception:
        pass
    return kontigs


def _buat_pemetaan_kromosom(kontig_sampel: set[str], kontig_anotasi: set[str], out_file: Path) -> bool:
    """Buat berkas pemetaan untuk bcftools annotate --rename-chrs jika terjadi perbedaan format chr."""
    perlu_mapping = False
    baris_map = []

    # Cek apakah satu memakai prefix 'chr' dan yang lain tidak
    for ks in kontig_sampel:
        if ks in kontig_anotasi:
            continue
        if ks.startswith("chr") and ks[3:] in kontig_anotasi:
            baris_map.append(f"{ks[3:]}\t{ks}")
            perlu_mapping = True
        elif not ks.startswith("chr") and f"chr{ks}" in kontig_anotasi:
            baris_map.append(f"chr{ks}\t{ks}")
            perlu_mapping = True

    if perlu_mapping and baris_map:
        out_file.write_text("\n".join(baris_map) + "\n", encoding="utf-8")
        return True
    return False


def jalankan(ctx: Konteks, sh: Runner) -> None:
    """Jalankan anotasi VCF jika berkas anotasi valid tersedia."""
    vcf_filter = ctx.berkas.get("vcf_filter")
    if not vcf_filter or not Path(vcf_filter).exists():
        raise TahapGagal("Berkas VCF terfilter dari tahap filtering tidak ditemukan.")

    anot = ctx.anotasi
    # Kasus 1: Anotasi tidak dipilih
    if not anot:
        sh.catat("Berkas referensi anotasi tidak dipilih. Tahap anotasi dilewati.", jenis="info")
        ctx.berkas["vcf_akhir"] = vcf_filter
        sh.progres(100)
        return

    anot_path = Path(anot)
    if not anot_path.exists():
        raise TahapGagal(f"Berkas anotasi yang dipilih tidak ditemukan pada sistem: {anot_path.name}")

    # Kasus 2: Format non-VCF (Keputusan K5)
    nama_lower = anot_path.name.lower()
    if not (nama_lower.endswith(".vcf") or nama_lower.endswith(".vcf.gz")):
        sh.catat(
            f"Format berkas anotasi '{anot_path.name}' bukan VCF (.vcf / .vcf.gz). "
            "Anotasi dilewati (dukungan GTF/GFF berada di luar cakupan saat ini).",
            jenis="peringatan",
        )
        ctx.berkas["vcf_akhir"] = vcf_filter
        sh.progres(100)
        return

    sh.catat(f"Mempersiapkan anotasi varian menggunakan database: {anot_path.name}...")
    sh.progres(20)

    # Pastikan berkas anotasi terindeks (.tbi / .csi)
    idx_tbi = Path(str(anot_path) + ".tbi")
    idx_csi = Path(str(anot_path) + ".csi")
    if not idx_tbi.exists() and not idx_csi.exists():
        sh.catat(f"Membuat indeks untuk database anotasi ({anot_path.name})...")
        sh.run(["bcftools", "index", "-f", str(anot_path)], nama="bcftools index anotasi")

    sh.progres(40)

    # 3. Penyelarasan format kromosom (Risiko R10)
    chrs_sampel = _ambil_kontig_vcf(Path(vcf_filter))
    chrs_anotasi = _ambil_kontig_vcf(anot_path)
    rename_file = ctx.kerja / "rename_chrs.tsv"

    # Evaluasi apakah ada kontig yang beririsan
    irisan_awal = chrs_sampel.intersection(chrs_anotasi)
    perlu_mapping = _buat_pemetaan_kromosom(chrs_sampel, chrs_anotasi, rename_file)

    # Deteksi field ID dan INFO yang benar-benar ada di file anotasi
    kolom_c = _ambil_kolom_anotasi_tersedia(anot_path)
    sh.catat(f"Field anotasi yang diterapkan: {', '.join(kolom_c)}")

    cmd_annotate = [
        "bcftools", "annotate",
        "-a", str(anot_path),
        "-c", ",".join(kolom_c),
    ]

    if perlu_mapping:
        sh.catat("Ditemukan perbedaan penamaan kromosom (chrX vs X). Menerapkan penyesuaian otomatis kontig.")
        cmd_annotate.extend(["--rename-chrs", str(rename_file)])
    elif not irisan_awal and chrs_sampel and chrs_anotasi:
        # Peringatan di log jika sama sekali tidak ada kontig yang cocok
        sh.catat(
            f"PERINGATAN: Tidak ada kromosom/kontig yang cocok antara sampel {list(chrs_sampel)[:5]} "
            f"dan berkas anotasi {list(chrs_anotasi)[:5]}. Anotasi kemungkinan tidak akan menempel.",
            jenis="peringatan",
        )

    out_vcf = ctx.kerja / "annotated.vcf.gz"
    cmd_annotate.extend(["-Oz", "-o", str(out_vcf), str(vcf_filter)])

    sh.catat("Menjalankan bcftools annotate...")
    sh.progres(60)

    sh.run(cmd_annotate, nama="bcftools annotate")
    sh.progres(85)

    if not out_vcf.exists() or out_vcf.stat().st_size == 0:
        raise TahapGagal("Tahap anotasi selesai tetapi berkas annotated.vcf.gz tidak terbentuk.")

    # Indeks VCF akhir
    sh.run(["bcftools", "index", "-f", str(out_vcf)], nama="bcftools index annotated")
    sh.progres(95)

    ctx.berkas["vcf_akhir"] = out_vcf
    sh.catat(f"Tahap anotasi selesai -> {out_vcf.name}")
    sh.progres(100)

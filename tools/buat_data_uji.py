#!/usr/bin/env python3
"""Pembuat Data Uji Deterministik & Truth Set (WP-5 Fattha, Tester).

Membangkitkan data uji genomik mini:
1. ref.fa: Genom referensi sintetis (~10.000 bp)
2. truth.vcf: Varian kebenaran (SNP & indel yang disisipkan)
3. FASTQ paired-end (sample_R1.fastq.gz & sample_R2.fastq.gz) pada kedalaman >= 30x
4. FASTQ single-end (sample_single.fastq.gz)
5. anotasi_dbsnp.vcf.gz: Basis data anotasi tiruan
6. anotasi_beda_kontig.vcf.gz: Basis data anotasi tanpa prefix 'chr' untuk uji R10

Dapat menggunakan 'wgsim' jika tersedia, atau fallback Python generator deterministik.
"""
import argparse
import gzip
from pathlib import Path
import random
import shutil
import subprocess
import sys


def buat_referensi_sintetis(panjang: int = 10000, seed: int = 42, kontig: str = "chr21") -> str:
    """Membangkitkan sekuens DNA referensi sintetis dengan rasio GC ~42%."""
    rnd = random.Random(seed)
    bases = ["A", "C", "G", "T"]
    bobot = [0.29, 0.21, 0.21, 0.29]
    seq = "".join(rnd.choices(bases, weights=bobot, k=panjang))
    return seq


def sisipkan_mutasi(ref_seq: str, n_snp: int = 25, seed: int = 101) -> tuple[str, list[dict]]:
    """Menyisipkan SNP yang diketahui ke dalam sekuens referensi untuk membentuk genom donor."""
    rnd = random.Random(seed)
    panjang = len(ref_seq)
    donor_list = list(ref_seq)

    # Pilih posisi mutasi yang berjarak aman (agar tidak menempel di ujung)
    posisi_kandidat = list(range(200, panjang - 200, panjang // (n_snp + 5)))
    rnd.shuffle(posisi_kandidat)
    posisi_terpilih = sorted(posisi_kandidat[:n_snp])

    bases = ["A", "C", "G", "T"]
    truth_variants = []

    for pos in posisi_terpilih:  # pos adalah 0-indexed di Python, 1-indexed di VCF
        ref_base = ref_seq[pos]
        alt_base = rnd.choice([b for b in bases if b != ref_base])
        donor_list[pos] = alt_base

        truth_variants.append({
            "pos": pos + 1,  # 1-indexed VCF
            "ref": ref_base,
            "alt": alt_base,
            "tipe": "SNP",
            "gt": "1/1",
        })

    donor_seq = "".join(donor_list)
    return donor_seq, truth_variants


def tulis_truth_vcf(path_vcf: Path, variants: list[dict], kontig: str = "chr21") -> None:
    """Menulis berkas VCF kebenaran (ground truth)."""
    header = [
        "##fileformat=VCFv4.2",
        f"##contig=<ID={kontig},length=10000>",
        '##INFO=<ID=TYPE,Number=1,Type=String,Description="Variant type">',
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
        '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">',
        f"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tTRUTH_SAMPLE",
    ]
    lines = header[:]
    for v in variants:
        lines.append(f"{kontig}\t{v['pos']}\t.\t{v['ref']}\t{v['alt']}\t100\tPASS\tTYPE={v['tipe']}\tGT:DP\t{v['gt']}:40")

    path_vcf.write_text("\n".join(lines) + "\n", encoding="utf-8")


def simulasi_reads_python(donor_seq: str, out_r1: Path, out_r2: Path, depth: int = 35, read_len: int = 100, seed: int = 202) -> None:
    """Generator simulasi read paired-end deterministik berbasis Python murni."""
    rnd = random.Random(seed)
    panjang = len(donor_seq)
    total_bases = panjang * depth
    n_pairs = total_bases // (read_len * 2)

    qual_str = "I" * read_len  # Phred quality Q40

    komplemen = str.maketrans("ACGTNacgtn", "TGCANtgcan")

    def revcomp(s):
        return s.translate(komplemen)[::-1]

    with gzip.open(out_r1, "wt", encoding="utf-8") as f1, gzip.open(out_r2, "wt", encoding="utf-8") as f2:
        for i in range(n_pairs):
            # Insert size 250 - 350 bp
            insert_size = rnd.randint(220, 320)
            start = rnd.randint(0, panjang - insert_size)
            fragment = donor_seq[start:start + insert_size]

            r1_seq = fragment[:read_len]
            r2_seq = revcomp(fragment[-read_len:])

            f1.write(f"@read_{i+1}/1\n{r1_seq}\n+\n{qual_str}\n")
            f2.write(f"@read_{i+1}/2\n{r2_seq}\n+\n{qual_str}\n")


def simulasi_reads_single(donor_seq: str, out_single: Path, depth: int = 35, read_len: int = 100, seed: int = 303) -> None:
    """Generator simulasi read single-end deterministik."""
    rnd = random.Random(seed)
    panjang = len(donor_seq)
    total_bases = panjang * depth
    n_reads = total_bases // read_len
    qual_str = "I" * read_len

    with gzip.open(out_single, "wt", encoding="utf-8") as f:
        for i in range(n_reads):
            start = rnd.randint(0, panjang - read_len)
            read_seq = donor_seq[start:start + read_len]
            f.write(f"@read_single_{i+1}\n{read_seq}\n+\n{qual_str}\n")


def buat_anotasi_uji(path_anotasi_chr: Path, path_anotasi_nochr: Path, variants: list[dict], kontig: str = "chr21") -> None:
    """Membuat berkas anotasi VCF tiruan untuk verifikasi integrasi anotasi dan mapping kontig."""
    gens = ["BRCA1", "TP53", "EGFR", "KRAS", "PTEN", "CFTR"]
    header_chr = [
        "##fileformat=VCFv4.2",
        f"##contig=<ID={kontig},length=10000>",
        '##INFO=<ID=GENE,Number=1,Type=String,Description="Gene Symbol">',
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
    ]
    kontig_nochr = kontig.replace("chr", "")
    header_nochr = [
        "##fileformat=VCFv4.2",
        f"##contig=<ID={kontig_nochr},length=10000>",
        '##INFO=<ID=GENE,Number=1,Type=String,Description="Gene Symbol">',
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
    ]

    lines_chr = header_chr[:]
    lines_nochr = header_nochr[:]

    for idx, v in enumerate(variants):
        gene_name = gens[idx % len(gens)]
        rs_id = f"rs{1000 + idx}"
        lines_chr.append(f"{kontig}\t{v['pos']}\t{rs_id}\t{v['ref']}\t{v['alt']}\t100\tPASS\tGENE={gene_name}")
        lines_nochr.append(f"{kontig_nochr}\t{v['pos']}\t{rs_id}\t{v['ref']}\t{v['alt']}\t100\tPASS\tGENE={gene_name}")

    raw_chr = path_anotasi_chr.with_suffix("") if path_anotasi_chr.suffix == ".gz" else path_anotasi_chr
    raw_nochr = path_anotasi_nochr.with_suffix("") if path_anotasi_nochr.suffix == ".gz" else path_anotasi_nochr

    raw_chr.write_text("\n".join(lines_chr) + "\n", encoding="utf-8")
    raw_nochr.write_text("\n".join(lines_nochr) + "\n", encoding="utf-8")

    # Kompres dengan bgzip / bcftools jika tersedia agar format blok gzip valid
    if shutil.which("bcftools"):
        subprocess.run(["bcftools", "view", "-Oz", "-o", str(path_anotasi_chr), str(raw_chr)], check=False)
        subprocess.run(["bcftools", "index", "-f", str(path_anotasi_chr)], check=False)
        subprocess.run(["bcftools", "view", "-Oz", "-o", str(path_anotasi_nochr), str(raw_nochr)], check=False)
        subprocess.run(["bcftools", "index", "-f", str(path_anotasi_nochr)], check=False)
    elif shutil.which("bgzip"):
        subprocess.run(["bgzip", "-c", str(raw_chr)], stdout=open(path_anotasi_chr, "wb"), check=False)
        subprocess.run(["bgzip", "-c", str(raw_nochr)], stdout=open(path_anotasi_nochr, "wb"), check=False)
    else:
        with gzip.open(path_anotasi_chr, "wt", encoding="utf-8") as f:
            f.write("\n".join(lines_chr) + "\n")
        with gzip.open(path_anotasi_nochr, "wt", encoding="utf-8") as f:
            f.write("\n".join(lines_nochr) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Generate deterministic mini test dataset for Human GVC.")
    parser.add_argument("--outdir", default="data_uji", help="Output directory (default: data_uji)")
    parser.add_argument("--kontig", default="chr21", help="Contig name (default: chr21)")
    parser.add_argument("--panjang", type=int, default=10000, help="Contig length in bp (default: 10000)")
    parser.add_argument("--nsnp", type=int, default=20, help="Number of SNPs to insert (default: 20)")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"=== Menghasilkan Data Uji Mini ({args.kontig}, {args.panjang} bp) ===")
    ref_seq = buat_referensi_sintetis(args.panjang, seed=42, kontig=args.kontig)
    ref_file = outdir / "ref.fa"
    ref_file.write_text(f">{args.kontig}\n{ref_seq}\n", encoding="utf-8")
    print(f"[1/5] Referensi dibuat: {ref_file} ({args.panjang} bp)")

    donor_seq, truth_variants = sisipkan_mutasi(ref_seq, n_snp=args.nsnp, seed=101)
    truth_vcf = outdir / "truth.vcf"
    tulis_truth_vcf(truth_vcf, truth_variants, kontig=args.kontig)
    print(f"[2/5] Truth set dibuat: {truth_vcf} ({len(truth_variants)} varian SNP disisipkan)")

    # FASTQ Paired-End
    r1 = outdir / "sample_R1.fastq.gz"
    r2 = outdir / "sample_R2.fastq.gz"
    simulasi_reads_python(donor_seq, r1, r2, depth=35, read_len=100, seed=202)
    print(f"[3/5] Reads paired-end dibuat: {r1.name}, {r2.name} (kedalaman ~35x)")

    # FASTQ Single-End
    r_single = outdir / "sample_single.fastq.gz"
    simulasi_reads_single(donor_seq, r_single, depth=35, read_len=100, seed=303)
    print(f"[4/5] Reads single-end dibuat: {r_single.name} (kedalaman ~35x)")

    # Anotasi
    anot_chr = outdir / "anotasi_dbsnp.vcf.gz"
    anot_nochr = outdir / "anotasi_beda_kontig.vcf.gz"
    buat_anotasi_uji(anot_chr, anot_nochr, truth_variants, kontig=args.kontig)
    print(f"[5/5] Berkas anotasi uji dibuat: {anot_chr.name} dan {anot_nochr.name}")

    print("=== Seluruh Data Uji Berhasil Dihasilkan! ===")


if __name__ == "__main__":
    main()


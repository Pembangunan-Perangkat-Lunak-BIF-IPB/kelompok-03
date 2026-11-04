#!/usr/bin/env python3
"""Skrip Validasi & Perbandingan VCF Hasil Pipeline terhadap Truth Set (WP-5 Fattha).

Menghitung:
- True Positive (TP)
- False Positive (FP)
- False Negative (FN)
- Recall (Sensitivitas) = TP / (TP + FN)
- Presisi = TP / (TP + FP)
- F1-Score

Memverifikasi pemenuhan kriteria Gerbang Penerimaan G3 (Recall >= 90%, Presisi >= 90%).
"""
import argparse
import gzip
from pathlib import Path
import sys


def parse_vcf_records(path_vcf: Path) -> dict[tuple[str, int, str, str], dict]:
    """Membaca VCF dan mengembalikan dictionary dengan kunci (chrom, pos, ref, alt)."""
    p = Path(path_vcf)
    if not p.exists():
        print(f"Error: Berkas VCF tidak ditemukan: {p}", file=sys.stderr)
        return {}

    op = gzip.open if p.suffix == ".gz" else open
    records = {}

    with op(p, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue

            chrom = parts[0]
            # Normalisasi nama kontig: chr21 -> 21 untuk perbandingan seragam
            norm_chrom = chrom[3:] if chrom.startswith("chr") else chrom
            pos = int(parts[1])
            ref = parts[3].upper()
            alt_list = parts[4].upper().split(",")

            qual = float(parts[5]) if len(parts) > 5 and parts[5] not in (".", "") else 0.0
            info = parts[7] if len(parts) > 7 else ""

            for alt in alt_list:
                key = (norm_chrom, pos, ref, alt)
                records[key] = {"qual": qual, "info": info, "asli_chrom": chrom}

    return records


def bandingkan_vcf(hasil_vcf: Path, truth_vcf: Path, ambang_target: float = 90.0) -> dict:
    """Membandingkan hasil variant calling dengan ground truth."""
    hasil = parse_vcf_records(hasil_vcf)
    truth = parse_vcf_records(truth_vcf)

    set_hasil = set(hasil.keys())
    set_truth = set(truth.keys())

    tp_set = set_hasil & set_truth
    fp_set = set_hasil - set_truth
    fn_set = set_truth - set_hasil

    tp = len(tp_set)
    fp = len(fp_set)
    fn = len(fn_set)

    recall = (tp / (tp + fn) * 100.0) if (tp + fn) > 0 else 0.0
    presisi = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else 0.0
    f1 = (2 * presisi * recall / (presisi + recall)) if (presisi + recall) > 0 else 0.0

    lulus_g3 = (recall >= ambang_target) and (presisi >= ambang_target)

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "total_truth": len(set_truth),
        "total_hasil": len(set_hasil),
        "recall": round(recall, 2),
        "presisi": round(presisi, 2),
        "f1": round(f1, 2),
        "lulus_g3": lulus_g3,
        "fp_items": list(fp_set),
        "fn_items": list(fn_set),
    }


def cetak_laporan(res: dict, path_hasil: str, path_truth: str, ambang: float = 90.0):
    print("=" * 68)
    print("       LAPORAN EVALUASI & VALIDASI HASIL PIPELINE (GERBANG G3)")
    print("=" * 68)
    print(f"Berkas Hasil : {path_hasil}")
    print(f"Berkas Truth : {path_truth}")
    print("-" * 68)
    print(f"Total Varian Kebenaran (Truth) : {res['total_truth']}")
    print(f"Total Varian Terpanggil (Call) : {res['total_hasil']}")
    print(f"True Positives (TP)           : {res['tp']}")
    print(f"False Positives (FP)          : {res['fp']}")
    print(f"False Negatives (FN)          : {res['fn']}")
    print("-" * 68)
    print(f"RECALL  (Sensitivitas)        : {res['recall']}%  (Target: >= {ambang}%)")
    print(f"PRESISI (Akurasi Call)        : {res['presisi']}%  (Target: >= {ambang}%)")
    print(f"F1-SCORE                      : {res['f1']}%")
    print("-" * 68)
    status_str = "MEMENUHI SYARAT (LULUS GERBANG G3)" if res['lulus_g3'] else "BELUM MEMENUHI AMBANG G3"
    print(f"STATUS PENERIMAAN GERBANG G3  : [{status_str}]")
    print("=" * 68)


def main():
    parser = argparse.ArgumentParser(description="Bandingkan VCF hasil calling pipeline terhadap truth VCF.")
    parser.add_argument("hasil_vcf", help="Path berkas VCF hasil pipeline")
    parser.add_argument("truth_vcf", help="Path berkas VCF ground truth")
    parser.add_argument("--ambang", type=float, default=90.0, help="Ambang minimal persentase G3 (default: 90.0)")
    args = parser.parse_args()

    res = bandingkan_vcf(Path(args.hasil_vcf), Path(args.truth_vcf), ambang_target=args.ambang)
    cetak_laporan(res, args.hasil_vcf, args.truth_vcf, ambang=args.ambang)

    if not res["lulus_g3"]:
        sys.exit(1)


if __name__ == "__main__":
    main()


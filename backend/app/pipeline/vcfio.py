"""Fungsi pembaca dan pembuat berkas VCF serta CSV (I/O VCF)."""
import gzip
from pathlib import Path


def _gen_dari_info(info: str):
    """Mengekstrak simbol gen dari INFO VCF (GENE= atau GENEINFO=)."""
    for kv in info.split(";"):
        if kv.startswith("GENE="):
            return kv[5:].split(",")[0][:100]
        if kv.startswith("GENEINFO="):  # format dbSNP: SIMBOL:id|SIMBOL2:id
            return kv[9:].split("|")[0].split(":")[0][:100]
    return None


def parse_vcf(path) -> list[dict]:
    """Baca VCF (.vcf / .vcf.gz). Mengambil alel ALT pertama dan GT/DP/GQ sampel pertama."""
    path = Path(path)
    op = gzip.open if path.suffix == ".gz" else open
    hasil = []
    with op(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            c = line.rstrip("\n").split("\t")
            if len(c) < 8 or c[4] in (".", ""):
                continue
            v = {
                "kromosom": c[0][:20],
                "posisi": int(c[1]),
                "ref": c[3],
                "alt": c[4].split(",")[0],
                "quality_score": float(c[5]) if c[5] not in (".", "") else 0.0,
                "gen": _gen_dari_info(c[7]),
                "gt": None,
                "dp": 0,
                "gq": None,
            }
            if len(c) >= 10:
                d = dict(zip(c[8].split(":"), c[9].split(":")))
                v["gt"] = d.get("GT", "./.")
                v["dp"] = int(d["DP"]) if d.get("DP", ".").isdigit() else 0
                v["gq"] = float(d["GQ"]) if d.get("GQ", ".").replace(".", "", 1).isdigit() else None
            hasil.append(v)
    return hasil


def bangun_vcf(varian: list[dict], nama_sampel: str) -> str:
    """Membangun teks format VCF v4.2 dari daftar varian."""
    h = [
        "##fileformat=VCFv4.2",
        "##source=HumanGVC",
        '##INFO=<ID=GENE,Number=1,Type=String,Description="Simbol gen (anotasi)">',
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotipe">',
        '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Kedalaman">',
        '##FORMAT=<ID=GQ,Number=1,Type=Float,Description="Kualitas genotipe">',
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t" + nama_sampel.replace("\t", " "),
    ]
    for v in varian:
        h.append("\t".join(map(str, [
            v["kromosom"],
            v["posisi"],
            ".",
            v["ref"],
            v["alt"],
            v["quality_score"],
            "PASS",
            f"GENE={v['gen']}" if v.get("gen") else ".",
            "GT:DP:GQ",
            f"{v.get('gt') or './.'}:{v.get('dp') or 0}:{v.get('gq') if v.get('gq') is not None else '.'}",
        ])))
    return "\n".join(h) + "\n"


def bangun_csv(varian: list[dict]) -> str:
    """Membangun teks format CSV dari daftar varian."""
    return "kromosom,posisi,ref,alt,qual,gen,genotipe,kedalaman\n" + "\n".join(
        f"{v['kromosom']},{v['posisi']},{v['ref']},{v['alt']},{v['quality_score']},{v.get('gen') or ''},{v.get('gt') or ''},{v.get('dp') or ''}"
        for v in varian
    ) + "\n"


"""Modul Parser Ringkasan QC dan Alignment (WP-4 Abid).

Mengimplementasikan fungsi murni:
- ringkasan_qc: Mengurai fastp.json -> metrik FR-14
- ringkasan_alignment: Mengurai keluaran samtools flagstat -> metrik FR-15
"""
import json
from pathlib import Path
import re
from typing import Union


def ringkasan_qc(sumber: Union[Path, str, dict]) -> dict:
    """Mengurai keluaran fastp.json menjadi ringkasan kontrol kualitas (FR-14).

    Kontrak 3.4: {reads_sebelum, reads_sesudah, q30_sebelum, q30_sesudah}
    """
    data = {}
    if isinstance(sumber, dict):
        data = sumber
    else:
        p = Path(sumber)
        if p.exists() and p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            try:
                data = json.loads(str(sumber))
            except Exception:
                data = {}

    summary = data.get("summary", {})
    before = summary.get("before_filtering", {})
    after = summary.get("after_filtering", {})

    reads_sebelum = int(before.get("total_reads", 0))
    reads_sesudah = int(after.get("total_reads", 0))

    q30_rate_before = float(before.get("q30_rate", 0.0))
    q30_rate_after = float(after.get("q30_rate", 0.0))

    # Konversi ke persentase (0.94 -> 94.0%) jika berupa rasio 0.0 s.d 1.0
    q30_sebelum = round(q30_rate_before * 100 if q30_rate_before <= 1.0 else q30_rate_before, 2)
    q30_sesudah = round(q30_rate_after * 100 if q30_rate_after <= 1.0 else q30_rate_after, 2)

    return {
        "reads_sebelum": reads_sebelum,
        "reads_sesudah": reads_sesudah,
        "q30_sebelum": q30_sebelum,
        "q30_sesudah": q30_sesudah,
    }


def ringkasan_alignment(sumber: Union[Path, str]) -> dict:
    """Mengurai teks samtools flagstat menjadi ringkasan alignment (FR-15).

    Kontrak 3.4: {total_reads, reads_teralign, persen_teralign}
    """
    teks = ""
    if isinstance(sumber, Path) or (isinstance(sumber, str) and Path(sumber).exists() and Path(sumber).is_file()):
        try:
            teks = Path(sumber).read_text(encoding="utf-8", errors="replace")
        except Exception:
            teks = ""
    else:
        teks = str(sumber)

    total_reads = 0
    reads_teralign = 0
    persen_teralign = 0.0

    for line in teks.splitlines():
        line = line.strip()
        # Baris total: "10000 + 0 in total (QC-passed reads + QC-failed reads)"
        m_tot = re.match(r"^(\d+)\s*\+\s*\d+\s+in total", line)
        if m_tot:
            total_reads = int(m_tot.group(1))
            continue

        # Baris mapped: "9850 + 0 mapped (98.50% : N/A)" atau "80 + 0 mapped (80.00%)"
        m_map = re.search(r"^(\d+)\s*\+\s*\d+\s+mapped\s*\(([\d.]+)%", line)
        if m_map:
            reads_teralign = int(m_map.group(1))
            try:
                persen_teralign = round(float(m_map.group(2)), 2)
            except ValueError:
                persen_teralign = 0.0

    return {
        "total_reads": total_reads,
        "reads_teralign": reads_teralign,
        "persen_teralign": persen_teralign,
    }


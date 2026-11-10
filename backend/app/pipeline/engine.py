"""Workflow Engine & Job Manager (WP-1 / Rakazaki).

Mengorkestrasi antrean thread pool, eksekusi 6 tahap (simulasi & nyata),
penyimpanan varian/genotipe, dan pembersihan folder kerja secara andal.
"""
from __future__ import annotations

import random
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.config import (
    MASA_RETENSI_HARI,
    PIPELINE_MODE,
    PIPELINE_THREADS,
    PIPELINE_WORKERS,
    SIM_DETIK_PER_TAHAP,
    STAGE_LABEL,
    STAGES,
    STORAGE_DIR,
)
from app.db import get_conn
from .konteks import Konteks, TahapGagal
from .referensi_mgr import pastikan_indeks_referensi
from .runner import Runner
from .stages import (
    alignment,
    anotasi,
    bam_processing,
    filtering,
    qc_trimming,
    variant_calling,
)
from .vcfio import bangun_csv, bangun_vcf, parse_vcf

_pool = ThreadPoolExecutor(max_workers=PIPELINE_WORKERS, thread_name_prefix="pipeline")


def kirim(id_analisis: int) -> None:
    """Kirim analisis ke antrean thread latar."""
    _pool.submit(_jalankan_aman, id_analisis)


def pulihkan_saat_start() -> int:
    """Analisis yang tertinggal 'menunggu/berjalan' saat server mati ditandai gagal."""
    with get_conn() as c:
        rows = c.execute(
            """UPDATE analisis SET status='gagal',
                      log_kesalahan='Server dimulai ulang saat analisis berjalan. Jalankan sebagai analisis baru.'
               WHERE status IN ('menunggu','berjalan')
               RETURNING id_analisis"""
        ).fetchall()
        for r in rows:
            c.execute(
                "INSERT INTO log_proses (id_analisis, tahap, jenis_pesan, pesan) "
                "VALUES (%s, NULL, 'error', 'Analisis dihentikan karena server dimulai ulang.')",
                (r["id_analisis"],),
            )
    return len(rows)


# ---------- util DB ----------
def _log(id_a: int, tahap: str | None, jenis: str, pesan: str) -> None:
    with get_conn() as c:
        c.execute(
            "INSERT INTO log_proses (id_analisis, tahap, jenis_pesan, pesan) VALUES (%s, %s, %s, %s)",
            (id_a, tahap, jenis, pesan[:2000]),
        )


def _set(id_a: int, **kw: Any) -> None:
    cols = ", ".join(f"{k}=%s" for k in kw)
    with get_conn() as c:
        c.execute(f"UPDATE analisis SET {cols} WHERE id_analisis=%s", [*kw.values(), id_a])


def _konteks_db(id_a: int):
    with get_conn() as c:
        a = c.execute("SELECT * FROM analisis WHERE id_analisis=%s", (id_a,)).fetchone()
        s = c.execute("SELECT * FROM sampel WHERE id_sampel=%s", (a["id_sampel"],)).fetchone()
        r = c.execute("SELECT * FROM referensi WHERE id_referensi=%s", (a["id_referensi"],)).fetchone()
        an = (
            c.execute("SELECT * FROM referensi WHERE id_referensi=%s", (a["id_referensi_anotasi"],)).fetchone()
            if a["id_referensi_anotasi"]
            else None
        )
    return a, s, r, an


def _riwayat(id_a: int, mulai: float, vcf: str | None, csv: str | None) -> None:
    with get_conn() as c:
        c.execute(
            """INSERT INTO riwayat_analisis (id_analisis, waktu_proses_detik, masa_retensi_hari, lokasi_hasil_vcf, lokasi_hasil_csv)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (id_analisis) DO NOTHING""",
            (id_a, int(time.time() - mulai), MASA_RETENSI_HARI, vcf, csv),
        )


def _simpan_varian(id_a: int, id_sampel: int, varian: list[dict]) -> None:
    with get_conn() as c:
        for v in varian:
            row = c.execute(
                """INSERT INTO varian (id_analisis, kromosom, posisi, ref, alt, quality_score, gen)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT ON CONSTRAINT uq_varian DO NOTHING
                   RETURNING id_varian""",
                (
                    id_a,
                    v["kromosom"],
                    v["posisi"],
                    v["ref"],
                    v["alt"],
                    max(0, v["quality_score"]),
                    v.get("gen"),
                ),
            ).fetchone()
            if row:
                c.execute(
                    """INSERT INTO genotipe (id_varian, id_sampel, genotipe, kedalaman, kualitas_genotipe)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        row["id_varian"],
                        id_sampel,
                        v.get("gt") or "./.",
                        max(0, v.get("dp") or 0),
                        v.get("gq"),
                    ),
                )


# ---------- Alur Utama ----------
def _jalankan_aman(id_a: int) -> None:
    mulai = time.time()
    try:
        _jalankan(id_a, mulai)
    except TahapGagal as e:
        _gagal(id_a, str(e), mulai)
    except Exception as e:
        _gagal(id_a, f"Kesalahan tak terduga: {e}", mulai)


def _gagal(id_a: int, pesan: str, mulai: float) -> None:
    with get_conn() as c:
        a = c.execute("SELECT tahap_saat_ini FROM analisis WHERE id_analisis=%s", (id_a,)).fetchone()
    tahap = a["tahap_saat_ini"] if a else None
    _log(id_a, tahap, "error", pesan)
    _set(id_a, status="gagal", log_kesalahan=pesan)
    _riwayat(id_a, mulai, None, None)


# ---------- Logika Simulasi (Mode Cepat & Uji Regresi 15 Tes) ----------
GENS = ["BRCA1", "TP53", "CFTR", "APOE", "EGFR", "KRAS", "BRCA2", "MTHFR", "SAMD11", "PTEN"]
CHRS = ["chr1", "chr2", "chr7", "chr12", "chr17", "chr19", "chrX"]


def _tahap_sim(tahap: str, ctx: Konteks, id_a: int) -> str | None:
    detik = SIM_DETIK_PER_TAHAP
    nama = ctx.nama_sampel.lower()
    time.sleep(detik / 2)
    _log(id_a, tahap, "berjalan", f"Memproses {STAGE_LABEL[tahap]} ({ctx.nama_sampel})...")
    time.sleep(detik / 2)

    if "gagal" in nama and tahap == "alignment":
        raise TahapGagal("kode keluar 1 (data tidak dapat diproses).")

    if tahap == "filtering":
        rnd = random.Random(id_a * 7919)
        p, vs = ctx.parameter, []
        for _ in range(90):
            ref = rnd.choice("ACGT")
            alt = rnd.choice([b for b in "ACGT" if b != ref])
            dp, q = rnd.randint(3, 80), round(rnd.uniform(10, 99), 1)
            if dp >= p.get("kedalaman_min", 10) and q >= p.get("qual_min", 30):
                vs.append(
                    {
                        "kromosom": rnd.choice(CHRS),
                        "posisi": rnd.randint(10_000, 200_000_000),
                        "ref": ref,
                        "alt": alt,
                        "quality_score": q,
                        "gen": rnd.choice(GENS) if rnd.random() > 0.35 else None,
                        "gt": rnd.choice(["0/1", "1/1"]),
                        "dp": dp,
                        "gq": round(rnd.uniform(30, 99), 1),
                    }
                )
        ctx.berkas["varian_sim"] = sorted(
            {(v["kromosom"], v["posisi"], v["ref"], v["alt"]): v for v in vs}.values(),
            key=lambda v: (v["kromosom"], v["posisi"]),
        )
    return None


def _jalankan(id_a: int, mulai: float) -> None:
    a, s, ref, anot = _konteks_db(id_a)
    if a["status"] != "menunggu":
        return

    kerja = STORAGE_DIR / "work" / str(id_a)
    kerja.mkdir(parents=True, exist_ok=True)
    _set(id_a, status="berjalan", progres_persen=0)
    _log(id_a, None, "info", f"Memulai pipeline ({PIPELINE_MODE})...")
    ket: str | None = None

    ref_path = STORAGE_DIR / ref["lokasi_berkas"]
    anot_path = (STORAGE_DIR / anot["lokasi_berkas"]) if anot else None
    r1_path = STORAGE_DIR / s["lokasi_fastq_r1"]
    r2_path = (STORAGE_DIR / s["lokasi_fastq_r2"]) if s.get("lokasi_fastq_r2") else None

    ctx = Konteks(
        id_analisis=id_a,
        id_sampel=s["id_sampel"],
        nama_sampel=s["nama_sampel"],
        kerja=kerja,
        referensi=ref_path,
        anotasi=anot_path,
        fastq_r1=r1_path,
        fastq_r2=r2_path,
        parameter=a["parameter"] or {},
        threads=PIPELINE_THREADS,
    )

    n_stages = len(STAGES)
    stage_modules = {
        "qc_trimming": qc_trimming,
        "alignment": alignment,
        "bam_processing": bam_processing,
        "variant_calling": variant_calling,
        "filtering": filtering,
        "anotasi": anotasi,
    }

    try:
        # Jika mode nyata, pastikan indeks referensi tersedia sekali di awal
        if PIPELINE_MODE == "nyata":
            sh_init = Runner(id_a, "alignment", tahap_index=0, total_tahap=n_stages)
            pastikan_indeks_referensi(ctx.referensi, sh_init)

        for i, tahap in enumerate(STAGES):
            label = STAGE_LABEL[tahap]
            _set(id_a, tahap_saat_ini=tahap, progres_persen=int(i / n_stages * 100))

            if tahap == "anotasi" and not anot:
                _log(id_a, tahap, "info", "Berkas anotasi tidak dipilih. Tahap anotasi dilewati.")
                ket = "Anotasi dilewati: berkas anotasi tidak tersedia."
                break

            _log(id_a, tahap, "info", f"Memulai tahap {label}...")
            sh = Runner(id_a, tahap, tahap_index=i, total_tahap=n_stages)

            try:
                if PIPELINE_MODE == "simulasi":
                    _tahap_sim(tahap, ctx, id_a)
                else:
                    mod = stage_modules.get(tahap)
                    if not mod:
                        raise TahapGagal(f"Modul untuk tahap '{tahap}' belum terdaftar.")
                    mod.jalankan(ctx, sh)
            except TahapGagal as e:
                raise TahapGagal(f"Tahap {label} gagal: {e}")

            _log(id_a, tahap, "berhasil", f"{label} selesai.")
            _set(id_a, progres_persen=min(99, int((i + 1) / n_stages * 100)))

        # Selesai seluruh tahap -> Simpan hasil
        if PIPELINE_MODE == "simulasi":
            varian = ctx.berkas.get("varian_sim", [])
        else:
            vcf_final = ctx.berkas.get("vcf_akhir") or ctx.berkas.get("vcf_filter")
            if not vcf_final or not Path(vcf_final).exists():
                raise TahapGagal("Berkas VCF hasil akhir tidak ditemukan.")
            varian = parse_vcf(vcf_final)

        if not anot or ket:
            for v in varian:
                v["gen"] = None

        _simpan_varian(id_a, s["id_sampel"], varian)

        hasil_dir = STORAGE_DIR / "results" / str(id_a)
        hasil_dir.mkdir(parents=True, exist_ok=True)
        (hasil_dir / "hasil.vcf").write_text(bangun_vcf(varian, s["nama_sampel"]), encoding="utf-8")
        (hasil_dir / "hasil.csv").write_text(bangun_csv(varian), encoding="utf-8")

        _riwayat(id_a, mulai, f"results/{id_a}/hasil.vcf", f"results/{id_a}/hasil.csv")
        _set(id_a, status="selesai", progres_persen=100, tahap_saat_ini="anotasi", keterangan=ket)
        _log(id_a, None, "berhasil", f"Analisis selesai: {len(varian)} varian tersimpan.")

    finally:
        # PEMBERSIHAN FOLDER KERJA (Risiko R7): selalu dibersihkan baik sukses maupun gagal
        shutil.rmtree(kerja, ignore_errors=True)

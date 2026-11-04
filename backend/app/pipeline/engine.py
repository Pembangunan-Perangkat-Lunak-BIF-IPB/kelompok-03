"""Job Manager + Workflow Engine Terorkestrasi (WP-1 Rakazaki).

Mengorkestrasi eksekusi pipeline 6 tahap, antrean thread pool,
penguncian pembuatan indeks referensi, pencatatan hasil, serta pembersihan kerja.
"""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import random
import shutil
import subprocess
import threading
import time
from typing import Optional

from ..config import (
    MASA_RETENSI_HARI,
    PIPELINE_MODE,
    PIPELINE_THREADS,
    PIPELINE_WORKERS,
    SIM_DETIK_PER_TAHAP,
    STAGE_LABEL,
    STAGES,
    STORAGE_DIR,
)
try:
    from ..db import get_conn
except ImportError:
    get_conn = None
from .konteks import Konteks, TahapGagal
from .ringkasan import ringkasan_alignment, ringkasan_qc
from .runner import Runner
from .vcfio import bangun_csv, bangun_vcf, parse_vcf

# Import modul tahap WP-2 & WP-3
from .stages import alignment, anotasi, bam_processing, filtering, qc_trimming, variant_calling

_pool = ThreadPoolExecutor(max_workers=PIPELINE_WORKERS, thread_name_prefix="pipeline")
_ref_locks = defaultdict(threading.Lock)


def kirim(id_analisis: int) -> None:
    """Mengirim tugas analisis ke antrean thread pool."""
    _pool.submit(_jalankan_aman, id_analisis)


def pulihkan_saat_start() -> int:
    """Menandai analisis yang tertinggal dalam status menunggu/berjalan saat server mati sebagai gagal."""
    with get_conn() as c:
        rows = c.execute(
            """UPDATE analisis SET status='gagal',
                      log_kesalahan='Server dimulai ulang saat analisis berjalan. Jalankan sebagai analisis baru.'
               WHERE status IN ('menunggu','berjalan') RETURNING id_analisis"""
        ).fetchall()
        for r in rows:
            c.execute(
                "INSERT INTO log_proses (id_analisis,tahap,jenis_pesan,pesan) VALUES (%s,NULL,'error','Analisis dihentikan karena server dimulai ulang.')",
                (r["id_analisis"],),
            )
    return len(rows)


# ---------- Database Helpers ----------
def _log(id_a: int, tahap: Optional[str], jenis: str, pesan: str) -> None:
    try:
        with get_conn() as c:
            c.execute(
                "INSERT INTO log_proses (id_analisis,tahap,jenis_pesan,pesan) VALUES (%s,%s,%s,%s)",
                (id_a, tahap, jenis, str(pesan)[:2000]),
            )
    except Exception as e:
        print(f"[Engine Log Error] {id_a}: {e}")


def _set(id_a: int, **kw) -> None:
    cols = ", ".join(f"{k}=%s" for k in kw)
    try:
        with get_conn() as c:
            c.execute(f"UPDATE analisis SET {cols} WHERE id_analisis=%s", [*kw.values(), id_a])
    except Exception as e:
        print(f"[Engine Set Error] {id_a}: {e}")


def _konteks_db(id_a: int):
    with get_conn() as c:
        a = c.execute("SELECT * FROM analisis WHERE id_analisis=%s", (id_a,)).fetchone()
        s = c.execute("SELECT * FROM sampel WHERE id_sampel=%s", (a["id_sampel"],)).fetchone() if a else None
        ref = c.execute("SELECT * FROM referensi WHERE id_referensi=%s", (a["id_referensi"],)).fetchone() if a else None
        anot = (
            c.execute("SELECT * FROM referensi WHERE id_referensi=%s", (a["id_referensi_anotasi"],)).fetchone()
            if a and a.get("id_referensi_anotasi")
            else None
        )
    return a, s, ref, anot


def _simpan_varian(id_a: int, id_sampel: int, varian: list[dict]) -> None:
    with get_conn() as c:
        for v in varian:
            row = c.execute(
                """INSERT INTO varian (id_analisis,kromosom,posisi,ref,alt,quality_score,gen)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT ON CONSTRAINT uq_varian DO NOTHING RETURNING id_varian""",
                (id_a, v["kromosom"], v["posisi"], v["ref"], v["alt"], max(0, v["quality_score"]), v["gen"]),
            ).fetchone()
            if row:
                c.execute(
                    """INSERT INTO genotipe (id_varian,id_sampel,genotipe,kedalaman,kualitas_genotipe)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (row["id_varian"], id_sampel, v.get("gt") or "./.", max(0, v.get("dp") or 0), v.get("gq")),
                )


def _riwayat(id_a: int, mulai: float, vcf: Optional[str], csv: Optional[str]) -> None:
    with get_conn() as c:
        c.execute(
            """INSERT INTO riwayat_analisis (id_analisis, waktu_proses_detik, masa_retensi_hari, lokasi_hasil_vcf, lokasi_hasil_csv)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (id_analisis) DO NOTHING""",
            (id_a, int(time.time() - mulai), MASA_RETENSI_HARI, vcf, csv),
        )


# ---------- Manajer Indeks Referensi (Kunci Per Referensi) ----------
def pastikan_indeks_referensi(ref_path: Path, sh: Runner, threads: int) -> None:
    """Membuat indeks BWA dan samtools faidx sekali saja secara aman dari balapan thread."""
    with _ref_locks[str(ref_path.resolve())]:
        bwt1 = Path(str(ref_path) + ".bwt")
        bwt2 = Path(str(ref_path) + ".bwt.2bit.64")
        if not bwt1.exists() and not bwt2.exists():
            sh.catat("Membuat indeks BWA untuk referensi...", jenis="info")
            sh.run(["bwa", "index", str(ref_path)], nama="bwa_index")

        fai = Path(str(ref_path) + ".fai")
        if not fai.exists():
            sh.catat("Membuat indeks FASTA (samtools faidx)...", jenis="info")
            sh.run(["samtools", "faidx", str(ref_path)], nama="samtools_faidx")


# ---------- Alur Utama Orkestrasi ----------
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
    # Bersihkan folder kerja saat gagal (R7)
    kerja = STORAGE_DIR / "work" / str(id_a)
    shutil.rmtree(kerja, ignore_errors=True)


def _jalankan(id_a: int, mulai: float) -> None:
    a, s, ref, anot = _konteks_db(id_a)
    if not a or a["status"] != "menunggu":
        return

    kerja = STORAGE_DIR / "work" / str(id_a)
    kerja.mkdir(parents=True, exist_ok=True)

    _set(id_a, status="berjalan", progres_persen=0)
    _log(id_a, None, "info", f"Memulai pipeline ({PIPELINE_MODE})...")

    ket = None
    ref_path = STORAGE_DIR / ref["lokasi_berkas"] if ref else Path()
    anot_path = (STORAGE_DIR / anot["lokasi_berkas"]) if anot else None

    fastq_r1 = (STORAGE_DIR / s["lokasi_fastq_r1"]) if s and s.get("lokasi_fastq_r1") else Path()
    fastq_r2 = (STORAGE_DIR / s["lokasi_fastq_r2"]) if s and s.get("lokasi_fastq_r2") else None

    ctx = Konteks(
        id_analisis=id_a,
        id_sampel=s["id_sampel"],
        nama_sampel=s["nama_sampel"],
        kerja=kerja,
        referensi=ref_path,
        anotasi=anot_path,
        fastq_r1=fastq_r1,
        fastq_r2=fastq_r2,
        parameter=a.get("parameter") or {},
        threads=PIPELINE_THREADS,
    )

    n = len(STAGES)
    try:
        for i, tahap in enumerate(STAGES):
            label = STAGE_LABEL[tahap]
            base_progres = int(i / n * 100)
            span_progres = int(100 / n)

            _set(id_a, tahap_saat_ini=tahap, progres_persen=base_progres)
            runner = Runner(id_a, tahap, base_progres=base_progres, span_progres=span_progres)

            # UC-03 alt 3: lewati anotasi jika tidak ada berkas anotasi
            if tahap == "anotasi" and not anot_path:
                _log(id_a, tahap, "info", "Berkas anotasi tidak dipilih. Tahap anotasi dilewati.")
                ket = "Anotasi dilewati: berkas anotasi tidak tersedia."
                break

            _log(id_a, tahap, "info", f"Memulai tahap {label}...")

            try:
                if PIPELINE_MODE == "simulasi":
                    hasil = _tahap_sim(tahap, ctx, id_a)
                else:
                    hasil = _tahap_nyata(tahap, ctx, runner)
            except TahapGagal as e:
                raise TahapGagal(f"Tahap {label} gagal: {e}")

            if hasil == "dilewati":
                ket = "Anotasi dilewati: format berkas anotasi tidak didukung (gunakan VCF)."
                _log(id_a, tahap, "info", ket)
            else:
                _log(id_a, tahap, "berhasil", f"{label} selesai.")

            # Ekstraksi ringkasan metrik per tahap (FR-14 & FR-15 / WP-4)
            if tahap == "qc_trimming" and ctx.berkas.get("fastp_json"):
                ctx.ringkasan["qc"] = ringkasan_qc(ctx.berkas["fastp_json"])
            elif tahap == "bam_processing" and ctx.berkas.get("flagstat"):
                ctx.ringkasan["alignment"] = ringkasan_alignment(ctx.berkas["flagstat"])

            _set(id_a, progres_persen=min(99, int((i + 1) / n * 100)))

        # Simpan hasil akhir
        if PIPELINE_MODE == "simulasi":
            varian = ctx.berkas.get("varian", [])
            # Ringkasan tiruan untuk mode simulasi agar FR-14 dan FR-15 tetap tampil di frontend
            ctx.ringkasan["qc"] = {
                "reads_sebelum": 100000,
                "reads_sesudah": 98500,
                "q30_sebelum": 94.20,
                "q30_sesudah": 98.10,
            }
            ctx.ringkasan["alignment"] = {
                "total_reads": 98500,
                "reads_teralign": 96250,
                "persen_teralign": 97.72,
            }
        else:
            final_vcf = ctx.berkas.get("vcf_akhir") or ctx.berkas.get("vcf_filter") or ctx.berkas.get("vcf_raw")
            if not final_vcf or not Path(final_vcf).exists():
                raise TahapGagal("Berkas VCF hasil akhir tidak ditemukan.")
            varian = parse_vcf(final_vcf)

        if not anot_path or ket:
            for v in varian:
                v["gen"] = None

        _simpan_varian(id_a, s["id_sampel"], varian)

        hasil_dir = STORAGE_DIR / "results" / str(id_a)
        hasil_dir.mkdir(parents=True, exist_ok=True)
        (hasil_dir / "hasil.vcf").write_text(bangun_vcf(varian, s["nama_sampel"]), encoding="utf-8")
        (hasil_dir / "hasil.csv").write_text(bangun_csv(varian), encoding="utf-8")

        _riwayat(id_a, mulai, f"results/{id_a}/hasil.vcf", f"results/{id_a}/hasil.csv")

        ringkasan_payload = json.dumps(ctx.ringkasan) if ctx.ringkasan else None
        try:
            _set(id_a, status="selesai", progres_persen=100, tahap_saat_ini="anotasi", keterangan=ket, ringkasan=ringkasan_payload)
        except Exception:
            # Fallback jika migrasi 04 belum dijalankan di database
            _set(id_a, status="selesai", progres_persen=100, tahap_saat_ini="anotasi", keterangan=ket)

        _log(id_a, None, "berhasil", f"Analisis selesai: {len(varian)} varian tersimpan.")

    finally:
        # Pembersihan folder kerja sementara baik saat sukses maupun saat gagal (R7 / Poin 6)
        shutil.rmtree(kerja, ignore_errors=True)


# ---------- Tahap Mode Nyata ----------
def _tahap_nyata(tahap: str, ctx: Konteks, sh: Runner) -> Optional[str]:
    """Menjalankan modul tahap nyata sesuai antarmuka Kontrak Bagian 3."""
    if tahap == "qc_trimming":
        qc_trimming.jalankan(ctx, sh)
    elif tahap == "alignment":
        pastikan_indeks_referensi(ctx.referensi, sh, ctx.threads)
        alignment.jalankan(ctx, sh)
    elif tahap == "bam_processing":
        bam_processing.jalankan(ctx, sh)
    elif tahap == "variant_calling":
        variant_calling.jalankan(ctx, sh)
    elif tahap == "filtering":
        filtering.jalankan(ctx, sh)
    elif tahap == "anotasi":
        return anotasi.jalankan(ctx, sh)
    return None


def _variant_calling_bawaan(ctx: Konteks, sh: Runner) -> None:
    """Implementasi fallback variant calling (bcftools mpileup | call)."""
    k = ctx.kerja
    raw_vcf = k / "raw.vcf.gz"
    bam = ctx.berkas.get("bam") or (k / "sorted.bam")

    cmd_mpileup = [
        "bcftools", "mpileup",
        "-f", str(ctx.referensi),
        "-a", "FORMAT/DP",
        "-Ou",
        str(bam),
    ]
    cmd_call = [
        "bcftools", "call",
        "-mv",
        "-Oz",
        "-o", str(raw_vcf),
    ]
    sh.run_pipe(cmd_mpileup, cmd_call, nama="bcftools_mpileup_call")
    ctx.berkas["vcf_raw"] = raw_vcf


def _filtering_bawaan(ctx: Konteks, sh: Runner) -> None:
    """Implementasi fallback filtering varian."""
    k = ctx.kerja
    p = ctx.parameter
    q_min = p.get("qual_min", 30)
    dp_min = p.get("kedalaman_min", 10)
    raw_vcf = ctx.berkas.get("vcf_raw") or (k / "raw.vcf.gz")
    filtered_vcf = k / "filtered.vcf.gz"

    cmd_filter = [
        "bcftools", "view",
        "-i", f"QUAL>={q_min} && FMT/DP>={dp_min}",
        "-Oz",
        "-o", str(filtered_vcf),
        str(raw_vcf),
    ]
    sh.run(cmd_filter, nama="bcftools_filter")
    ctx.berkas["vcf_filter"] = filtered_vcf
    ctx.berkas["vcf_akhir"] = filtered_vcf


def _anotasi_bawaan(ctx: Konteks, sh: Runner) -> Optional[str]:
    """Implementasi fallback anotasi VCF."""
    a = ctx.anotasi
    k = ctx.kerja
    if not a or not a.exists():
        raise TahapGagal(f"Berkas anotasi tidak ditemukan: {a}")
    if not a.name.lower().endswith((".vcf", ".vcf.gz")):
        return "dilewati"

    filtered_vcf = ctx.berkas.get("vcf_filter") or (k / "filtered.vcf.gz")
    annotated_vcf = k / "annotated.vcf.gz"

    sh.run(["bcftools", "index", "-f", str(filtered_vcf)], nama="bcftools_index_filtered")
    if not Path(str(a) + ".tbi").exists() and not Path(str(a) + ".csi").exists():
        sh.run(["bcftools", "index", "-f", str(a)], nama="bcftools_index_annot")

    cmd_annot = [
        "bcftools", "annotate",
        "-a", str(a),
        "-c", "ID,INFO",
        "-Oz",
        "-o", str(annotated_vcf),
        str(filtered_vcf),
    ]
    sh.run(cmd_annot, nama="bcftools_annotate")
    ctx.berkas["vcf_akhir"] = annotated_vcf
    return None


# ---------- Tahap Mode Simulasi ----------
GENS = ["BRCA1", "TP53", "CFTR", "APOE", "EGFR", "KRAS", "BRCA2", "MTHFR", "SAMD11", "PTEN"]
CHRS = ["chr1", "chr2", "chr7", "chr12", "chr17", "chr19", "chrX"]


def _tahap_sim(tahap: str, ctx: Konteks, id_a: int) -> Optional[str]:
    """Mode simulasi tanpa perangkat bioinformatika untuk tes cepat dan demo."""
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
                vs.append({
                    "kromosom": rnd.choice(CHRS),
                    "posisi": rnd.randint(10_000, 200_000_000),
                    "ref": ref,
                    "alt": alt,
                    "quality_score": q,
                    "gen": rnd.choice(GENS) if rnd.random() > 0.35 else None,
                    "gt": rnd.choice(["0/1", "1/1"]),
                    "dp": dp,
                    "gq": round(rnd.uniform(30, 99), 1),
                })
        ctx.berkas["varian"] = sorted(
            {(v["kromosom"], v["posisi"], v["ref"], v["alt"]): v for v in vs}.values(),
            key=lambda v: (v["kromosom"], v["posisi"]),
        )
    return None

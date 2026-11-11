"""Job Manager + Workflow Engine (Desain Modular). Menjalankan 6 tahap berurutan di thread latar.

Mode `simulasi`: tiap tahap hanya menunggu, hasil varian dibangkitkan acak (untuk demo/uji, tanpa tool).
Mode `nyata`   : fastp -> bwa mem -> samtools -> bcftools mpileup/call -> bcftools filter -> bcftools annotate.
Setiap tahap menulis log_proses; status/progres disimpan di tabel analisis (FR-07, FR-08).
Kegagalan satu tahap menghentikan analisis, menandai `gagal`, dan menyimpan log_kesalahan (UC-03 alt 2).
"""
import gzip, random, shutil, subprocess, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .config import (MASA_RETENSI_HARI, PIPELINE_MODE, PIPELINE_THREADS, PIPELINE_WORKERS, SIM_DETIK_PER_TAHAP,
                     STAGE_LABEL, STAGES, STORAGE_DIR)
from .db import get_conn

_pool = ThreadPoolExecutor(max_workers=PIPELINE_WORKERS, thread_name_prefix="pipeline")


class TahapGagal(Exception):
    pass


def kirim(id_analisis: int) -> None:
    _pool.submit(_jalankan_aman, id_analisis)


def pulihkan_saat_start() -> int:
    """Analisis yang tertinggal 'menunggu/berjalan' saat server mati ditandai gagal (progres tidak hilang diam-diam)."""
    with get_conn() as c:
        rows = c.execute(
            """UPDATE analisis SET status='gagal', log_kesalahan='Server dimulai ulang saat analisis berjalan. Jalankan sebagai analisis baru.'
               WHERE status IN ('menunggu','berjalan') RETURNING id_analisis""").fetchall()
        for r in rows:
            c.execute("INSERT INTO log_proses (id_analisis,tahap,jenis_pesan,pesan) VALUES (%s,NULL,'error','Analisis dihentikan karena server dimulai ulang.')", (r["id_analisis"],))
    return len(rows)


# ---------- util DB ----------
def _log(id_a, tahap, jenis, pesan):
    with get_conn() as c:
        c.execute("INSERT INTO log_proses (id_analisis,tahap,jenis_pesan,pesan) VALUES (%s,%s,%s,%s)", (id_a, tahap, jenis, pesan[:2000]))


def _set(id_a, **kw):
    cols = ", ".join(f"{k}=%s" for k in kw)
    with get_conn() as c:
        c.execute(f"UPDATE analisis SET {cols} WHERE id_analisis=%s", [*kw.values(), id_a])


def _konteks(id_a):
    with get_conn() as c:
        a = c.execute("SELECT * FROM analisis WHERE id_analisis=%s", (id_a,)).fetchone()
        s = c.execute("SELECT * FROM sampel WHERE id_sampel=%s", (a["id_sampel"],)).fetchone()
        r = c.execute("SELECT * FROM referensi WHERE id_referensi=%s", (a["id_referensi"],)).fetchone()
        an = c.execute("SELECT * FROM referensi WHERE id_referensi=%s", (a["id_referensi_anotasi"],)).fetchone() if a["id_referensi_anotasi"] else None
    return a, s, r, an


# ---------- alur utama ----------
def _jalankan_aman(id_a):
    mulai = time.time()
    try:
        _jalankan(id_a, mulai)
    except TahapGagal as e:
        _gagal(id_a, str(e), mulai)
    except Exception as e:  # noqa: BLE001 - apa pun yang tak terduga tetap harus tercatat
        _gagal(id_a, f"Kesalahan tak terduga: {e}", mulai)


def _gagal(id_a, pesan, mulai):
    with get_conn() as c:
        a = c.execute("SELECT tahap_saat_ini FROM analisis WHERE id_analisis=%s", (id_a,)).fetchone()
    _log(id_a, a["tahap_saat_ini"] if a else None, "error", pesan)
    _set(id_a, status="gagal", log_kesalahan=pesan)
    _riwayat(id_a, mulai, None, None)


def _riwayat(id_a, mulai, vcf, csv):
    with get_conn() as c:
        c.execute(
            """INSERT INTO riwayat_analisis (id_analisis, waktu_proses_detik, masa_retensi_hari, lokasi_hasil_vcf, lokasi_hasil_csv)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (id_analisis) DO NOTHING""",
            (id_a, int(time.time() - mulai), MASA_RETENSI_HARI, vcf, csv))


def _jalankan(id_a, mulai):
    a, s, ref, anot = _konteks(id_a)
    if a["status"] != "menunggu":
        return
    kerja = STORAGE_DIR / "work" / str(id_a)
    kerja.mkdir(parents=True, exist_ok=True)
    _set(id_a, status="berjalan", progres_persen=0)
    _log(id_a, None, "info", "Memulai pipeline...")
    ket = None
    ctx = {"a": a, "s": s, "ref": STORAGE_DIR / ref["lokasi_berkas"], "anot": (STORAGE_DIR / anot["lokasi_berkas"]) if anot else None,
           "p": a["parameter"], "kerja": kerja, "vcf": None}
    n = len(STAGES)
    for i, tahap in enumerate(STAGES):
        label = STAGE_LABEL[tahap]
        _set(id_a, tahap_saat_ini=tahap, progres_persen=int(i / n * 100))
        if tahap == "anotasi" and not anot:
            _log(id_a, tahap, "info", "Berkas anotasi tidak dipilih. Tahap anotasi dilewati.")  # UC-03 alt 3
            ket = "Anotasi dilewati: berkas anotasi tidak tersedia."
            break
        _log(id_a, tahap, "info", f"Memulai tahap {label}...")
        try:
            hasil = (_tahap_sim if PIPELINE_MODE == "simulasi" else _tahap_nyata)(tahap, ctx, id_a)
        except TahapGagal as e:
            raise TahapGagal(f"Tahap {label} gagal: {e}")
        if hasil == "dilewati":
            ket = "Anotasi dilewati: format berkas anotasi tidak didukung (gunakan VCF)."
            _log(id_a, tahap, "info", ket)
        else:
            _log(id_a, tahap, "berhasil", f"{label} selesai.")
        _set(id_a, progres_persen=min(99, int((i + 1) / n * 100)))
    # simpan hasil
    varian = ctx["varian"] if PIPELINE_MODE == "simulasi" else parse_vcf(ctx["vcf"])
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
    shutil.rmtree(kerja, ignore_errors=True)  # BAM antara tidak perlu disimpan


# ---------- simulasi ----------
GENS = ["BRCA1", "TP53", "CFTR", "APOE", "EGFR", "KRAS", "BRCA2", "MTHFR", "SAMD11", "PTEN"]
CHRS = ["chr1", "chr2", "chr7", "chr12", "chr17", "chr19", "chrX"]


def _tahap_sim(tahap, ctx, id_a):
    detik = SIM_DETIK_PER_TAHAP
    nama = ctx["s"]["nama_sampel"].lower()
    time.sleep(detik / 2)
    _log(id_a, tahap, "berjalan", f"Memproses {STAGE_LABEL[tahap]} ({ctx['s']['nama_sampel']})...")
    time.sleep(detik / 2)
    if "gagal" in nama and tahap == "alignment":     # skenario uji: nama sampel berisi 'gagal'
        raise TahapGagal("kode keluar 1 (data tidak dapat diproses).")
    if tahap == "filtering":
        rnd = random.Random(id_a * 7919)
        p, vs = ctx["p"], []
        for _ in range(90):
            ref = rnd.choice("ACGT"); alt = rnd.choice([b for b in "ACGT" if b != ref])
            dp, q = rnd.randint(3, 80), round(rnd.uniform(10, 99), 1)
            if dp >= p["kedalaman_min"] and q >= p["qual_min"]:   # parameter benar-benar memengaruhi hasil
                vs.append({"kromosom": rnd.choice(CHRS), "posisi": rnd.randint(10_000, 200_000_000), "ref": ref, "alt": alt,
                           "quality_score": q, "gen": rnd.choice(GENS) if rnd.random() > .35 else None,
                           "gt": rnd.choice(["0/1", "1/1"]), "dp": dp, "gq": round(rnd.uniform(30, 99), 1)})
        ctx["varian"] = sorted({(v["kromosom"], v["posisi"], v["ref"], v["alt"]): v for v in vs}.values(), key=lambda v: (v["kromosom"], v["posisi"]))


# ---------- nyata ----------
def _sh(id_a, tahap, cmd, **kw):
    """Jalankan perintah; stderr terakhir dicatat ke log. Gagal -> TahapGagal."""
    _log(id_a, tahap, "berjalan", "$ " + " ".join(map(str, cmd))[:300])
    try:
        r = subprocess.run([str(x) for x in cmd], capture_output=True, text=True, **kw)
    except FileNotFoundError:
        raise TahapGagal(f"perangkat '{cmd[0]}' tidak terpasang di server.")
    if r.returncode != 0:
        raise TahapGagal(f"{cmd[0]} keluar dengan kode {r.returncode}: {(r.stderr or '').strip()[-400:]}")
    return r


def _tahap_nyata(tahap, ctx, id_a):
    T, p, k, s = str(PIPELINE_THREADS), ctx["p"], ctx["kerja"], ctx["s"]
    ref = ctx["ref"]
    if not ref.exists():
        raise TahapGagal(f"berkas referensi tidak ditemukan: {ref.name}")
    r1 = STORAGE_DIR / s["lokasi_fastq_r1"]
    r2 = STORAGE_DIR / s["lokasi_fastq_r2"] if s["lokasi_fastq_r2"] else None
    if tahap == "qc_trimming":   # fastp = QC + trimming sekaligus; laporan JSON disimpan
        cmd = ["fastp", "-i", r1, "-o", k / "t1.fastq.gz", "-q", p["kualitas_pemangkasan_min"], "-w", T, "-j", k / "fastp.json", "-h", k / "fastp.html"]
        if r2:
            cmd += ["-I", r2, "-O", k / "t2.fastq.gz"]
        _sh(id_a, tahap, cmd)
    elif tahap == "alignment":
        if not Path(str(ref) + ".bwt").exists() and not Path(str(ref) + ".bwt.2bit.64").exists():
            _sh(id_a, tahap, ["bwa", "index", ref])
        rg = f"@RG\\tID:{s['id_sampel']}\\tSM:{s['nama_sampel']}\\tPL:ILLUMINA"
        reads = [k / "t1.fastq.gz"] + ([k / "t2.fastq.gz"] if r2 else [])
        sam = subprocess.run(["bwa", "mem", "-t", T, "-R", rg, str(ref), *map(str, reads)], stdout=open(k / "aln.sam", "w"), stderr=subprocess.PIPE, text=True)
        if sam.returncode != 0:
            raise TahapGagal(f"bwa mem gagal: {sam.stderr[-400:]}")
        _log(id_a, tahap, "berjalan", "Alignment BWA-MEM selesai, mengubah ke BAM...")
        _sh(id_a, tahap, ["samtools", "view", "-@", T, "-b", "-o", k / "aln.bam", k / "aln.sam"])
    elif tahap == "bam_processing":
        _sh(id_a, tahap, ["samtools", "sort", "-@", T, "-o", k / "sorted.bam", k / "aln.bam"])
        _sh(id_a, tahap, ["samtools", "index", k / "sorted.bam"])
        if not Path(str(ref) + ".fai").exists():
            _sh(id_a, tahap, ["samtools", "faidx", ref])
    elif tahap == "variant_calling":
        mp = subprocess.Popen(["bcftools", "mpileup", "-f", str(ref), "-a", "FORMAT/DP", "-Ou", str(k / "sorted.bam")], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        call = subprocess.run(["bcftools", "call", "-mv", "-Oz", "-o", str(k / "raw.vcf.gz")], stdin=mp.stdout, capture_output=True, text=True)
        mp.stdout.close(); mp.wait()
        if mp.returncode != 0 or call.returncode != 0:
            raise TahapGagal(f"bcftools mpileup/call gagal: {(call.stderr or '')[-300:]}")
    elif tahap == "filtering":
        _sh(id_a, tahap, ["bcftools", "view", "-i", f"QUAL>={p['qual_min']} && FMT/DP>={p['kedalaman_min']}", "-Oz", "-o", k / "filtered.vcf.gz", k / "raw.vcf.gz"])
        ctx["vcf"] = k / "filtered.vcf.gz"
    elif tahap == "anotasi":
        a = ctx["anot"]
        if not a.exists():
            raise TahapGagal(f"berkas anotasi tidak ditemukan: {a.name}")
        if not a.name.lower().endswith((".vcf", ".vcf.gz")):
            return "dilewati"   # GTF/GFF belum didukung pada mode nyata
        _sh(id_a, tahap, ["bcftools", "index", "-f", k / "filtered.vcf.gz"])
        if not Path(str(a) + ".tbi").exists() and not Path(str(a) + ".csi").exists():
            _sh(id_a, tahap, ["bcftools", "index", "-f", a])
        _sh(id_a, tahap, ["bcftools", "annotate", "-a", a, "-c", "ID,INFO", "-Oz", "-o", k / "annotated.vcf.gz", k / "filtered.vcf.gz"])
        ctx["vcf"] = k / "annotated.vcf.gz"


# ---------- VCF <-> data ----------
def _gen_dari_info(info: str):
    for kv in info.split(";"):
        if kv.startswith("GENE="):
            return kv[5:].split(",")[0][:100]
        if kv.startswith("GENEINFO="):                      # format dbSNP: SIMBOL:id|SIMBOL2:id
            return kv[9:].split("|")[0].split(":")[0][:100]
    return None


def parse_vcf(path) -> list[dict]:
    """Baca VCF (.vcf / .vcf.gz). Alel ALT pertama saja; GT/DP/GQ dari sampel pertama."""
    path = Path(path)
    op = gzip.open if path.suffix == ".gz" else open
    hasil = []
    with op(path, "rt") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            c = line.rstrip("\n").split("\t")
            if len(c) < 8 or c[4] in (".", ""):
                continue
            v = {"kromosom": c[0][:20], "posisi": int(c[1]), "ref": c[3], "alt": c[4].split(",")[0],
                 "quality_score": float(c[5]) if c[5] not in (".", "") else 0.0, "gen": _gen_dari_info(c[7]),
                 "gt": None, "dp": 0, "gq": None}
            if len(c) >= 10:
                d = dict(zip(c[8].split(":"), c[9].split(":")))
                v["gt"] = d.get("GT", "./."); v["dp"] = int(d["DP"]) if d.get("DP", ".").isdigit() else 0
                v["gq"] = float(d["GQ"]) if d.get("GQ", ".").replace(".", "", 1).isdigit() else None
            hasil.append(v)
    return hasil


def _simpan_varian(id_a, id_sampel, varian):
    with get_conn() as c:
        for v in varian:
            row = c.execute(
                """INSERT INTO varian (id_analisis,kromosom,posisi,ref,alt,quality_score,gen) VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT ON CONSTRAINT uq_varian DO NOTHING RETURNING id_varian""",
                (id_a, v["kromosom"], v["posisi"], v["ref"], v["alt"], max(0, v["quality_score"]), v["gen"])).fetchone()
            if row:
                c.execute("INSERT INTO genotipe (id_varian,id_sampel,genotipe,kedalaman,kualitas_genotipe) VALUES (%s,%s,%s,%s,%s)",
                          (row["id_varian"], id_sampel, v.get("gt") or "./.", max(0, v.get("dp") or 0), v.get("gq")))


def bangun_vcf(varian, nama_sampel) -> str:
    h = ["##fileformat=VCFv4.2", "##source=HumanGVC", '##INFO=<ID=GENE,Number=1,Type=String,Description="Simbol gen (anotasi)">',
         '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotipe">', '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Kedalaman">',
         '##FORMAT=<ID=GQ,Number=1,Type=Float,Description="Kualitas genotipe">',
         "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t" + nama_sampel.replace("\t", " ")]
    for v in varian:
        h.append("\t".join(map(str, [v["kromosom"], v["posisi"], ".", v["ref"], v["alt"], v["quality_score"], "PASS",
                                     f"GENE={v['gen']}" if v.get("gen") else ".", "GT:DP:GQ", f"{v.get('gt') or './.'}:{v.get('dp') or 0}:{v.get('gq') if v.get('gq') is not None else '.'}"])))
    return "\n".join(h) + "\n"


def bangun_csv(varian) -> str:
    return "kromosom,posisi,ref,alt,qual,gen,genotipe,kedalaman\n" + "\n".join(
        f"{v['kromosom']},{v['posisi']},{v['ref']},{v['alt']},{v['quality_score']},{v.get('gen') or ''},{v.get('gt') or ''},{v.get('dp') or ''}" for v in varian) + "\n"

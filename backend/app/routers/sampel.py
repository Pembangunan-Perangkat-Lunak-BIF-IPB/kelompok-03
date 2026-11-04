import re, uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from ..config import MAX_UPLOAD_MB, PARAM_DEFAULT, STORAGE_DIR
from ..db import get_conn
from ..deps import catat, pengguna_saat_ini
from ..services import FASTQ_EXT, analisis_lengkap, hapus_folder, pasangan_fastq, periksa_isi_fastq, rel, simpan_stream

router = APIRouter(prefix="/api/sampel", tags=["sampel"])


@router.post("", status_code=201)
def unggah_sampel(nama_sampel: str = Form(""), lokasi: str = Form(""), strain: str = Form(""), karakteristik: str = Form(""),
                  fastq_r1: UploadFile = File(...), fastq_r2: Optional[UploadFile] = File(None), u=Depends(pengguna_saat_ini)):
    """UC-01: terima FASTQ + metadata, validasi (FR-02), simpan sampel, buat analisis berstatus draf."""
    meta = {"nama_sampel": nama_sampel, "lokasi": lokasi, "strain": strain, "karakteristik": karakteristik}
    kosong = [k for k, v in meta.items() if not v.strip()]
    if kosong:
        raise HTTPException(422, "Metadata belum lengkap: " + ", ".join(kosong) + ".")   # UC-01 alt 3
    files = [f for f in (fastq_r1, fastq_r2) if f is not None and f.filename]
    if not files:
        raise HTTPException(422, "Berkas FASTQ belum dipilih.")
    bad = [f.filename for f in files if not FASTQ_EXT.search(f.filename)]
    if bad:
        raise HTTPException(422, f"Format berkas tidak didukung: {', '.join(bad)}. Gunakan .fastq atau .fastq.gz.")   # BR-02
    if len(files) == 2:
        urut = pasangan_fastq([f.filename for f in files])
        if urut is None:
            raise HTTPException(422, "Pasangan paired-end tidak cocok. Nama berkas harus sama kecuali penanda R1/R2.")   # BR-03
        files = [files[i] for i in urut]
    folder = STORAGE_DIR / "uploads" / uuid.uuid4().hex[:12]
    folder.mkdir(parents=True)
    try:
        paths = []
        for n, f in enumerate(files, 1):
            p = folder / f"R{n}_{re.sub(r'[^\w.\-]', '_', f.filename)}"
            if simpan_stream(f, p, MAX_UPLOAD_MB) == 0:
                raise HTTPException(422, f"Berkas {f.filename} kosong.")
            periksa_isi_fastq(p, f.filename)
            paths.append(p)
        with get_conn() as c:
            s = c.execute(
                """INSERT INTO sampel (id_pengguna,nama_sampel,lokasi,strain,karakteristik,tipe_baca,lokasi_fastq_r1,lokasi_fastq_r2)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id_sampel""",
                (u["id_pengguna"], *(v.strip() for v in meta.values()), "paired-end" if len(paths) == 2 else "single-end",
                 rel(paths[0]), rel(paths[1]) if len(paths) == 2 else None)).fetchone()
            gen = c.execute("SELECT id_referensi FROM referensi WHERE status='bawaan' AND jenis='genom' ORDER BY id_referensi LIMIT 1").fetchone()
            a = c.execute("INSERT INTO analisis (id_pengguna,id_sampel,id_referensi,parameter) VALUES (%s,%s,%s,%s::jsonb) RETURNING id_analisis",
                          (u["id_pengguna"], s["id_sampel"], gen["id_referensi"] if gen else None, __import__("json").dumps(PARAM_DEFAULT))).fetchone()
            catat(c, u["id_pengguna"], "sampel", s["id_sampel"], "unggah")
            return analisis_lengkap(c, a["id_analisis"])
    except Exception:
        hapus_folder(folder)
        raise

"""Uji alur end-to-end UC-01 s.d. UC-07 dan aturan bisnis BR-01..BR-08 terhadap PostgreSQL sungguhan."""
import gzip, io, time
from app import pipeline
from app.db import get_conn
from .conftest import masuk

FQ = b"@r1\nACGTACGT\n+\nIIIIIIII\n@r2\nTTGGCCAA\n+\nIIIIIIII\n"
META = {"nama_sampel": "Sampel-001", "lokasi": "Bogor, Jawa Barat", "strain": "GRCh38-A", "karakteristik": "Jaringan tumor"}


def gz(b=FQ): return gzip.compress(b)


def unggah(client, h, files, meta=None):
    return client.post("/api/sampel", headers=h, data=meta or META, files=files)


def paired(): return [("fastq_r1", ("s_R1.fastq.gz", gz(), "application/gzip")), ("fastq_r2", ("s_R2.fastq.gz", gz(), "application/gzip"))]


def tunggu(client, h, id_a, sampai=("selesai", "gagal"), maks=30):
    for _ in range(int(maks / 0.2)):
        a = client.get(f"/api/analisis/{id_a}", headers=h).json()
        if a["status"] in sampai:
            return a
        time.sleep(0.2)
    raise AssertionError(f"analisis {id_a} tidak selesai: {a['status']}")


def test_auth(client):
    assert client.post("/api/auth/login", json={"email": "peneliti@ipb.ac.id", "password": "salah"}).status_code == 401
    assert client.get("/api/analisis").status_code == 401
    assert client.get("/api/analisis", headers={"Authorization": "Bearer x.y"}).status_code == 401


def test_uc01_validasi_unggah(client, peneliti):
    assert unggah(client, peneliti, [("fastq_r1", ("a.txt", FQ, "text/plain"))]).status_code == 422          # BR-02
    r = unggah(client, peneliti, [("fastq_r1", ("a_R1.fastq.gz", gz(), "x")), ("fastq_r2", ("b_R2.fastq.gz", gz(), "x"))])
    assert r.status_code == 422 and "Pasangan" in r.json()["detail"]                                         # BR-03
    assert unggah(client, peneliti, [("fastq_r1", ("a.fastq.gz", b"bukan gzip", "x"))]).status_code == 422
    assert unggah(client, peneliti, [("fastq_r1", ("a.fastq", b"@x\nAC\n+\nI\n", "x"))]).status_code == 422  # panjang urutan != kualitas
    r = unggah(client, peneliti, paired(), {**META, "strain": " "})
    assert r.status_code == 422 and "strain" in r.json()["detail"]                                           # metadata tak lengkap


def test_alur_penuh_dan_aturan_bisnis(client, peneliti, admin):
    # UC-01
    r = unggah(client, peneliti, paired()); assert r.status_code == 201, r.text
    a = r.json(); id_a = a["id_analisis"]
    assert a["status"] == "draf" and a["sampel"]["tipe_baca"] == "paired-end" and a["id_referensi"] == a["referensi"]["id_referensi"]
    assert a["parameter"] == {"kualitas_pemangkasan_min": 20, "kedalaman_min": 10, "qual_min": 30}
    # UC-02 + BR-04
    assert client.patch(f"/api/analisis/{id_a}", headers=peneliti, json={"parameter": {"kedalaman_min": 99999}}).status_code == 422
    assert client.patch(f"/api/analisis/{id_a}", headers=peneliti, json={"parameter": {"foo": 1}}).status_code == 422
    anot = client.get("/api/referensi?jenis=anotasi", headers=peneliti).json()[0]["id_referensi"]
    genom = client.get("/api/referensi?jenis=genom", headers=peneliti).json()[0]["id_referensi"]
    assert client.patch(f"/api/analisis/{id_a}", headers=peneliti, json={"id_referensi": anot}).status_code == 422   # jenis salah
    # BR-01: tanpa referensi tidak boleh jalan
    assert client.patch(f"/api/analisis/{id_a}", headers=peneliti, json={"id_referensi": None}).status_code == 200
    r = client.post(f"/api/analisis/{id_a}/jalankan", headers=peneliti)
    assert r.status_code == 422 and "genom referensi" in r.json()["detail"]
    r = client.patch(f"/api/analisis/{id_a}", headers=peneliti, json={"id_referensi": genom, "id_referensi_anotasi": anot, "parameter": {"kedalaman_min": 15}})
    assert r.json()["parameter"]["kedalaman_min"] == 15 and r.json()["parameter"]["qual_min"] == 30
    # BR-07: pengguna lain tidak bisa melihat
    lain = masuk(client, "rakahendrawan@ipb.ac.id", "Admin#123")
    assert client.get(f"/api/analisis/{id_a}", headers=lain).status_code == 404
    assert client.post(f"/api/analisis/{id_a}/jalankan", headers=lain).status_code == 404
    # hasil sebelum selesai ditolak (UC-05 alt 1)
    assert client.get(f"/api/analisis/{id_a}/ringkasan", headers=peneliti).status_code == 409
    # UC-03/04
    assert client.post(f"/api/analisis/{id_a}/jalankan", headers=peneliti).json()["status"] == "menunggu"
    assert client.post(f"/api/analisis/{id_a}/jalankan", headers=peneliti).status_code == 409
    done = tunggu(client, peneliti, id_a)
    assert done["status"] == "selesai" and done["progres_persen"] == 100 and done["keterangan"] is None
    log = client.get(f"/api/analisis/{id_a}/log", headers=peneliti).json()
    assert {x["tahap"] for x in log if x["tahap"]} == set(pipeline.STAGES)
    assert {"info", "berjalan", "berhasil"} <= {x["jenis_pesan"] for x in log}
    # BR-05: sudah dijalankan -> tidak bisa diubah
    assert client.patch(f"/api/analisis/{id_a}", headers=peneliti, json={"parameter": {"qual_min": 1}}).status_code == 409
    # UC-05
    rs = client.get(f"/api/analisis/{id_a}/ringkasan", headers=peneliti).json()
    assert rs["total_varian"] > 0 and rs["qual_rata2"] >= 30           # filter qual_min=30 benar-benar diterapkan
    v = client.get(f"/api/analisis/{id_a}/varian?page=1&size=5", headers=peneliti).json()
    assert v["total"] == rs["total_varian"] and len(v["items"]) == 5
    assert all(x["quality_score"] >= 30 for x in v["items"])
    vcf = client.get(f"/api/analisis/{id_a}/unduh?format=vcf", headers=peneliti); assert vcf.status_code == 200 and vcf.text.startswith("##fileformat=VCFv4.2")
    csv = client.get(f"/api/analisis/{id_a}/unduh?format=csv", headers=peneliti); assert csv.text.splitlines()[0].startswith("kromosom,posisi")
    assert len(csv.text.strip().splitlines()) - 1 == rs["total_varian"]
    # basis data bersama: sebelum publikasi tidak terlihat
    assert client.get("/api/varian?q=SAMP", headers=lain).json()["total"] == 0
    # FR-10 kunci, FR-11 publikasi
    assert client.post(f"/api/analisis/{id_a}/kunci", headers=peneliti).json()["terkunci"] is True
    assert client.post(f"/api/analisis/{id_a}/publikasi", headers=peneliti).json()["dipublikasikan"] is True
    with get_conn() as c:   # trigger DB BR-05 menolak ubah analisis terkunci walau lewat SQL langsung
        try:
            c.execute("UPDATE analisis SET status='draf' WHERE id_analisis=%s", (id_a,)); assert False
        except Exception as e:
            assert "terkunci" in str(e)
    # UC-06
    s = client.get("/api/varian?q=SAMP-&page=1&size=10", headers=lain).json()
    assert s["total"] == rs["total_varian"] and s["items"][0]["pengunggah"] == "Yaphets Mubakar"
    first = s["items"][0]
    assert client.get(f"/api/varian?q={first['kromosom']}:{first['posisi']}", headers=lain).json()["total"] >= 1
    assert client.get("/api/varian?q=chr1:abc", headers=lain).status_code == 422
    assert client.get("/api/varian?qual_min=abc", headers=lain).status_code == 422
    assert client.get("/api/varian?q=TIDAKADA999", headers=lain).json()["total"] == 0
    assert all(x["quality_score"] >= 90 for x in client.get("/api/varian?qual_min=90&size=100", headers=lain).json()["items"])
    d = client.get(f"/api/varian/{first['id_varian']}", headers=lain).json()
    assert d["genotipe"]["kedalaman"] >= 15 and d["sampel"]["nama_sampel"] == "Sampel-001"
    # jejak akses (FR-13)
    with get_conn() as c:
        aksi = {r["jenis_aksi"] for r in c.execute("SELECT jenis_aksi FROM log_akses").fetchall()}
    assert {"login", "unggah", "jalankan", "unduh", "cari", "lihat", "ubah"} <= aksi
    # BR-05: ulang sebagai analisis baru
    n = client.post(f"/api/analisis/{id_a}/salin", headers=peneliti).json()
    assert n["status"] == "draf" and n["id_analisis"] != id_a and n["parameter"]["kedalaman_min"] == 15
    # BR-08: lewat masa retensi -> tidak tampil
    ids = [x["id_analisis"] for x in client.get("/api/analisis", headers=peneliti).json()]
    assert id_a in ids
    with get_conn() as c:
        c.execute("UPDATE riwayat_analisis SET tanggal = now() - interval '91 days' WHERE id_analisis=%s", (id_a,))
    assert id_a not in [x["id_analisis"] for x in client.get("/api/analisis", headers=peneliti).json()]
    assert client.get(f"/api/analisis/{id_a}", headers=peneliti).status_code == 404


def test_analisis_gagal_dan_br06(client, peneliti):
    a = unggah(client, peneliti, [("fastq_r1", ("x.fastq", FQ, "x"))], {**META, "nama_sampel": "uji-gagal"}).json()
    assert a["sampel"]["tipe_baca"] == "single-end"
    client.post(f"/api/analisis/{a['id_analisis']}/jalankan", headers=peneliti)
    g = tunggu(client, peneliti, a["id_analisis"])
    assert g["status"] == "gagal" and "Alignment" in g["log_kesalahan"] and g["tahap_saat_ini"] == "alignment"
    assert client.post(f"/api/analisis/{g['id_analisis']}/publikasi", headers=peneliti).status_code == 409   # BR-06
    assert client.post(f"/api/analisis/{g['id_analisis']}/kunci", headers=peneliti).status_code == 409
    assert client.get(f"/api/analisis/{g['id_analisis']}/varian", headers=peneliti).status_code == 409
    log = client.get(f"/api/analisis/{g['id_analisis']}/log", headers=peneliti).json()
    assert log[-1]["jenis_pesan"] == "error"


def test_tanpa_anotasi_dilewati(client, peneliti):
    a = unggah(client, peneliti, [("fastq_r1", ("y.fastq.gz", gz(), "x"))], {**META, "nama_sampel": "tanpa-anotasi"}).json()
    client.post(f"/api/analisis/{a['id_analisis']}/jalankan", headers=peneliti)
    d = tunggu(client, peneliti, a["id_analisis"])
    assert d["status"] == "selesai" and "Anotasi dilewati" in d["keterangan"]                                # UC-03 alt 3
    assert all(x["gen"] is None for x in client.get(f"/api/analisis/{d['id_analisis']}/varian?size=100", headers=peneliti).json()["items"])


def test_uc02_unggah_referensi(client, peneliti):
    assert client.post("/api/referensi", headers=peneliti, data={"jenis": "genom"}, files={"berkas": ("x.txt", b"abc")}).status_code == 422
    r = client.post("/api/referensi", headers=peneliti, data={"jenis": "genom", "nama_referensi": "Kecil"}, files={"berkas": ("kecil.fa", b">c1\nACGT\n")})
    assert r.status_code == 201 and r.json()["status"] == "unggahan" and r.json()["id_pengunggah"] is not None


def test_uc07_admin(client, peneliti, admin):
    assert client.get("/api/pengguna", headers=peneliti).status_code == 403
    assert client.post("/api/pengguna", headers=peneliti, json={"nama": "x", "email": "a@b.co", "password": "12345678"}).status_code == 403
    p = {"nama": "Uji Baru", "email": "uji.baru@ipb.ac.id", "password": "Rahasia#123", "peran": "peneliti"}
    assert client.post("/api/pengguna", headers=admin, json={**p, "password": "pendek"}).status_code == 422
    assert client.post("/api/pengguna", headers=admin, json={**p, "email": "bukan-email"}).status_code == 422
    r = client.post("/api/pengguna", headers=admin, json=p); assert r.status_code == 201 and "password_hash" not in r.json()
    assert client.post("/api/pengguna", headers=admin, json=p).status_code == 409           # email unik
    masuk(client, "uji.baru@ipb.ac.id", "Rahasia#123")
    uid = r.json()["id_pengguna"]
    assert client.patch(f"/api/pengguna/{uid}", headers=admin, json={**p, "password": None, "aktif": False}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "uji.baru@ipb.ac.id", "password": "Rahasia#123"}).status_code == 403
    me = client.get("/api/auth/me", headers=admin).json()
    assert client.patch(f"/api/pengguna/{me['id_pengguna']}", headers=admin, json={"nama": me["nama"], "email": me["email"], "peran": "peneliti", "aktif": True}).status_code == 409
    # referensi: dipakai analisis tidak boleh dihapus; yang tak terpakai boleh
    pakai = client.get("/api/referensi?jenis=genom", headers=admin).json()[0]["id_referensi"]
    assert client.delete(f"/api/referensi/{pakai}", headers=admin).status_code == 409
    kecil = [x for x in client.get("/api/referensi", headers=admin).json() if x["nama_referensi"] == "Kecil"][0]
    assert client.delete(f"/api/referensi/{kecil['id_referensi']}", headers=peneliti).status_code == 403
    assert client.delete(f"/api/referensi/{kecil['id_referensi']}", headers=admin).status_code == 204


def test_parse_vcf(tmp_path):
    isi = ("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\n"
           "chr1\t100\trs1\tA\tG,T\t99.5\tPASS\tGENEINFO=BRCA1:672|X:1\tGT:DP:GQ\t0/1:35:99\n"
           "chr2\t200\t.\tC\t.\t.\t.\t.\n"
           "chr17\t41196312\t.\tG\tA\t50\t.\tGENE=TP53\tGT:DP\t1/1:20\n")
    for nama, data in (("a.vcf", isi.encode()), ("b.vcf.gz", gzip.compress(isi.encode()))):
        p = tmp_path / nama; p.write_bytes(data)
        v = pipeline.parse_vcf(p)
        assert len(v) == 2 and v[0]["alt"] == "G" and v[0]["gen"] == "BRCA1" and v[0]["dp"] == 35 and v[0]["gt"] == "0/1"
        assert v[1]["gen"] == "TP53" and v[1]["gq"] is None

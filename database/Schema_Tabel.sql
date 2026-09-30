-- ---------- 1. PENGGUNA ----------
CREATE TABLE pengguna (
    id_pengguna    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nama           VARCHAR(150) NOT NULL,
    email          VARCHAR(255) NOT NULL UNIQUE,
    password_hash  TEXT         NOT NULL,
    peran          VARCHAR(20)  NOT NULL DEFAULT 'peneliti'
                   CHECK (peran IN ('peneliti', 'administrator')),
    aktif          BOOLEAN      NOT NULL DEFAULT TRUE,
    dibuat_pada    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------- 2. SAMPEL ----------
CREATE TABLE sampel (
    id_sampel        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_pengguna      INTEGER      NOT NULL
                     REFERENCES pengguna(id_pengguna) ON DELETE RESTRICT,
    nama_sampel      VARCHAR(150) NOT NULL,
    lokasi           VARCHAR(255) NOT NULL,
    strain           VARCHAR(100) NOT NULL,
    karakteristik    TEXT         NOT NULL,
    tipe_baca        VARCHAR(12)  NOT NULL
                     CHECK (tipe_baca IN ('paired-end', 'single-end')),
    lokasi_fastq_r1  TEXT         NOT NULL,   -- path/S3 key, bukan isi berkas
    lokasi_fastq_r2  TEXT,                    -- wajib terisi jika paired-end
    dibuat_pada      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_sampel_paired
        CHECK (tipe_baca = 'single-end' OR lokasi_fastq_r2 IS NOT NULL)  -- BR-03
);

-- ---------- 3. REFERENSI ----------
-- Menampung genom referensi (FASTA) dan basis data anotasi
CREATE TABLE referensi (
    id_referensi   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nama_referensi VARCHAR(200) NOT NULL,
    status         VARCHAR(10)  NOT NULL
                   CHECK (status IN ('bawaan', 'unggahan')),
    jenis          VARCHAR(10)  NOT NULL DEFAULT 'genom'
                   CHECK (jenis IN ('genom', 'anotasi')),
    lokasi_berkas  TEXT         NOT NULL,
    id_pengunggah  INTEGER
                   REFERENCES pengguna(id_pengguna) ON DELETE SET NULL,
    dibuat_pada    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------- 4. ANALISIS ----------
CREATE TABLE analisis (
    id_analisis          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_pengguna          INTEGER NOT NULL
                         REFERENCES pengguna(id_pengguna) ON DELETE RESTRICT,
    id_sampel            INTEGER
                         REFERENCES sampel(id_sampel) ON DELETE RESTRICT,
    id_referensi         INTEGER
                         REFERENCES referensi(id_referensi) ON DELETE RESTRICT,
    id_referensi_anotasi INTEGER
                         REFERENCES referensi(id_referensi) ON DELETE RESTRICT,
    tanggal              TIMESTAMPTZ NOT NULL DEFAULT now(),
    status               VARCHAR(10) NOT NULL DEFAULT 'draf'
                         CHECK (status IN ('draf','menunggu','berjalan','selesai','gagal')),
    parameter            JSONB       NOT NULL
                         DEFAULT '{"kualitas_pemangkasan_min":20,"kedalaman_min":10,"qual_min":30}',
    tahap_saat_ini       VARCHAR(30)
                         CHECK (tahap_saat_ini IN
                           ('qc_trimming','alignment','bam_processing',
                            'variant_calling','filtering','anotasi')),
    progres_persen       SMALLINT    NOT NULL DEFAULT 0
                         CHECK (progres_persen BETWEEN 0 AND 100),
    log_kesalahan        TEXT,
    keterangan           TEXT,                    -- mis. "anotasi dilewati"
    terkunci             BOOLEAN     NOT NULL DEFAULT FALSE,
    dipublikasikan       BOOLEAN     NOT NULL DEFAULT FALSE,
    -- BR-01: analisis non-draf harus punya sampel + referensi
    CONSTRAINT ck_analisis_lengkap
        CHECK (status = 'draf' OR (id_sampel IS NOT NULL AND id_referensi IS NOT NULL)),
    -- BR-05: hanya analisis selesai yang boleh dikunci
    CONSTRAINT ck_analisis_terkunci
        CHECK (NOT terkunci OR status = 'selesai'),
    -- BR-06: analisis gagal/tidak lengkap tidak boleh dipublikasikan
    CONSTRAINT ck_analisis_publikasi
        CHECK (NOT dipublikasikan OR status = 'selesai')
);

-- BR-05: analisis terkunci tidak boleh diubah (hasil, parameter, referensi)
CREATE OR REPLACE FUNCTION cegah_ubah_analisis_terkunci() RETURNS trigger AS $$
BEGIN
    IF OLD.terkunci AND (
           NEW.parameter            IS DISTINCT FROM OLD.parameter
        OR NEW.id_sampel            IS DISTINCT FROM OLD.id_sampel
        OR NEW.id_referensi         IS DISTINCT FROM OLD.id_referensi
        OR NEW.id_referensi_anotasi IS DISTINCT FROM OLD.id_referensi_anotasi
        OR NEW.status               IS DISTINCT FROM OLD.status
        OR NEW.terkunci = FALSE
    ) THEN
        RAISE EXCEPTION 'Analisis % sudah terkunci (BR-05). Jalankan sebagai analisis baru.',
                        OLD.id_analisis;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_analisis_terkunci
    BEFORE UPDATE ON analisis
    FOR EACH ROW EXECUTE FUNCTION cegah_ubah_analisis_terkunci();

-- ---------- 5. VARIAN ----------
CREATE TABLE varian (
    id_varian     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_analisis   INTEGER NOT NULL
                  REFERENCES analisis(id_analisis) ON DELETE CASCADE,
    kromosom      VARCHAR(20)   NOT NULL,
    posisi        BIGINT        NOT NULL CHECK (posisi > 0),
    ref           TEXT          NOT NULL,
    alt           TEXT          NOT NULL,
    quality_score NUMERIC(10,2) NOT NULL CHECK (quality_score >= 0),
    gen           VARCHAR(100),                 -- dari anotasi (opsional), untuk pencarian UC-06
    CONSTRAINT uq_varian UNIQUE (id_analisis, kromosom, posisi, ref, alt)
);

-- ---------- 6. GENOTIPE ----------
CREATE TABLE genotipe (
    id_genotipe       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_varian         BIGINT  NOT NULL
                      REFERENCES varian(id_varian) ON DELETE CASCADE,
    id_sampel         INTEGER NOT NULL
                      REFERENCES sampel(id_sampel) ON DELETE RESTRICT,
    genotipe          VARCHAR(20)   NOT NULL,   -- contoh: 0/1, 1/1, 0|1
    kedalaman         INTEGER       NOT NULL CHECK (kedalaman >= 0),
    kualitas_genotipe NUMERIC(10,2) CHECK (kualitas_genotipe >= 0),
    CONSTRAINT uq_genotipe UNIQUE (id_varian, id_sampel)
);

-- ---------- 7. RIWAYAT ANALISIS ----------
CREATE TABLE riwayat_analisis (
    id_riwayat          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_analisis         INTEGER NOT NULL UNIQUE
                        REFERENCES analisis(id_analisis) ON DELETE CASCADE,
    tanggal             TIMESTAMPTZ NOT NULL DEFAULT now(),
    waktu_proses_detik  INTEGER CHECK (waktu_proses_detik >= 0),
    masa_retensi_hari   INTEGER NOT NULL DEFAULT 90 CHECK (masa_retensi_hari > 0), -- BR-08
    lokasi_hasil_vcf    TEXT,
    lokasi_hasil_csv    TEXT
);

-- ---------- 8. LOG AKSES ----------
CREATE TABLE log_akses (
    id_log        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    waktu         TIMESTAMPTZ NOT NULL DEFAULT now(),
    id_pengguna   INTEGER     NOT NULL
                  REFERENCES pengguna(id_pengguna) ON DELETE RESTRICT,
    jenis_objek   VARCHAR(20) NOT NULL
                  CHECK (jenis_objek IN ('sampel','analisis','varian','referensi','akun')),
    id_objek      BIGINT      NOT NULL,          -- id pada tabel sesuai jenis_objek
    jenis_aksi    VARCHAR(20) NOT NULL
                  CHECK (jenis_aksi IN ('login','lihat','unggah','ubah','hapus',
                                        'jalankan','unduh','cari'))
);

-- ---------- 9. LOG PROSES ----------
CREATE TABLE log_proses (
    id_log_proses BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_analisis   INTEGER NOT NULL
                  REFERENCES analisis(id_analisis) ON DELETE CASCADE,
    waktu         TIMESTAMPTZ NOT NULL DEFAULT now(),
    tahap         VARCHAR(30)
                  CHECK (tahap IN ('qc_trimming','alignment','bam_processing',
                                   'variant_calling','filtering','anotasi')),
    jenis_pesan   VARCHAR(10) NOT NULL
                  CHECK (jenis_pesan IN ('info','berjalan','berhasil','error')),
    pesan         TEXT NOT NULL
);

-- ---------- INDEKS ----------
CREATE INDEX idx_sampel_pengguna    ON sampel(id_pengguna);
CREATE INDEX idx_analisis_pengguna  ON analisis(id_pengguna, tanggal DESC);
CREATE INDEX idx_analisis_status    ON analisis(status);
CREATE INDEX idx_varian_analisis    ON varian(id_analisis);
CREATE INDEX idx_varian_lokus       ON varian(kromosom, posisi);
CREATE INDEX idx_varian_quality     ON varian(quality_score);
CREATE INDEX idx_varian_gen         ON varian(gen);
CREATE INDEX idx_genotipe_varian    ON genotipe(id_varian);
CREATE INDEX idx_log_pengguna_waktu ON log_akses(id_pengguna, waktu DESC);
CREATE INDEX idx_log_objek          ON log_akses(jenis_objek, id_objek);
CREATE INDEX idx_log_proses_analisis ON log_proses(id_analisis, waktu);
-- 1. pengguna
INSERT INTO pengguna (nama, email, password_hash, peran)
VALUES ('Rakazaki Putra Hendrawan', 'raka@example.com',
        crypt('Peneliti#123', gen_salt('bf')), 'peneliti');
SELECT id_pengguna, nama, email, peran FROM pengguna;

-- 2. sampel (paired-end)
INSERT INTO sampel (id_pengguna, nama_sampel, lokasi, strain, karakteristik,
                    tipe_baca, lokasi_fastq_r1, lokasi_fastq_r2)
VALUES ((SELECT id_pengguna FROM pengguna WHERE email='raka@example.com'),
        'SMP-001', 'Bogor, Jawa Barat', 'Homo sapiens', 'Sampel darah, sehat',
        'paired-end', 'uploads/smp001/R1.fastq.gz', 'uploads/smp001/R2.fastq.gz');
SELECT id_sampel, nama_sampel, lokasi, strain, tipe_baca FROM sampel;

-- 3. referensi (unggahan pengguna, anotasi)
INSERT INTO referensi (nama_referensi, status, jenis, lokasi_berkas, id_pengunggah)
VALUES ('Anotasi Kustom Raka', 'unggahan', 'anotasi', 'references/custom/anno.gtf',
        (SELECT id_pengguna FROM pengguna WHERE email='raka@example.com'));
SELECT id_referensi, nama_referensi, status, jenis FROM referensi;

-- 4. analisis
INSERT INTO analisis (id_pengguna, id_sampel, id_referensi, status,
                      tahap_saat_ini, progres_persen)
VALUES ((SELECT id_pengguna FROM pengguna WHERE email='raka@example.com'),
        (SELECT id_sampel FROM sampel WHERE nama_sampel='SMP-001'),
        (SELECT id_referensi FROM referensi WHERE status='bawaan' AND jenis='genom'),
        'berjalan', 'alignment', 40);
SELECT id_analisis, status, tahap_saat_ini, progres_persen, parameter FROM analisis;

-- 5. varian
INSERT INTO varian (id_analisis, kromosom, posisi, ref, alt, quality_score, gen)
VALUES ((SELECT max(id_analisis) FROM analisis), 'chr1', 1014143, 'C', 'T', 228.40, 'SAMD11');
SELECT id_varian, kromosom, posisi, ref || '>' || alt AS mutasi, quality_score FROM varian;

-- 6. genotipe
INSERT INTO genotipe (id_varian, id_sampel, genotipe, kedalaman, kualitas_genotipe)
VALUES ((SELECT max(id_varian) FROM varian),
        (SELECT id_sampel FROM sampel WHERE nama_sampel='SMP-001'), '0/1', 35, 99);
SELECT * FROM genotipe;

-- 7. riwayat_analisis
INSERT INTO riwayat_analisis (id_analisis, waktu_proses_detik, lokasi_hasil_vcf, lokasi_hasil_csv)
VALUES ((SELECT max(id_analisis) FROM analisis), 3600,
        'results/1/final.vcf.gz', 'results/1/final.csv');
SELECT * FROM riwayat_analisis;

-- 8. log_akses
INSERT INTO log_akses (id_pengguna, jenis_objek, id_objek, jenis_aksi)
VALUES ((SELECT id_pengguna FROM pengguna WHERE email='raka@example.com'),
        'analisis', (SELECT max(id_analisis) FROM analisis), 'lihat');
SELECT * FROM log_akses;

-- 9. log_proses
INSERT INTO log_proses (id_analisis, tahap, jenis_pesan, pesan) VALUES
 (1, NULL,          'info',     'Analisis dimulai'),
 (1, 'qc_trimming', 'berjalan', 'Menjalankan FastQC dan fastp'),
 (1, 'qc_trimming', 'berhasil', 'QC dan trimming selesai');

-- Query buat panel log UC-04 (kronologis)
SELECT waktu, tahap, jenis_pesan, pesan
FROM log_proses
WHERE id_analisis = 1
ORDER BY waktu;

-- Polling log baru saja (buat auto-refresh di frontend, NFR-05)
SELECT waktu, tahap, jenis_pesan, pesan
FROM log_proses
WHERE id_analisis = 1 AND id_log_proses > 42   -- 42 = id log terakhir yang sudah diterima
ORDER BY id_log_proses;
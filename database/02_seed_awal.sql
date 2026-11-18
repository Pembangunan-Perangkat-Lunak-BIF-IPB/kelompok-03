-- Data awal Human GVC. Jalankan SETELAH 01_schema.sql, pada database yang sama.
-- Aman dijalankan ulang (ON CONFLICT / WHERE NOT EXISTS).
-- GANTI kata sandi bawaan di bawah ini sebelum dipakai di luar pengembangan.
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- crypt()/gen_salt() untuk hash kata sandi (bcrypt)

INSERT INTO pengguna (nama, email, password_hash, peran) VALUES
  ('Rakazaki Putra Hendrawan', 'rakahendrawan@ipb.ac.id', crypt('Admin#123',    gen_salt('bf')), 'administrator'),
  ('Yaphets Mubakar',          'peneliti@ipb.ac.id',      crypt('Peneliti#123', gen_salt('bf')), 'peneliti')
ON CONFLICT (email) DO NOTHING;

-- Referensi bawaan sistem (FR-03). Letakkan berkas aslinya di STORAGE_DIR/references/
INSERT INTO referensi (nama_referensi, status, jenis, lokasi_berkas)
SELECT 'GRCh38.fasta', 'bawaan', 'genom', 'references/GRCh38.fasta'
WHERE NOT EXISTS (SELECT 1 FROM referensi WHERE status='bawaan' AND jenis='genom');
INSERT INTO referensi (nama_referensi, status, jenis, lokasi_berkas)
SELECT 'dbSNP_v155.vcf.gz', 'bawaan', 'anotasi', 'references/dbSNP_v155.vcf.gz'
WHERE NOT EXISTS (SELECT 1 FROM referensi WHERE status='bawaan' AND jenis='anotasi');

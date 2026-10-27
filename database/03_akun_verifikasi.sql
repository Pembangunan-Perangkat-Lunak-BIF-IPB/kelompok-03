-- Migrasi 03: registrasi mandiri, verifikasi email, dan reset kata sandi.
-- Jalankan SETELAH 01_schema.sql dan 02_seed_awal.sql. Aman dijalankan ulang (idempoten).
-- PERUBAHAN DI LUAR SKPL: lihat PERUBAHAN_DI_LUAR_SKPL.md.

-- 1) Kolom baru di tabel pengguna. Akun yang sudah ada dianggap terverifikasi (hanya saat kolom pertama kali dibuat).
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'pengguna' AND column_name = 'email_terverifikasi') THEN
    ALTER TABLE pengguna ADD COLUMN email_terverifikasi BOOLEAN NOT NULL DEFAULT FALSE;
    UPDATE pengguna SET email_terverifikasi = TRUE;
  END IF;
END $$;

-- 2) Tabel baru: token sekali pakai untuk verifikasi email dan reset kata sandi.
--    Yang disimpan hanya HASH (SHA-256) token; token asli hanya ada di email pengguna.
CREATE TABLE IF NOT EXISTS token_email (
    id_token      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_pengguna   INTEGER     NOT NULL REFERENCES pengguna(id_pengguna) ON DELETE CASCADE,
    jenis         VARCHAR(20) NOT NULL CHECK (jenis IN ('verifikasi', 'reset_sandi')),
    token_hash    CHAR(64)    NOT NULL UNIQUE,
    kedaluwarsa   TIMESTAMPTZ NOT NULL,
    dipakai_pada  TIMESTAMPTZ,
    dibuat_pada   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_token_email_pengguna ON token_email (id_pengguna, jenis);

-- Migrasi 04: Penambahan kolom ringkasan analisis untuk FR-14 (QC) dan FR-15 (Alignment).
-- Jalankan SETELAH 01_schema.sql, 02_seed_awal.sql, dan 03_akun_verifikasi.sql. Aman dijalankan ulang (idempoten).

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'analisis' AND column_name = 'ringkasan'
  ) THEN
    ALTER TABLE analisis ADD COLUMN ringkasan JSONB DEFAULT NULL;
    COMMENT ON COLUMN analisis.ringkasan IS 'Ringkasan metrik per tahap: qc (FR-14) dan alignment (FR-15) dalam format JSON.';
  END IF;
END $$;

